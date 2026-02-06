def generate_response(llm, prompt: str) -> str:
    return llm.invoke(prompt).content
