from propertyops_ai_investigator.data.experiment import (
    ScenarioType,
    create_scenario_config,
)
from propertyops_ai_investigator.services.workspace import (
    RunStatus,
    load_manifest,
    reset_current_run,
)


def test_reset_current_run_creates_manifest(
    tmp_path,
):
    workspace = tmp_path / "current_run"

    config = create_scenario_config(
        ScenarioType.HEATING_VALVE_FAULT
    )

    manifest = reset_current_run(
        config,
        workspace,
    )

    assert (
        workspace / "manifest.json"
    ).exists()

    assert (
        manifest.status
        == RunStatus.READY
    )

    loaded = load_manifest(
        workspace
    )

    assert (
        loaded.run_id
        == manifest.run_id
    )

    assert (
        loaded.config.scenario
        == ScenarioType.HEATING_VALVE_FAULT
    )


def test_reset_current_run_removes_old_artifacts(
    tmp_path,
):
    workspace = tmp_path / "current_run"

    workspace.mkdir(
        parents=True
    )

    old_file = (
        workspace / "old_result.csv"
    )

    old_file.write_text(
        "old",
        encoding="utf-8",
    )

    config = create_scenario_config(
        ScenarioType.NORMAL_OPERATION
    )

    reset_current_run(
        config,
        workspace,
    )

    assert not old_file.exists()

    assert (
        workspace / "manifest.json"
    ).exists()