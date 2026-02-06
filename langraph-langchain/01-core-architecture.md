# 01 - Core Architecture & Graph Creation

O LangGraph modela workflows como **grafos direcionados e stateful**. Existem dois paradigmas principais para construir esses grafos: **Graph API** e **Functional API**.

## 1. Graph API (StateGraph)

Ideal para workflows complexos com múltiplos caminhos, ciclos e onde a visualização do fluxo é importante.

### Definindo o Estado
O estado é o schema que flui pelo grafo. Use `TypedDict` com **Reducers** para definir como os campos são atualizados.

```python
from typing import TypedDict, Annotated
from langgraph.graph import add_messages

class State(TypedDict):
    # Sobrescreve o valor anterior (default)
    query: str
    # Acumula mensagens (reducer add_messages)
    messages: Annotated[list, add_messages]
    # Soma valores (reducer customizado)
    api_calls: Annotated[int, lambda x, y: x + y]
```

> [!TIP]
> Use `MessagesState` como base para chatbots, pois ele já inclui o campo `messages` com o reducer correto.

### Construindo o Grafo
Nodes são funções Python, e Edges conectam esses nodes.

```python
from langgraph.graph import StateGraph, START, END

builder = StateGraph(State)

# Nodes: Recebem state, retornam atualizações
def retrieve(state: State):
    return {"messages": ["Contexto recuperado..."]}

def generate(state: State):
    return {"messages": ["Resposta gerada!"]}

builder.add_node("retrieve", retrieve)
builder.add_node("generate", generate)

# Edges: START/END e condicionais
builder.add_edge(START, "retrieve")
builder.add_edge("retrieve", "generate")
builder.add_edge("generate", END)

graph = builder.compile()
```

---

## 2. Functional API (@entrypoint e @task)

Ideal para workflows lineares, imperativos, ou onde o controle de fluxo via Python puro (if/for) é preferível.

### Conceitos
- **@entrypoint**: Define o ponto de entrada e gerencia o checkpointer.
- **@task**: Define unidades de trabalho checkpointáveis (não re-executam em caso de erro/resume).

```python
from langgraph.func import entrypoint, task

@task
def fetch_data(url: str):
    return requests.get(url).text

@entrypoint(checkpointer=InMemorySaver())
def workflow(urls: list[str]):
    # Paralelismo nativo com Python
    futures = [fetch_data(url) for url in urls]
    results = [f.result() for f in futures]
    return results
```

---

## 3. Resumo: Qual usar?

| Característica | Graph API | Functional API |
|----------------|-----------|----------------|
| **Fluxo** | Declarativo (Nodes/Edges) | Imperativo (Python puro) |
| **Estado** | Global (compartilhado) | Local (passagem de args) |
| **Complexidade** | Alta (ciclos, multi-agente) | Baixa/Média (lineares) |
| **Visualização** | Excelente | Limitada |

---

## Boas Práticas
1. **Nodes Atômicos**: Cada node deve ter apenas uma responsabilidade.
2. **Retorne apenas o delta**: Nodes devem retornar apenas os campos que mudaram no estado.
3. **Idempotência**: Garanta que seus nodes (especialmente com side-effects) possam ser re-executados com segurança.
