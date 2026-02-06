from langchain_core.documents import Document


def retrieve_context(retriever, query: str) -> tuple[str, list[Document]]:
    docs = retriever.invoke(query)
    if not docs:
        return "", []
    context = "\n\n".join(doc.page_content for doc in docs)
    return context, docs
