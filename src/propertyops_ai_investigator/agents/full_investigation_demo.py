import asyncio

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_google_genai import ChatGoogleGenerativeAI

from propertyops_ai_investigator.agents.mcp_tools import (
    READ_TOOLS,
)
from propertyops_ai_investigator.domain.models import (
    InvestigationAssessment,
)


async def main() -> None:
    model = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        thinking_level="minimal",
    )

    agent = create_agent(
        model=model,
        tools=READ_TOOLS,
        response_format=ToolStrategy(
            InvestigationAssessment
        ),
        system_prompt=(
            "You are a property operations investigation assistant. "
            "Investigate operational incidents using available tools. "

            "Important rules: "
            "1. Use tools for factual operational information. "
            "2. Do not invent telemetry, maintenance records, or complaints. "
            "3. Distinguish evidence from hypotheses. "
            "4. Do not claim a confirmed root cause unless the evidence proves it. "
            "5. Do not perform write actions. "
            "6. Investigate across relevant evidence sources before recommending action."
        ),
    )

    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": """
A high-severity anomaly was detected for AHU-001
in building BLDG-001.

Incident window:
2026-01-15 01:00 to 2026-01-15 05:00.

Initial anomaly evidence:
- maximum power approximately 148.7 kW
- heating valve reached approximately 95%
- minimum supply-air temperature approximately 14.4 C
- AHU fan was running
- this occurred outside expected occupied hours

Investigate the incident.

Check:
- relevant telemetry during the incident,
- maintenance history for AHU-001,
- tenant complaints from BLDG-001 / ZONE-003
  between 2026-01-15 06:00 and 12:00.

Then produce an evidence-based assessment and recommend
the next operational step.
"""
                }
            ]
        }
    )

    print("Tool trajectory:")
    print()

    for message in result["messages"]:
        if getattr(message, "tool_calls", None):
            for tool_call in message.tool_calls:
                print(
                    f"AI → {tool_call['name']}"
                    f"({tool_call['args']})"
                )

        if message.type == "tool":
            print(f"TOOL → {message.name}")
            print(f"      {message.content}")

    print()
    print("Structured assessment:")
    print()

    assessment = result["structured_response"]

    print(
        assessment.model_dump_json(
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())