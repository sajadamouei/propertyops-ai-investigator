from propertyops_ai_investigator.rag.retriever import (
    TechnicalRetriever,
    load_technical_chunks,
)


def test_technical_corpus_is_chunked():
    chunks = load_technical_chunks()

    assert len(chunks) >= 9

    sources = {
        chunk.source
        for chunk in chunks
    }

    assert {
        "01_heating_valve_troubleshooting.md",
        "02_after_hours_ahu_operation.md",
        "03_cold_comfort_response.md",
    }.issubset(sources)


def test_heating_valve_query_retrieves_relevant_document():
    retriever = TechnicalRetriever()

    results = retriever.search(
        (
            "Heating valve commanded fully open "
            "but supply air remains cold. "
            "Check actuator and hot water."
        ),
        k=3,
    )

    assert len(results) == 3

    assert (
        results[0].source
        == "01_heating_valve_troubleshooting.md"
    )

    assert (
        results[0].score
        >= results[1].score
    )


def test_after_hours_query_retrieves_schedule_guidance():
    retriever = TechnicalRetriever()

    results = retriever.search(
        (
            "AHU fan is running overnight "
            "outside occupied hours. "
            "Check schedules and overrides."
        ),
        k=3,
    )

    assert (
        results[0].source
        == "02_after_hours_ahu_operation.md"
    )


def test_empty_query_is_rejected():
    retriever = TechnicalRetriever()

    try:
        retriever.search("")
    except ValueError as exc:
        assert (
            "cannot be empty"
            in str(exc)
        )
    else:
        raise AssertionError(
            "Expected empty query error."
        )