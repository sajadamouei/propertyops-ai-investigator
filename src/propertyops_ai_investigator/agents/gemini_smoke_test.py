from langchain_google_genai import ChatGoogleGenerativeAI


def main() -> None:
    model = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        thinking_level="minimal",
    )

    response = model.invoke(
        """
        You are helping a property operations engineer.

        Explain in two sentences why unusually high HVAC
        energy consumption outside occupied hours should
        be investigated.
        """
    )

    print(response.text)


if __name__ == "__main__":
    main()