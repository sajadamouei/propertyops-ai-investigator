import re
from functools import lru_cache
from pathlib import Path

import faiss
import numpy as np
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer


TECHNICAL_DOCS_DIR = Path(
    "data/source/technical_docs"
)

EMBEDDING_MODEL_NAME = (
    "sentence-transformers/all-MiniLM-L6-v2"
)


class TechnicalChunk(BaseModel):
    chunk_id: str
    source: str
    text: str


class RetrievalResult(BaseModel):
    chunk_id: str
    source: str
    text: str
    score: float


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(
        EMBEDDING_MODEL_NAME
    )


def load_technical_chunks(
    docs_dir: Path = TECHNICAL_DOCS_DIR,
) -> list[TechnicalChunk]:
    chunks: list[TechnicalChunk] = []

    for path in sorted(
        docs_dir.glob("*.md")
    ):
        text = path.read_text(
            encoding="utf-8"
        )

        sections = re.split(
            r"\n(?=## )",
            text,
        )

        for index, section in enumerate(
            sections
        ):
            section = section.strip()

            if not section:
                continue

            chunks.append(
                TechnicalChunk(
                    chunk_id=(
                        f"{path.stem}-{index}"
                    ),
                    source=path.name,
                    text=section,
                )
            )

    return chunks


class TechnicalRetriever:
    def __init__(
        self,
        docs_dir: Path = TECHNICAL_DOCS_DIR,
    ) -> None:
        self.chunks = load_technical_chunks(
            docs_dir
        )

        if not self.chunks:
            raise ValueError(
                "No technical document chunks found."
            )

        self.model = get_embedding_model()

        embeddings = self.model.encode(
            [
                chunk.text
                for chunk in self.chunks
            ],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

        embeddings = np.asarray(
            embeddings,
            dtype=np.float32,
        )

        self.index = faiss.IndexFlatIP(
            embeddings.shape[1]
        )

        self.index.add(
            embeddings
        )

    def search(
        self,
        query: str,
        k: int = 3,
    ) -> list[RetrievalResult]:
        if not query.strip():
            raise ValueError(
                "Retrieval query cannot be empty."
            )

        k = min(
            k,
            len(self.chunks),
        )

        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

        query_embedding = np.asarray(
            query_embedding,
            dtype=np.float32,
        )

        scores, indexes = self.index.search(
            query_embedding,
            k,
        )

        results = []

        for score, index in zip(
            scores[0],
            indexes[0],
        ):
            chunk = self.chunks[
                int(index)
            ]

            results.append(
                RetrievalResult(
                    chunk_id=chunk.chunk_id,
                    source=chunk.source,
                    text=chunk.text,
                    score=float(score),
                )
            )

        return results