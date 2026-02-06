# StateGraph - Graph API

## Definindo Estado

O estado é o schema que flui pelo grafo. Use `TypedDict` ou `Pydantic`:

```python
from typing import TypedDict, NotRequired, Annotated
from langgraph.graph import add_messages

class State(TypedDict):
    # Campo simples
    query: str
    
    # Campo opcional
    context: NotRequired[str]
    
    # Campo com reducer (append ao invés de sobrescrever)
    messages: Annotated[list, add_messages]
```

## Reducers

Reducers definem como atualizar campos quando múltiplos nodes retornam valores:

```python
from operator import add

class State(TypedDict):
    # Soma valores
    count: Annotated[int, add]
    
    # Concatena listas (default para messages)
    messages: Annotated[list, add_messages]
```

## MessagesState

State pré-definido para chatbots:

```python
from langgraph.graph import MessagesState

class MyState(MessagesState):
    # Já inclui: messages: Annotated[list, add_messages]
    custom_field: str
```

## Criando o Grafo

```python
from langgraph.graph import StateGraph, START, END

builder = StateGraph(State)

# Adicionar nodes
builder.add_node("retrieve", retrieve_function)
builder.add_node("generate", generate_function)

# Conectar edges
builder.add_edge(START, "retrieve")
builder.add_edge("retrieve", "generate")
builder.add_edge("generate", END)

# Compilar
graph = builder.compile()
```

## Nodes

Nodes são funções que recebem estado e retornam atualizações:

```python
def my_node(state: State) -> dict:
    # Retorna APENAS os campos que mudam
    return {"context": "novo contexto"}

def node_with_config(state: State, config: RunnableConfig) -> dict:
    thread_id = config["configurable"]["thread_id"]
    return {"result": f"Thread: {thread_id}"}

def node_with_runtime(state: State, runtime: Runtime) -> dict:
    # Acesso a store, stream_writer, context
    store = runtime.store
    return state
```

## Edges

### Normal Edge
```python
builder.add_edge("node_a", "node_b")
```

### Conditional Edge
```python
def router(state: State) -> str:
    if state["query_type"] == "simple":
        return "simple_node"
    return "complex_node"

builder.add_conditional_edges(
    "classifier",
    router,
    {"simple_node": "simple_node", "complex_node": "complex_node"}
)
```

### Entry Condicional
```python
builder.add_conditional_edges(START, router)
```

## Compilação

```python
# Básico
graph = builder.compile()

# Com checkpointer (persistência)
from langgraph.checkpoint.memory import InMemorySaver
graph = builder.compile(checkpointer=InMemorySaver())

# Com store (memória de longo prazo)
from langgraph.store.memory import InMemoryStore
graph = builder.compile(checkpointer=checkpointer, store=InMemoryStore())
```

## Invocação

```python
# Sem persistência
result = graph.invoke({"query": "hello"})

# Com thread_id (persistência)
config = {"configurable": {"thread_id": "user-123"}}
result = graph.invoke({"messages": [...]}, config)

# Streaming
for event in graph.stream({"messages": [...]}, config):
    print(event)
```
