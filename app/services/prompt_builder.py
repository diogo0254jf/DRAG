from app.services.prompts import get_prompt


class PromptNotConfigured(RuntimeError):
    pass


class PromptRenderError(RuntimeError):
    pass


def _get_required_placeholders(prompt) -> list[str]:
    if not prompt.required_placeholders:
        return []
    return list(prompt.required_placeholders)


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _render_prompt(prompt, values: dict) -> str:
    required = _get_required_placeholders(prompt)
    missing = [name for name in required if name not in values]
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise PromptRenderError(f"Missing placeholders: {missing_text}")
    return prompt.template.format_map(_SafeDict(values))


def build_smalltalk_prompt(db, query: str, history: str, memory: str) -> str:
    prompt = get_prompt(db, "smalltalk")
    if not prompt:
        raise PromptNotConfigured("Prompt 'smalltalk' not configured")
    return _render_prompt(
        prompt,
        {
            "query": query,
            "history": history,
            "memory": memory,
        },
    )


def build_no_context_prompt(db, query: str, history: str, memory: str) -> str:
    prompt = get_prompt(db, "no_context")
    if not prompt:
        raise PromptNotConfigured("Prompt 'no_context' not configured")
    return _render_prompt(
        prompt,
        {
            "query": query,
            "history": history,
            "memory": memory,
        },
    )


def build_rag_prompt(db, query: str, context: str, history: str, memory: str) -> str:
    prompt = get_prompt(db, "rag")
    if not prompt:
        raise PromptNotConfigured("Prompt 'rag' not configured")
    return _render_prompt(
        prompt,
        {
            "query": query,
            "context": context,
            "history": history,
            "memory": memory,
        },
    )
