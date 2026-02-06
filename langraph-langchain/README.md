# LangGraph & LangChain - Documentação de Referência

Esta pasta contém documentação abrangente sobre LangGraph, coletada e organizada para servir como referência rápida em conversas futuras.

## Índice

### Fundamentos
| Arquivo | Conteúdo |
|---------|----------|
| [01-overview.md](./01-overview.md) | Visão geral do LangGraph, instalação e conceitos básicos |
| [02-state-graph.md](./02-state-graph.md) | Graph API: StateGraph, State, Nodes, Edges |
| [03-persistence.md](./03-persistence.md) | Checkpointers, Threads, Memory Store |
| [04-memory.md](./04-memory.md) | Short-term e Long-term Memory |

### APIs e Padrões
| Arquivo | Conteúdo |
|---------|----------|
| [05-functional-api.md](./05-functional-api.md) | @entrypoint e @task decorators |
| [06-interrupts-hitl.md](./06-interrupts-hitl.md) | Human-in-the-loop com interrupt() |
| [07-durable-execution.md](./07-durable-execution.md) | Determinismo, replay e resuming |
| [08-boas-praticas.md](./08-boas-praticas.md) | Patterns, testing e checklist de produção |

### Funcionalidades Avançadas
| Arquivo | Conteúdo |
|---------|----------|
| [09-streaming.md](./09-streaming.md) | 5 modos de streaming, tokens LLM, custom data |
| [10-tools.md](./10-tools.md) | @tool, ToolNode, tools_condition, error handling |
| [11-subgraphs.md](./11-subgraphs.md) | Modularização com subgraphs, multi-agent |
| [12-command-send.md](./12-command-send.md) | Command para fluxo, Send para map-reduce |
| [13-agentic-rag.md](./13-agentic-rag.md) | Tutorial completo de Agentic RAG |

### Produção
| Arquivo | Conteúdo |
|---------|----------|
| [14-context-runtime.md](./14-context-runtime.md) | Context schema, Runtime, injeção de dados |
| [15-prebuilt.md](./15-prebuilt.md) | create_react_agent, ToolNode, MessagesState |
| [16-deployment.md](./16-deployment.md) | PostgresSaver, FastAPI, LangSmith, checklist |

## Quick Reference

### Instalação
```bash
pip install -U langgraph
pip install langgraph-checkpoint-postgres  # Produção
```

### Grafo Mínimo
```python
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.postgres import PostgresSaver

def chat(state: MessagesState):
    return {"messages": [llm.invoke(state["messages"])]}

builder = StateGraph(MessagesState)
builder.add_node("chat", chat)
builder.add_edge(START, "chat")
builder.add_edge("chat", END)

graph = builder.compile(checkpointer=PostgresSaver.from_conn_string(DB_URL))
```

### Invocação com Persistência
```python
config = {"configurable": {"thread_id": "user-123"}}
result = graph.invoke({"messages": [user_message]}, config)
```

## Fonte
Documentação oficial: https://docs.langchain.com/oss/python/langgraph/overview
