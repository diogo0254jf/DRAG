import os
from typing import List, Optional

from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import DOCS_DIR, FAISS_PATH, OLLAMA_CHAT_MODEL, OLLAMA_EMBED_MODEL, RAG_K


def index_docs() -> Optional[FAISS]:
    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR, exist_ok=True)

    loader = DirectoryLoader(
        DOCS_DIR,
        glob="*",
        loader_cls=PyPDFLoader,
        show_progress=True,
    )
    docs: List[Document] = loader.load() or []

    if len(docs) == 0:
        txt_loader = DirectoryLoader(
            DOCS_DIR,
            glob="*",
            loader_cls=TextLoader,
            show_progress=True,
        )
        docs = txt_loader.load() or []

    if len(docs) == 0:
        return None

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", ".", "!", "?", " ", ""],
    )
    chunks = splitter.split_documents(docs)

    embed_model = OllamaEmbeddings(model=OLLAMA_EMBED_MODEL)
    texts = [c.page_content for c in chunks]

    vectorstore = FAISS.from_texts(texts, embed_model, metadatas=[c.metadata for c in chunks])
    vectorstore.save_local(FAISS_PATH)

    return vectorstore


def load_vectorstore() -> FAISS:
    embed_model = OllamaEmbeddings(model=OLLAMA_EMBED_MODEL)
    return FAISS.load_local(FAISS_PATH, embed_model, allow_dangerous_deserialization=True)


def build_llm() -> ChatOllama:
    return ChatOllama(model=OLLAMA_CHAT_MODEL, temperature=0.1)


def build_retriever(vectorstore: FAISS):
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
