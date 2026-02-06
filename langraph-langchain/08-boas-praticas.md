# Boas Práticas e Patterns

## Arquitetura de Agentes

### Pattern: RAG Agent com LangGraph

```python
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.postgres import PostgresSaver

class RAGState(MessagesState):
    context: str = ""
    
def retrieve(state: RAGState):
    query = state["messages"][-1].content
    docs = retriever.invoke(query)
    return {"context": "\n\n".join(d.page_content for d in docs)}

def generate(state: RAGState):
    prompt = f"""Use this context to answer:
    {state['context']}
    
    Question: {state['messages'][-1].content}"""
    response = llm.invoke(prompt)
    return {"messages": [response]}

def should_retrieve(state: RAGState) -> str:
    """Router: decide se precisa de contexto"""
    query = state["messages"][-1].content
    if len(query.split()) <= 3:
        return "generate"  # Smalltalk direto
    return "retrieve"

builder = StateGraph(RAGState)
builder.add_node("retrieve", retrieve)
builder.add_node("generate", generate)
builder.add_conditional_edges(START, should_retrieve)
builder.add_edge("retrieve", "generate")
builder.add_edge("generate", END)

checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)
graph = builder.compile(checkpointer=checkpointer)
```

### Pattern: Agent com Tools

```python
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode

@tool
def search_web(query: str) -> str:
    """Search the web for information"""
    return web_search(query)

@tool  
def calculator(expression: str) -> str:
    """Calculate mathematical expressions"""
    return str(eval(expression))

tools = [search_web, calculator]
llm_with_tools = llm.bind_tools(tools)

def agent(state):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state) -> str:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

builder = StateGraph(MessagesState)
builder.add_node("agent", agent)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", should_continue)
builder.add_edge("tools", "agent")

graph = builder.compile()
```

## Gerenciamento de Estado

### ✅ Retorne apenas campos que mudam

```python
def good_node(state):
    # Só retorna o que muda
    return {"result": compute_result(state["input"])}

def bad_node(state):
    # Não copie todo o estado
    return {**state, "result": compute_result(state["input"])}  # ❌
```

### ✅ Use reducers para acumulação

```python
from operator import add
from langgraph.graph import add_messages

class State(TypedDict):
    # Mensagens acumulam
    messages: Annotated[list, add_messages]
    
    # Contadores somam
    api_calls: Annotated[int, add]
    
    # Listas concatenam
    sources: Annotated[list, add]
```

### ✅ Separe input/output schemas se necessário

```python
class InputState(TypedDict):
    query: str

class OutputState(TypedDict):
    answer: str
    sources: list[str]

class InternalState(InputState, OutputState):
    context: str  # Não exposto

builder = StateGraph(
    InternalState,
    input=InputState,
    output=OutputState
)
```

## Error Handling

### Pattern: Retry com Fallback

```python
from langgraph.func import task

@task(retry_policy={"max_attempts": 3, "backoff": 2.0})
def call_primary_api(data):
    return primary_api.call(data)

def api_node(state):
    try:
        result = call_primary_api(state["data"]).result()
    except Exception:
        # Fallback
        result = fallback_api.call(state["data"])
    return {"result": result}
```

### Pattern: Error State

```python
class State(TypedDict):
    messages: list
    error: str | None

def risky_node(state):
    try:
        result = risky_operation()
        return {"messages": [result]}
    except Exception as e:
        return {"error": str(e)}

def should_continue(state):
    if state.get("error"):
        return "error_handler"
    return "next_node"
```

## Performance

### ✅ Paralelização com tasks

```python
@task
def process_item(item):
    return expensive_operation(item)

def batch_node(state):
    # Executa em paralelo
    futures = [process_item(item) for item in state["items"]]
    results = [f.result() for f in futures]
    return {"results": results}
```

### ✅ Streaming para UX

```python
async def handle_chat(message: str):
    config = {"configurable": {"thread_id": session_id}}
    
    async for event in graph.astream(
        {"messages": [message]}, 
        config,
        stream_mode="messages"  # Stream tokens
    ):
        yield event
```

### ✅ Cache de nodes

```python
from langgraph.cache import InMemoryCache

builder.add_node("expensive", expensive_node, cache=InMemoryCache())
```

## Testing

### Unit Test de Nodes

```python
def test_retrieve_node():
    state = {"messages": [HumanMessage("What is X?")]}
    result = retrieve(state)
    
    assert "context" in result
    assert len(result["context"]) > 0
```

### Integration Test de Graph

```python
def test_full_flow():
    checkpointer = InMemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    
    config = {"configurable": {"thread_id": "test"}}
    result = graph.invoke(
        {"messages": [HumanMessage("Hello")]},
        config
    )
    
    assert len(result["messages"]) == 2
    assert result["messages"][-1].type == "ai"
```

### Test de Persistence

```python
def test_resume_after_interrupt():
    graph = builder.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "test"}}
    
    # Primeira execução - para em interrupt
    result1 = graph.invoke({"query": "sensitive"}, config)
    assert "__interrupt__" in str(result1)
    
    # Resume
    result2 = graph.invoke(Command(resume="approve"), config)
    assert result2["status"] == "completed"
```

## Checklist de Produção

- [ ] Usar `PostgresSaver` ao invés de `InMemorySaver`
- [ ] Todas as API calls em `@task`
- [ ] Error handling em todos os nodes
- [ ] Logging estruturado
- [ ] Métricas de latência por node
- [ ] Rate limiting em API calls
- [ ] Timeout configurado
- [ ] Recursion limit definido
- [ ] Testes de replay/resume
- [ ] Monitoramento com LangSmith
