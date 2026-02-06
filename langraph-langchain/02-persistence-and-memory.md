# 02 - Persistence, Memory & Durable Execution

A persistência é o que torna os agentes LangGraph **stateful** e **robustos**, permitindo pausar, retomar e manter memória entre sessões.

## 1. Persistência (Checkpointers)

Um **Checkpointer** salva snapshots do estado do grafo. Cada execução é vinculada a um `thread_id`.

```python
from langgraph.checkpoint.postgres import PostgresSaver

# O checkpointer gerencia o salvamento automático
checkpointer = PostgresSaver.from_conn_string(DB_URL)
graph = builder.compile(checkpointer=checkpointer)

# Para invocar mantendo o estado:
config = {"configurable": {"thread_id": "conversa-42"}}
graph.invoke({"messages": [...]}, config)
```

### Bibliotecas Suportadas
- `InMemorySaver`: Testes e desenvolvimento local.
- `SqliteSaver`: Protótipos e persistência local simples.
- `PostgresSaver`: **Padrão ouro para produção**.

---

## 2. Tipos de Memória

| Tipo | Escopo | Mecanismo | Uso comum |
|------|--------|-----------|-----------|
| **Short-term** | Uma thread | Checkpointer | Histórico da conversa atual |
| **Long-term** | Entre threads | Memory Store | Preferências do usuário, fatos |

### Long-term Memory (Store)
Permite que o agente "lembre" de coisas sobre o usuário de ontem para hoje.

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()
graph = builder.compile(checkpointer=checkpointer, store=store)

# Dentro de um node:
def update_profile(state, runtime):
    runtime.store.put(
        namespace=("users", state["user_id"]),
        key="prefs",
        value={"theme": "dark"}
    )
```

---

## 3. Durable Execution

Durable execution garante que o workflow possa ser retomado após um crash ou erro, sem repetir tarefas já concluídas (se estiverem em `@task`).

### Determinismo e Replay
Ao retomar, o LangGraph re-executa o código. **Atenção:** código não-determinístico (random, timestamps) deve estar dentro de uma `@task`.

```python
from langgraph.func import task

@task
def get_current_time():
    return datetime.now().isoformat()

# Em caso de replay, o valor de 'get_current_time' será 
# recuperado do checkpoint, mantendo o fluxo estável.
```

---

## 4. Time Travel (Replay & Edit)

Com o histórico de checkpoints, você pode:
1. **Visualizar o passado**: `graph.get_state_history(config)`
2. **Voltar no tempo**: Invoque o grafo passando um `checkpoint_id` específico.
3. **Editar o estado**: `graph.update_state(config, {"field": "new_value"})` para corrigir o rumo da conversa.

---

## Durability Modes (Produção)
- `"exit"`: Salva apenas ao final (melhor performance).
- `"sync"`: Salva em cada step (máxima segurança, ideal para transações).
- `"async"`: Salva em background (balanço ideal).
