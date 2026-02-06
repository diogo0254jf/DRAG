# Streaming

## Modos de Stream Suportados

| Modo | Descrição |
|------|-----------|
| `values` | Retorna estado completo após cada step |
| `updates` | Retorna apenas as mudanças de estado após cada node |
| `messages` | Stream tokens de LLM em tempo real |
| `custom` | Stream dados customizados via `get_stream_writer` |
| `debug` | Informações detalhadas de debugging |

## Uso Básico

```python
# Stream updates (mudanças de estado)
for chunk in graph.stream(inputs, stream_mode="updates"):
    print(chunk)

# Async stream
async for chunk in graph.astream(inputs, stream_mode="updates"):
    print(chunk)
```

## Múltiplos Modos

```python
# Combinar múltiplos modos
for mode, chunk in graph.stream(
    inputs, 
    stream_mode=["updates", "custom"]
):
    print(f"Mode: {mode}, Chunk: {chunk}")
```

## Stream de Tokens LLM

O modo `messages` permite stream token-by-token do LLM:

```python
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, MessagesState

model = init_chat_model("gpt-4.1-mini")

def call_model(state: MessagesState):
    # Mesmo usando .invoke(), tokens são streamed com mode="messages"
    response = model.invoke(state["messages"])
    return {"messages": [response]}

graph = StateGraph(MessagesState)
graph.add_node(call_model)
graph.add_edge(START, "call_model")
graph = graph.compile()

# Stream tokens
for message_chunk, metadata in graph.stream(
    {"messages": [{"role": "user", "content": "Hello!"}]},
    stream_mode="messages",
):
    if message_chunk.content:
        print(message_chunk.content, end="", flush=True)
```

### Filtrar por LLM (com tags)

```python
# Modelos com tags diferentes
model_joke = init_chat_model("gpt-4", tags=["joke"])
model_poem = init_chat_model("gpt-4", tags=["poem"])

# Filtrar pelo tag
async for msg, metadata in graph.astream(
    {"topic": "cats"},
    stream_mode="messages",
):
    if metadata["tags"] == ["joke"]:
        print(msg.content, end="", flush=True)
```

## Stream de Dados Customizados

Use `get_stream_writer` para emitir dados customizados durante execução:

```python
from langgraph.config import get_stream_writer
from langgraph.graph import StateGraph, START

def process_node(state):
    writer = get_stream_writer()
    
    # Emitir progresso
    writer({"progress": "Starting processing..."})
    
    # Fazer algo
    result = process_data(state["data"])
    
    # Emitir mais dados
    writer({"progress": "Done!", "items_processed": 100})
    
    return {"result": result}

graph = StateGraph(State)
graph.add_node("process", process_node)
graph.add_edge(START, "process")
graph = graph.compile()

# Receber dados customizados
for chunk in graph.stream(inputs, stream_mode="custom"):
    print(chunk)  # {"progress": "Starting processing..."}
```

### Em Tools

```python
from langchain.tools import tool
from langgraph.config import get_stream_writer

@tool
def query_database(query: str) -> str:
    """Query database with progress updates"""
    writer = get_stream_writer()
    
    writer({"type": "progress", "data": "Querying..."})
    results = db.query(query)
    writer({"type": "progress", "data": f"Found {len(results)} results"})
    
    return str(results)
```

## Stream de Subgraphs

Para incluir outputs de subgraphs:

```python
# Subgraph incluso no stream
for chunk in graph.stream(
    inputs,
    stream_mode="updates",
    subgraphs=True  # Inclui outputs de subgraphs
):
    print(chunk)
```

## Debugging

```python
for chunk in graph.stream(inputs, stream_mode="debug"):
    # Informações detalhadas sobre cada step
    print(chunk)
```

## Async com Python < 3.11

```python
import asyncio
from langchain_core.runnables import RunnableConfig

async def main():
    async with asyncio.TaskGroup() as tg:
        async for chunk in graph.astream(
            inputs,
            stream_mode="messages",
        ):
            print(chunk)

# Necessário para Python < 3.11
asyncio.run(main())
```
