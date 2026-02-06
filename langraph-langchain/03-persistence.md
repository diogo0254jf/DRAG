# Persistence - Checkpointers & Memory Store

## Conceitos

- **Checkpoint**: Snapshot do estado do grafo em um ponto no tempo
- **Thread**: Identificador único para uma instância de execução (ex: conversa)
- **Store**: Armazenamento de memória de longo prazo que persiste entre threads

## Checkpointer Libraries

| Library | Uso | Instalação |
|---------|-----|------------|
| `InMemorySaver` | Desenvolvimento/testes | Incluído |
| `SqliteSaver` | Local/protótipos | `pip install langgraph-checkpoint-sqlite` |
| `PostgresSaver` | **Produção** | `pip install langgraph-checkpoint-postgres` |
| `CosmosDBSaver` | Azure production | `pip install langgraph-checkpoint-cosmosdb` |

## Configuração Básica

```python
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres import PostgresSaver

# Desenvolvimento
checkpointer = InMemorySaver()

# Produção
checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:pass@localhost/db"
)

graph = builder.compile(checkpointer=checkpointer)
```

## Usando Threads

```python
import uuid

# Cada conversa tem seu próprio thread_id
thread_id = str(uuid.uuid4())
config = {"configurable": {"thread_id": thread_id}}

# Primeira mensagem
result = graph.invoke({"messages": [user_msg]}, config)

# Próxima mensagem (histórico é automaticamente recuperado)
result = graph.invoke({"messages": [next_msg]}, config)
```

## Operações com Estado

### Get State
```python
state = graph.get_state(config)
print(state.values)  # Estado atual
print(state.next)    # Próximos nodes
```

### Get State History
```python
for state in graph.get_state_history(config):
    print(state.values)
    print(state.config)  # Inclui checkpoint_id
```

### Replay (Time Travel)
```python
# Pegar checkpoint específico do histórico
old_config = {"configurable": {"thread_id": "...", "checkpoint_id": "..."}}
graph.invoke(None, old_config)  # Continua daquele ponto
```

### Update State
```python
graph.update_state(config, {"messages": [new_message]})
```

## Memory Store (Long-term Memory)

Para memória que persiste **entre threads/conversas**:

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()
graph = builder.compile(checkpointer=checkpointer, store=store)

# No node, acessar via runtime
def memory_node(state, runtime):
    # Salvar memória
    runtime.store.put(
        namespace=("user", state["user_id"]),
        key="preferences",
        value={"theme": "dark"}
    )
    
    # Buscar memória
    items = runtime.store.search(
        namespace=("user", state["user_id"]),
        query="preferences"
    )
    return state
```

### Semantic Search no Store

```python
from langchain_openai import OpenAIEmbeddings

store = InMemoryStore(
    index={
        "embed": OpenAIEmbeddings(),
        "dims": 1536
    }
)

# Busca semântica
results = store.search(
    namespace=("memories",),
    query="user preferences for dark mode"
)
```

## Durability Modes

Controla quando checkpoints são salvos:

```python
# "exit": Só ao final (melhor performance)
graph.stream(input, config, durability="exit")

# "async": Assíncrono durante execução
graph.stream(input, config, durability="async")

# "sync": Síncrono antes de cada step (mais seguro)
graph.stream(input, config, durability="sync")
```
