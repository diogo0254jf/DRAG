# LangGraph Overview

## O que é LangGraph?

LangGraph é um framework para construir **agentes stateful** com controle sobre fluxo, estado e memória. Diferente de chains lineares, LangGraph modela workflows como **grafos direcionados**.

## Instalação

```bash
pip install -U langgraph
```

## Conceito Básico

```python
from langgraph.graph import StateGraph, MessagesState, START, END

def my_node(state: MessagesState):
    return {"messages": [{"role": "ai", "content": "hello"}]}

graph = StateGraph(MessagesState)
graph.add_node(my_node)
graph.add_edge(START, "my_node")
graph.add_edge("my_node", END)

app = graph.compile()
result = app.invoke({"messages": [{"role": "user", "content": "hi"}]})
```

## Benefícios Core

| Benefício | Descrição |
|-----------|-----------|
| **Durable Execution** | Agentes persistem através de falhas e podem rodar por longos períodos |
| **Human-in-the-loop** | Inspecionar e modificar estado do agente em qualquer ponto |
| **Memória Completa** | Short-term (durante sessão) e long-term (entre sessões) |
| **Debugging** | Visualização de traces e transições de estado com LangSmith |
| **Production-ready** | Infraestrutura escalável para workflows stateful |

## Ecossistema

- **LangGraph**: Framework core para grafos de agentes
- **LangSmith**: Observabilidade, traces, e deployment
- **LangChain**: Integrações e componentes para LLMs

## Dois Paradigmas

1. **Graph API**: Declarativo com `StateGraph`, nodes e edges explícitos
2. **Functional API**: Imperativo com `@entrypoint` e `@task` decorators
