# Deployment e Produção

## Checkpointers para Produção

### PostgreSQL (Recomendado)

```bash
pip install langgraph-checkpoint-postgres
```

```python
from langgraph.checkpoint.postgres import PostgresSaver

# Sync
checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:pass@host:5432/db"
)

# Async
async_checkpointer = await AsyncPostgresSaver.from_conn_string(
    "postgresql://user:pass@host:5432/db"
)

graph = builder.compile(checkpointer=checkpointer)
```

### SQLite (Desenvolvimento/Pequena Escala)

```bash
pip install langgraph-checkpoint-sqlite
```

```python
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string("checkpoints.db")
graph = builder.compile(checkpointer=checkpointer)
```

### Redis (Alta Performance)

```bash
pip install langgraph-checkpoint-redis
```

```python
from langgraph.checkpoint.redis import RedisSaver

checkpointer = RedisSaver(
    redis_url="redis://localhost:6379"
)
```

## Memory Store para Produção

### PostgreSQL Store

```python
from langgraph.store.postgres import PostgresStore

store = PostgresStore.from_conn_string(
    "postgresql://user:pass@host:5432/db"
)

# Com indexing para semantic search
store = PostgresStore.from_conn_string(
    conn_string,
    index={
        "dims": 1536,
        "embed": embeddings_model
    }
)

graph = builder.compile(checkpointer=checkpointer, store=store)
```

## LangGraph Platform (Cloud)

Deploy gerenciado em cloud:

```bash
pip install langgraph-cli
langgraph deploy
```

Benefícios:
- Escalabilidade automática
- Monitoramento integrado
- Versionamento
- API endpoints prontos

## Integração com FastAPI

```python
from fastapi import FastAPI
from langgraph.graph import StateGraph, MessagesState
from langgraph.checkpoint.postgres import PostgresSaver

app = FastAPI()

# Inicialização
checkpointer = None
graph = None

@app.on_event("startup")
async def startup():
    global checkpointer, graph
    checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)
    
    builder = StateGraph(MessagesState)
    # ... build graph
    graph = builder.compile(checkpointer=checkpointer)

@app.post("/chat")
async def chat(thread_id: str, message: str):
    config = {"configurable": {"thread_id": thread_id}}
    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": message}]},
        config
    )
    return {"response": result["messages"][-1].content}

@app.post("/chat/stream")
async def chat_stream(thread_id: str, message: str):
    from fastapi.responses import StreamingResponse
    
    config = {"configurable": {"thread_id": thread_id}}
    
    async def generate():
        async for chunk in graph.astream(
            {"messages": [{"role": "user", "content": message}]},
            config,
            stream_mode="messages"
        ):
            if chunk[0].content:
                yield f"data: {chunk[0].content}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

## LangSmith (Observabilidade)

```python
import os

# Habilitar tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "your-key"
os.environ["LANGCHAIN_PROJECT"] = "my-project"

# Traces são enviados automaticamente
result = graph.invoke(inputs, config)
```

## Retry e Error Handling

### Com @task (Functional API)

```python
from langgraph.func import task
import httpx

@task(retry_policy={"max_attempts": 3, "backoff_factor": 2})
def call_api(url: str) -> dict:
    response = httpx.get(url)
    response.raise_for_status()
    return response.json()
```

### Pattern de Fallback

```python
def robust_node(state):
    try:
        result = primary_llm.invoke(state["messages"])
    except Exception as e:
        logger.error(f"Primary failed: {e}")
        result = fallback_llm.invoke(state["messages"])
    
    return {"messages": [result]}
```

## Configurações de Performance

### Recursion Limit

```python
config = {
    "configurable": {"thread_id": "1"},
    "recursion_limit": 50  # Default é 25
}

result = graph.invoke(inputs, config)
```

### Durability Mode

```python
# Checkpoint após cada node (default)
graph = builder.compile(
    checkpointer=checkpointer,
    durability_mode="exit"
)

# Checkpoint async (melhor performance)
graph = builder.compile(
    checkpointer=checkpointer,
    durability_mode="async"
)
```

## Checklist de Produção

- [ ] **Persistence**: PostgresSaver ou RedisSaver
- [ ] **Memory Store**: PostgresStore com indexing
- [ ] **Observability**: LangSmith habilitado
- [ ] **Error Handling**: Retry policies configuradas
- [ ] **Rate Limiting**: Implementado no gateway
- [ ] **Timeouts**: Configurados para LLM calls
- [ ] **Recursion Limit**: Ajustado conforme necessário
- [ ] **Logging**: Estruturado com contexto
- [ ] **Health Checks**: Endpoint `/health`
- [ ] **Graceful Shutdown**: Cleanup de recursos
- [ ] **Tests**: Unit + Integration + Load
- [ ] **Monitoring**: Métricas de latência/erros
