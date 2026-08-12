import asyncio

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from propertyops_ai_investigator.agents.mcp_tools import (
    READ_TOOLS,
)


async def main() -> None:
    model = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        thinking_level="minimal",
    )

    print("MCP-backed LangChain tools:")

    for tool in READ_TOOLS:
        print(f"- {tool.name}")

    agent = create_agent(
        model=model,
        tools=READ_TOOLS,
        system_prompt=(
            "You are a property operations investigation assistant. "
            "Use available tools when factual operational information "
            "is required. Never invent maintenance records, telemetry, "
            "or tenant complaints."
        ),
    )

    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "An anomaly was detected on AHU-001. "
                        "Before suggesting a cause, check whether "
                        "this equipment has relevant maintenance history."
                    ),
                }
            ]
        }
    )

    print()
    print("Agent messages:")

    for message in result["messages"]:
        print(
            f"{message.type}: "
            f"{getattr(message, 'content', '')}"
        )


if __name__ == "__main__":
    asyncio.run(main())