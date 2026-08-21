import json
from pathlib import Path

from pydantic import BaseModel

from propertyops_ai_investigator.domain.models import (
    OperationalIncident,
)
from propertyops_ai_investigator.rag.retriever import (
    EMBEDDING_MODEL_NAME,
    RetrievalResult,
    TechnicalRetriever,
)
from propertyops_ai_investigator.services.workspace import (
    CURRENT_RUN_DIR,
    INCIDENT_FILE,
    RAG_RESULTS_FILE,
    PipelineStep,
    RunStatus,
    load_manifest,
    save_manifest,
)


class RagArtifact(BaseModel):
    query: str
    retrieval_queries: list[str]
    k: int
    embedding_model: str
    results: list[RetrievalResult]


class RagService:
    def __init__(
        self,
        workspace_dir: Path = CURRENT_RUN_DIR,
    ) -> None:
        self.workspace_dir = workspace_dir

    def _load_incident(
        self,
    ) -> OperationalIncident:
        path = (
            self.workspace_dir
            / INCIDENT_FILE
        )

        if not path.exists():
            raise RuntimeError(
                "Incident artifact does not exist."
            )

        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if data is None:
            raise RuntimeError(
                "No operational incident exists for RAG."
            )

        return OperationalIncident.model_validate(
            data
        )

    def build_default_queries(
        self,
        incident: OperationalIncident,
    ) -> list[str]:
        evidence_by_metric = {
            evidence.metric: evidence
            for evidence in incident.evidence
        }

        power = evidence_by_metric.get(
            "power_kw"
        )

        valve = evidence_by_metric.get(
            "heating_valve_pct"
        )

        supply_temp = evidence_by_metric.get(
            "supply_air_temp_c"
        )

        fan = evidence_by_metric.get(
            "fan_status"
        )

        heating_parts = [
            (
                f"Heating system troubleshooting "
                f"for {incident.equipment_id}."
            )
        ]

        if (
            valve is not None
            and supply_temp is not None
        ):
            heating_parts.append(
                (
                    f"The heating valve was commanded "
                    f"near fully open at "
                    f"{valve.value:.1f}% while "
                    f"supply-air temperature remained "
                    f"low at about "
                    f"{supply_temp.value:.1f} C."
                )
            )

        heating_parts.append(
            (
                "What should be checked in the heating "
                "valve actuator, linkage, actual valve "
                "movement, hot-water supply, and heating "
                "coil before replacing components?"
            )
        )

        operations_parts = [
            (
                f"After-hours AHU operation "
                f"troubleshooting for "
                f"{incident.equipment_id}."
            ),
            (
                f"The AHU operated outside expected "
                f"occupied hours from "
                f"{incident.started_at.isoformat()} "
                f"to {incident.ended_at.isoformat()}."
            ),
        ]

        if fan is not None and fan.value >= 1:
            operations_parts.append(
                "The AHU fan remained running."
            )

        if power is not None:
            operations_parts.append(
                (
                    f"Power demand reached "
                    f"{power.value:.1f} kW."
                )
            )

        operations_parts.append(
            (
                "What occupancy schedules, holiday "
                "calendars, temporary overrides, manual "
                "commands, or extended-hours requests "
                "should be checked?"
            )
        )

        return [
            " ".join(heating_parts),
            " ".join(operations_parts),
        ]    

    def build_default_query(
        self,
        incident: OperationalIncident,
    ) -> str:
        queries = self.build_default_queries(
            incident
        )

        return " ".join(queries)

    def run(
        self,
        query: str | None = None,
        k: int = 3,
    ) -> RagArtifact:
        manifest = load_manifest(
            self.workspace_dir
        )

        manifest.status = RunStatus.RUNNING
        manifest.current_step = PipelineStep.RAG

        save_manifest(
            manifest,
            self.workspace_dir,
        )

        try:
            incident = self._load_incident()

            if k < 1:
                raise ValueError(
                    "k must be at least 1."
                )

            if query is not None:
                retrieval_query = query.strip()

                if not retrieval_query:
                    raise ValueError(
                        "RAG query cannot be empty."
                    )

                retrieval_queries = [
                    retrieval_query
                ]

            else:
                retrieval_queries = (
                    self.build_default_queries(
                        incident
                    )
                )

                retrieval_query = " ".join(
                    retrieval_queries
                )

            retriever = TechnicalRetriever()

            results = self._search_queries(
                retriever,
                retrieval_queries,
                k,
            )

            artifact = RagArtifact(
                query=retrieval_query,
                retrieval_queries=(
                    retrieval_queries
                ),
                k=k,
                embedding_model=(
                    EMBEDDING_MODEL_NAME
                ),
                results=results,
            )

            (
                self.workspace_dir
                / RAG_RESULTS_FILE
            ).write_text(
                artifact.model_dump_json(
                    indent=2,
                ),
                encoding="utf-8",
            )

            if (
                PipelineStep.RAG
                not in manifest.completed_steps
            ):
                manifest.completed_steps.append(
                    PipelineStep.RAG
                )

            manifest.status = RunStatus.READY
            manifest.current_step = None

            save_manifest(
                manifest,
                self.workspace_dir,
            )

            return artifact

        except Exception:
            manifest.status = RunStatus.FAILED
            manifest.current_step = PipelineStep.RAG

            save_manifest(
                manifest,
                self.workspace_dir,
            )

            raise

    def _search_queries(
        self,
        retriever: TechnicalRetriever,
        queries: list[str],
        k: int,
    ) -> list[RetrievalResult]:
        grouped_results = [
            retriever.search(
                query,
                k=k,
            )
            for query in queries
        ]

        selected: dict[
            str,
            RetrievalResult,
        ] = {}

        # Preserve coverage across the different
        # investigation aspects by first taking the
        # best result from each focused query.
        for group in grouped_results:
            if not group:
                continue

            top_result = group[0]

            selected[
                top_result.chunk_id
            ] = top_result

        # Then fill the remaining result slots using
        # the highest similarity scores available.
        candidates = sorted(
            (
                result
                for group in grouped_results
                for result in group
            ),
            key=lambda result: result.score,
            reverse=True,
        )

        for result in candidates:
            if len(selected) >= k:
                break

            if (
                result.chunk_id
                not in selected
            ):
                selected[
                    result.chunk_id
                ] = result

        # Display final results by similarity score.
        return sorted(
            selected.values(),
            key=lambda result: result.score,
            reverse=True,
        )[:k]