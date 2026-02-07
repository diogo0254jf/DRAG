from langchain_postgres import PGVector
from langchain_ollama import ChatOllama, OllamaEmbeddings
from app.core.config import DATABASE_URL, OLLAMA_CHAT_MODEL, OLLAMA_EMBED_MODEL, RAG_K

def get_vectorstore() -> PGVector:
    embeddings = OllamaEmbeddings(model=OLLAMA_EMBED_MODEL)
    return PGVector(
        embeddings=embeddings,
        collection_name="documents",
        connection=DATABASE_URL,
        use_jsonb=True,
    )

def build_llm() -> ChatOllama:
    return ChatOllama(model=OLLAMA_CHAT_MODEL, temperature=0.1)


def build_retriever(vectorstore: PGVector):
    return vectorstore.as_retriever(search_kwargs={"k": RAG_K})


def answer_query(
    query: str,
    llm: ChatOllama,
    retriever,
    prompt_smalltalk: str,
    prompt_no_context: str,
    prompt_rag: str,
    history: str,
    memory: str,
) -> str:
    if len(query.split()) <= 3:
        return llm.invoke(
            prompt_smalltalk.format(query=query, history=history, memory=memory)
        ).content

    docs = retriever.invoke(query)
    if not docs:
        prompt = prompt_no_context.format(query=query, history=history, memory=memory)
    else:
        context = "\n\n".join(d.page_content for d in docs)
        prompt = prompt_rag.format(
            context=context,
            query=query,
            history=history,
            memory=memory,
        )

    return llm.invoke(prompt).content
