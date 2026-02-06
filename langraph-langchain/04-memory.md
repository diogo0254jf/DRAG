# Memory - Short-term & Long-term

## Tipos de Memória

| Tipo | Escopo | Mecanismo | Uso |
|------|--------|-----------|-----|
| **Short-term** | Dentro de uma thread | Checkpointer | Histórico de conversa |
| **Long-term** | Entre threads | Memory Store | Preferências, fatos sobre usuário |

## Short-term Memory (Histórico)

### Com MessagesState

```python
from langgraph.graph import MessagesState

class State(MessagesState):
    pass  # messages já tem reducer add_messages

# Mensagens são automaticamente acumuladas
def chat_node(state: State):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}
```

### Gerenciando Tamanho do Histórico

```python
from langchain_core.messages import trim_messages

def chat_node(state: State):
    # Manter últimas N mensagens ou tokens
    trimmed = trim_messages(
        state["messages"],
        max_tokens=2000,
        token_counter=len,  # ou tiktoken
        strategy="last",    # mantém mais recentes
        include_system=True # preserva system message
    )
    return {"messages": [llm.invoke(trimmed)]}
```

### Sumarização de Histórico

```python
def summarize_node(state: State):
    if len(state["messages"]) > 10:
        summary = llm.invoke(
            f"Summarize this conversation: {state['messages']}"
        )
        # Substituir mensagens antigas por resumo
        return {
            "messages": [
                SystemMessage(f"Previous summary: {summary}"),
                *state["messages"][-3:]  # últimas 3
            ]
        }
    return state
```

## Long-term Memory

### Tipos Conceituais

| Tipo | Descrição | Exemplo |
|------|-----------|---------|
| **Semantic** | Fatos e conhecimento | "User prefers dark mode" |
| **Episodic** | Experiências passadas | "In conversation X, user asked about Y" |
| **Procedural** | Regras e procedimentos | "When user says 'urgent', prioritize" |

### Implementação com Store

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

def extract_memories(state, runtime):
    """Extrair fatos importantes e salvar"""
    facts = llm.invoke(
        f"Extract key facts about the user from: {state['messages']}"
    )
    
    for fact in facts:
        runtime.store.put(
            namespace=("user", state["user_id"], "facts"),
            key=str(uuid.uuid4()),
            value={"fact": fact, "timestamp": datetime.now()}
        )
    
    return state

def recall_memories(state, runtime):
    """Recuperar memórias relevantes"""
    memories = runtime.store.search(
        namespace=("user", state["user_id"], "facts"),
        query=state["messages"][-1].content,
        limit=5
    )
    
    context = "\n".join(m.value["fact"] for m in memories)
    return {"memory_context": context}
```

### Escrita de Memórias

**Hot Path** (durante execução):
- Agente decide salvar antes de responder
- Mais controle, mas adiciona latência

**Background** (assíncrono):
- Processo separado analisa conversas
- Não impacta latência
- Pode perder contexto imediato

```python
# Hot path - no próprio node
def respond_and_remember(state, runtime):
    # Responder
    response = llm.invoke(state["messages"])
    
    # Salvar memória (hot path)
    runtime.store.put(...)
    
    return {"messages": [response]}

# Background - com @task
from langgraph.func import task

@task
def background_memory_extraction(messages, store, user_id):
    """Executado em background"""
    facts = extract_facts(messages)
    for fact in facts:
        store.put(namespace=("user", user_id), ...)
```

## Boas Práticas

1. **Use namespaces hierárquicos**: `("user", user_id, "preferences")`
2. **Indexe para busca semântica** quando tiver muitas memórias
3. **Adicione timestamps** para poder fazer decay/cleanup
4. **Separe fatos de opiniões** na estrutura de memória
5. **Teste hot path vs background** para seu caso de uso
