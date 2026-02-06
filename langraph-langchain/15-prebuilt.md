# Prebuilt Components

LangGraph fornece componentes prontos para uso.

## create_react_agent

Cria um agente ReAct completo:

```python
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool

model = init_chat_model("gpt-4")

@tool
def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"Weather in {city}: 22°C, sunny"

@tool
def search(query: str) -> str:
    """Search the web."""
    return f"Results for: {query}"

# Criar agente
agent = create_react_agent(
    model=model,
    tools=[get_weather, search],
)

# Usar
result = agent.invoke({
    "messages": [{"role": "user", "content": "What's the weather in Paris?"}]
})
```

### Com System Prompt

```python
agent = create_react_agent(
    model=model,
    tools=tools,
    prompt="You are a helpful travel assistant. Always be concise."
)
```

### Com Checkpointer

```python
from langgraph.checkpoint.memory import InMemorySaver

agent = create_react_agent(
    model=model,
    tools=tools,
    checkpointer=InMemorySaver()
)

config = {"configurable": {"thread_id": "user-123"}}
result = agent.invoke({"messages": [msg]}, config)
```

### Com State Modifier

```python
def add_system_message(state):
    """Add system message to history."""
    from langchain_core.messages import SystemMessage
    return [SystemMessage("Be helpful")] + state["messages"]

agent = create_react_agent(
    model=model,
    tools=tools,
    state_modifier=add_system_message
)
```

## ToolNode

Executa tools baseado em tool_calls:

```python
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, MessagesState

tool_node = ToolNode([get_weather, search])

builder = StateGraph(MessagesState)
builder.add_node("tools", tool_node)
```

## tools_condition

Roteador para decidir se chama tools ou finaliza:

```python
from langgraph.prebuilt import tools_condition

builder.add_conditional_edges(
    "agent",
    tools_condition,
    # Se LLM retornou tool_calls → "tools"
    # Se não → END
)
```

### Mapeamento Customizado

```python
builder.add_conditional_edges(
    "agent",
    tools_condition,
    {
        "tools": "my_tools_node",  # Nome customizado
        END: "final_node"          # Redirecionar
    }
)
```

## InjectedState

Injetar estado do grafo em tools:

```python
from langgraph.prebuilt import InjectedState
from typing import Annotated

@tool
def remember_context(
    query: str,
    state: Annotated[dict, InjectedState]
) -> str:
    """Tool that can access graph state."""
    messages = state.get("messages", [])
    return f"Context has {len(messages)} messages"
```

## InjectedStore

Injetar store em tools:

```python
from langgraph.prebuilt import InjectedStore
from langgraph.store.base import BaseStore
from typing import Annotated

@tool
def save_memory(
    fact: str,
    store: Annotated[BaseStore, InjectedStore]
) -> str:
    """Save to long-term memory."""
    store.put(
        namespace=("memories",),
        key=str(uuid.uuid4()),
        value={"fact": fact}
    )
    return "Saved!"
```

## MessagesState

Estado pré-definido para chat:

```python
from langgraph.graph import MessagesState

# Equivalente a:
class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
```

### Estender MessagesState

```python
from langgraph.graph import MessagesState

class MyState(MessagesState):
    # Adicionar campos extras
    user_id: str
    context: dict
```

## add_messages Reducer

Reducer built-in para mensagens:

```python
from langgraph.graph.message import add_messages
from typing import Annotated

class State(TypedDict):
    messages: Annotated[list, add_messages]
```

Comportamento:
- Adiciona novas mensagens
- Atualiza mensagens existentes pelo ID
- Remove mensagens com `RemoveMessage`

## RemoveMessage

Remover mensagens do histórico:

```python
from langchain_core.messages import RemoveMessage

def summarize_node(state):
    # Manter apenas 2 últimas mensagens
    to_remove = [
        RemoveMessage(id=m.id) 
        for m in state["messages"][:-2]
    ]
    return {"messages": to_remove}
```

## Patterns com Prebuilt

### Agente Básico

```python
from langgraph.prebuilt import create_react_agent

agent = create_react_agent(model, tools)
result = agent.invoke({"messages": [user_message]})
```

### Agente com Memória

```python
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.postgres import PostgresSaver

agent = create_react_agent(
    model, 
    tools,
    checkpointer=PostgresSaver.from_conn_string(DB_URL)
)

config = {"configurable": {"thread_id": thread_id}}
result = agent.invoke({"messages": [msg]}, config)
```

### Agente com Store

```python
from langgraph.prebuilt import create_react_agent
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

agent = create_react_agent(
    model,
    tools,
    store=store
)
```
