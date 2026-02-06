from app.core.rag import answer_query
from app.services.prompts import get_prompt


class PromptNotConfigured(RuntimeError):
    pass


def answer_with_prompts(
    db,
    message: str,
    llm,
    retriever,
    history: str,
    memory: str,
) -> str:
    prompt_smalltalk = get_prompt(db, "smalltalk")
    prompt_no_context = get_prompt(db, "no_context")
    prompt_rag = get_prompt(db, "rag")

    if not prompt_smalltalk or not prompt_no_context or not prompt_rag:
        raise PromptNotConfigured("Prompt templates are not configured")

    return answer_query(
        message,
        llm,
        retriever,
        prompt_smalltalk.template,
        prompt_no_context.template,
        prompt_rag.template,
        history,
        memory,
    )
