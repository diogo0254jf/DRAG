import os

from app.core.config import PROMPT_SEED_PATH
from app.core.rag import (
    FAISS_PATH,
    answer_query,
    build_llm,
    build_retriever,
    index_docs,
    load_vectorstore,
)
from app.services.prompts import load_seed_prompts

_seed_prompts = load_seed_prompts(PROMPT_SEED_PATH)
_prompt_map = {item.get("key"): item.get("template") for item in _seed_prompts}

PROMPT_SMALLTALK = _prompt_map.get("smalltalk")
PROMPT_NO_CONTEXT = _prompt_map.get("no_context")
PROMPT_RAG = _prompt_map.get("rag")

if not PROMPT_SMALLTALK or not PROMPT_NO_CONTEXT or not PROMPT_RAG:
    raise RuntimeError("Missing prompt templates. Set PROMPT_SEED_PATH to a valid JSON file.")


def chat_loop(vectorstore):
    llm = build_llm()
    retriever = build_retriever(vectorstore)

    print("\nRAG Chat pronto (Ollama + FAISS)")
    print("Digite 'quit' para sair.")

    while True:
        query = input("\nPergunta: ").strip()
        if query.lower() == "quit":
            break

        response = answer_query(
            query,
            llm,
            retriever,
            PROMPT_SMALLTALK,
            PROMPT_NO_CONTEXT,
            PROMPT_RAG,
            "",
            "",
        )
        print("Resposta:", response)


if __name__ == "__main__":
    if os.path.exists(FAISS_PATH):
        vectorstore = load_vectorstore()
        print("FAISS carregado do disco.")
    else:
        vectorstore = index_docs()
        if vectorstore is None:
            exit(1)

    chat_loop(vectorstore)
