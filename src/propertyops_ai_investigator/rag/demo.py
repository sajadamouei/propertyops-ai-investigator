from propertyops_ai_investigator.rag.retriever import (
    TechnicalRetriever,
)


def main() -> None:
    retriever = TechnicalRetriever()

    query = (
        "The AHU heating valve is commanded "
        "almost fully open but supply air remains cold. "
        "What should be checked?"
    )

    results = retriever.search(
        query,
        k=3,
    )

    print(f"Query: {query}")
    print()

    for rank, result in enumerate(
        results,
        start=1,
    ):
        print(
            f"#{rank} "
            f"{result.source} "
            f"score={result.score:.3f}"
        )

        print(
            result.text
        )

        print()


if __name__ == "__main__":
    main()