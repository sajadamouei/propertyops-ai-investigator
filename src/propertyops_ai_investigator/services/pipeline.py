import json
from pathlib import Path

import pandas as pd

from propertyops_ai_investigator.data.generate_synthetic import (
    generate_sensor_readings,
)
from propertyops_ai_investigator.ml.features import (
    build_feature_table,
)
from propertyops_ai_investigator.ml.incidents import (
    create_operational_incidents,
)
from propertyops_ai_investigator.ml.isolation_forest import (
    build_events,
    fit_detector,
    score_anomalies,
)
from propertyops_ai_investigator.services.workspace import (
    ANOMALY_SCORES_FILE,
    CURRENT_RUN_DIR,
    DETECTION_FILE,
    EVENTS_FILE,
    FEATURES_FILE,
    INCIDENT_FILE,
    RAW_TELEMETRY_FILE,
    PipelineStep,
    RunManifest,
    RunStatus,
    load_manifest,
    save_manifest,
)


class PipelineService:
    def __init__(
        self,
        workspace_dir: Path = CURRENT_RUN_DIR,
    ) -> None:
        self.workspace_dir = workspace_dir

    def _artifact_path(
        self,
        filename: str,
    ) -> Path:
        return self.workspace_dir / filename

    def _start_step(
        self,
        manifest: RunManifest,
        step: PipelineStep,
    ) -> None:
        manifest.status = RunStatus.RUNNING
        manifest.current_step = step

        save_manifest(
            manifest,
            self.workspace_dir,
        )

    def _complete_step(
        self,
        manifest: RunManifest,
        step: PipelineStep,
    ) -> None:
        if step not in manifest.completed_steps:
            manifest.completed_steps.append(step)

        manifest.status = RunStatus.READY
        manifest.current_step = None

        save_manifest(
            manifest,
            self.workspace_dir,
        )

    def _require_artifact(
        self,
        filename: str,
    ) -> Path:
        path = self._artifact_path(
            filename
        )

        if not path.exists():
            raise RuntimeError(
                f"Required pipeline artifact does not exist: "
                f"{filename}"
            )

        return path

    def generate_data(
        self,
    ) -> pd.DataFrame:
        manifest = load_manifest(
            self.workspace_dir
        )

        self._start_step(
            manifest,
            PipelineStep.GENERATE_DATA,
        )

        readings = generate_sensor_readings(
            manifest.config
        )

        path = self._artifact_path(
            RAW_TELEMETRY_FILE
        )

        readings.to_csv(
            path,
            index=False,
        )

        self._complete_step(
            manifest,
            PipelineStep.GENERATE_DATA,
        )

        return readings

    def engineer_features(
        self,
    ) -> pd.DataFrame:
        manifest = load_manifest(
            self.workspace_dir
        )

        raw_path = self._require_artifact(
            RAW_TELEMETRY_FILE
        )

        self._start_step(
            manifest,
            PipelineStep.FEATURE_ENGINEERING,
        )

        readings = pd.read_csv(
            raw_path,
            parse_dates=["timestamp"],
        )

        features = build_feature_table(
            readings
        )

        features.to_csv(
            self._artifact_path(
                FEATURES_FILE
            ),
            index=False,
        )

        self._complete_step(
            manifest,
            PipelineStep.FEATURE_ENGINEERING,
        )

        return features

    def detect_anomalies(
        self,
    ) -> tuple[
        pd.DataFrame,
        pd.DataFrame,
        float,
    ]:
        manifest = load_manifest(
            self.workspace_dir
        )

        features_path = self._require_artifact(
            FEATURES_FILE
        )

        self._start_step(
            manifest,
            PipelineStep.ANOMALY_DETECTION,
        )

        features = pd.read_csv(
            features_path,
            parse_dates=["timestamp"],
        )

        model, threshold = fit_detector(
            features
        )

        scored = score_anomalies(
            features,
            model,
            threshold,
        )

        events = build_events(
            scored
        )

        scored.to_csv(
            self._artifact_path(
                ANOMALY_SCORES_FILE
            ),
            index=False,
        )

        events.to_csv(
            self._artifact_path(
                EVENTS_FILE
            ),
            index=False,
        )

        detection_summary = {
            "threshold": threshold,
            "anomalous_observations": int(
                scored["is_anomaly"].sum()
            ),
            "event_count": len(events),
        }

        self._artifact_path(
            DETECTION_FILE
        ).write_text(
            json.dumps(
                detection_summary,
                indent=2,
            ),
            encoding="utf-8",
        )

        self._complete_step(
            manifest,
            PipelineStep.ANOMALY_DETECTION,
        )

        return scored, events, threshold

    def build_incident(
        self,
    ):
        manifest = load_manifest(
            self.workspace_dir
        )

        scored_path = self._require_artifact(
            ANOMALY_SCORES_FILE
        )

        events_path = self._require_artifact(
            EVENTS_FILE
        )

        self._start_step(
            manifest,
            PipelineStep.BUILD_INCIDENT,
        )

        scored = pd.read_csv(
            scored_path,
            parse_dates=["timestamp"],
        )

        events = pd.read_csv(
            events_path,
            parse_dates=[
                "start",
                "end",
            ],
        )

        incidents = create_operational_incidents(
            scored,
            events,
        )

        # This demo currently expects at most one meaningful
        # multi-hour operational incident.
        incident = (
            incidents[0]
            if incidents
            else None
        )

        incident_path = self._artifact_path(
            INCIDENT_FILE
        )

        if incident is None:
            incident_path.write_text(
                "null",
                encoding="utf-8",
            )
        else:
            incident_path.write_text(
                incident.model_dump_json(
                    indent=2,
                ),
                encoding="utf-8",
            )

        self._complete_step(
            manifest,
            PipelineStep.BUILD_INCIDENT,
        )

        return incident

    def run_deterministic_pipeline(
        self,
    ):
        self.generate_data()
        self.engineer_features()
        self.detect_anomalies()

        return self.build_incident()