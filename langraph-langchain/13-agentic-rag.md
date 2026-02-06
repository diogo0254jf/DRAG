# Agentic RAG

Tutorial completo para construir um agente RAG com LangGraph.

## Overview

Um Agentic RAG combina:
- **Retrieval**: Buscar documentos relevantes
- **Agent**: Decidir quando buscar, avaliar qualidade, reformular perguntas

## Componentes

1. **Generate Query or Respond**: Decide se precisa buscar ou responder direto
2. **Retriever Tool**: Busca documentos
3. **Grade Documents**: Avalia se documentos são relevantes
4. **Rewrite Question**: Reformula pergunta se docs não são bons
5. **Generate Answer**: Gera resposta final

## Implementação Completa

### 1. Setup

```python
from langchain.chat_models import init_chat_model
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

model = init_chat_model("gpt-4")
embeddings = OpenAIEmbeddings()

# Criar vectorstore
vectorstore = FAISS.from_texts(documents, embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
```

### 2. Retriever Tool

```python
from langchain.tools import tool

@tool
def retriever_tool(query: str) -> str:
    """Search for information in the knowledge base."""
    docs = retriever.invoke(query)
    return "\n\n".join(doc.page_content for doc in docs)
```

### 3. Generate Query or Respond Node

```python
from langgraph.graph import MessagesState

def generate_query_or_respond(state: MessagesState):
    """Decide whether to search or respond directly."""
    model_with_tools = model.bind_tools([retriever_tool])
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}
```

### 4. Grade Documents

```python
from pydantic import BaseModel, Field
from langchain_core.messages import ToolMessage

class GradeDocuments(BaseModel):
    """Grade relevance of retrieved documents."""
    relevant: bool = Field(
        description="Are the documents relevant to the question?"
    )

def grade_documents(state: MessagesState) -> str:
    """Evaluate document relevance and route accordingly."""
    messages = state["messages"]
    
    # Encontrar última tool message (resultado do retriever)
    tool_message = None
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            tool_message = msg
            break
    
    if not tool_message:
        return "generate_answer"
    
    # Grading com structured output
    grader = model.with_structured_output(GradeDocuments)
    question = messages[0].content
    docs = tool_message.content
    
    result = grader.invoke(
        f"Question: {question}\n\nDocuments: {docs}\n\n"
        "Are these documents relevant to answer the question?"
    )
    
    if result.relevant:
        return "generate_answer"
    return "rewrite_question"
```

### 5. Rewrite Question

```python
def rewrite_question(state: MessagesState):
    """Rewrite the question to improve retrieval."""
    original_question = state["messages"][0].content
    
    rewritten = model.invoke(
        f"The following question didn't get good retrieval results. "
        f"Rewrite it to be more specific:\n\n{original_question}"
    )
    
    return {"messages": [{"role": "user", "content": rewritten.content}]}
```

### 6. Generate Answer

```python
def generate_answer(state: MessagesState):
    """Generate final answer using retrieved context."""
    messages = state["messages"]
    
    # Encontrar context da tool message
    context = ""
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            context = msg.content
            break
    
    question = messages[0].content
    
    prompt = f"""Answer the question based on the following context:

Context: {context}

Question: {question}

Answer:"""
    
    response = model.invoke(prompt)
    return {"messages": [response]}
```

### 7. Montar o Grafo

```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

workflow = StateGraph(MessagesState)

# Nodes
workflow.add_node(generate_query_or_respond)
workflow.add_node("retrieve", ToolNode([retriever_tool]))
workflow.add_node(rewrite_question)
workflow.add_node(generate_answer)

# Edges
workflow.add_edge(START, "generate_query_or_respond")

# Decide se busca ou responde direto
workflow.add_conditional_edges(
    "generate_query_or_respond",
    tools_condition,
    {
        "tools": "retrieve",
        END: END,
    },
)

# Após retrieval, avalia documentos
workflow.add_conditional_edges(
    "retrieve",
    grade_documents,
    {
        "generate_answer": "generate_answer",
        "rewrite_question": "rewrite_question",
    }
)

workflow.add_edge("generate_answer", END)
workflow.add_edge("rewrite_question", "generate_query_or_respond")

graph = workflow.compile()
```

### 8. Visualizar

```python
from IPython.display import Image, display
display(Image(graph.get_graph().draw_mermaid_png()))
```

### 9. Executar

```python
from langchain_core.messages import HumanMessage

result = graph.invoke({
    "messages": [HumanMessage("What is LangGraph?")]
})

print(result["messages"][-1].content)
```

## Fluxo

```
START
  ↓
generate_query_or_respond
  ↓ (tools_condition)
  ├── END (se não precisa buscar)
  └── retrieve
        ↓ (grade_documents)
        ├── generate_answer → END
        └── rewrite_question → generate_query_or_respond (loop)
```

## Melhorias Opcionais

### Limite de Reformulações

```python
class State(MessagesState):
    rewrite_count: int = 0

def rewrite_question(state: State):
    if state["rewrite_count"] >= 2:
        # Limite atingido, responder mesmo assim
        return Command(goto="generate_answer")
    
    # ... rewrite logic
    return {
        "messages": [rewritten],
        "rewrite_count": state["rewrite_count"] + 1
    }
```

### Múltiplos Retrievers

```python
@tool
def web_search(query: str) -> str:
    """Search the web."""
    return web_search_api(query)

@tool
def db_search(query: str) -> str:
    """Search internal database."""
    return vectorstore.similarity_search(query)

tools = [web_search, db_search]
model_with_tools = model.bind_tools(tools)
```

### Streaming de Resposta

```python
async for chunk in graph.astream(
    {"messages": [HumanMessage("What is X?")]},
    stream_mode="messages"
):
    if chunk[0].content:
        print(chunk[0].content, end="", flush=True)
```
