from langchain_google_genai import ChatGoogleGenerativeAI

from propertyops_ai_investigator.domain.models import (
    InvestigationAssessment,
)


def main() -> None:
    model = ChatGoogleGenerativeAI(
            model="gemini-3.5-flash-lite",
            thinking_level="minimal",
        )

    structured_model = model.with_structured_output(
        InvestigationAssessment,
        method="json_schema",
    )

    result = structured_model.invoke(
        """
        A commercial building's AHU showed:

        - power consumption: 148 kW at 02:00
        - normal off-hours power: about 28 kW
        - heating valve: 95% open
        - supply air temperature: 14.4 C
        - fan running outside occupied hours

        Do not claim a confirmed root cause.
        Assess what should be investigated next.
        """
    )

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()