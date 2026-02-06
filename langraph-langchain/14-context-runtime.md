# Context e Runtime

## Static Runtime Context

Passe contexto que não muda durante a execução:

```python
from dataclasses import dataclass

@dataclass
class ContextSchema:
    user_name: str
    user_id: str
    tenant: str

# Invocar com context
graph.invoke(
    {"messages": [{"role": "user", "content": "hi!"}]},
    context={"user_name": "John", "user_id": "123", "tenant": "acme"}
)
```

## Acessar Context em Nodes

```python
from langgraph.runtime import Runtime

def my_node(state: State, runtime: Runtime[ContextSchema]):
    user_name = runtime.context.user_name
    user_id = runtime.context.user_id
    
    return {"greeting": f"Hello, {user_name}!"}
```

## Acessar Context em Tools

```python
from langchain.tools import tool, ToolRuntime

@tool
def get_user_email(
    query: str,
    runtime: ToolRuntime[ContextSchema]
) -> str:
    """Get user email based on context."""
    user_id = runtime.context.user_id
    email = db.get_email(user_id)
    return email
```

## Context em Agents

```python
from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest

@dataclass
class ContextSchema:
    user_name: str

@dynamic_prompt
def personalized_prompt(request: ModelRequest) -> str:
    user_name = request.runtime.context.user_name
    return f"You are an assistant for {user_name}."

agent = create_agent(
    model="gpt-4",
    tools=[get_weather],
    middleware=[personalized_prompt],
    context_schema=ContextSchema
)

agent.invoke(
    {"messages": [{"role": "user", "content": "hi"}]},
    context=ContextSchema(user_name="John")
)
```

## Runtime Properties

O objeto `Runtime` fornece acesso a:

```python
def my_node(state, runtime: Runtime):
    # Context passado no invoke
    runtime.context
    
    # Store para long-term memory
    runtime.store
    
    # Checkpointer para persistência
    runtime.checkpointer
    
    # Config da execução
    runtime.config
```

## Dynamic Context (Cross-Conversation)

Para contexto que muda ao longo de múltiplas conversas:

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

# Grafo com store
graph = builder.compile(store=store)

def my_node(state, runtime: Runtime):
    # Buscar contexto dinâmico do store
    user_prefs = runtime.store.search(
        namespace=("user", runtime.context.user_id),
        query="preferences"
    )
    
    # Atualizar contexto
    runtime.store.put(
        namespace=("user", runtime.context.user_id),
        key="last_seen",
        value={"timestamp": datetime.now()}
    )
    
    return state
```

## Pattern Comum: User Context

```python
@dataclass
class UserContext:
    user_id: str
    locale: str
    timezone: str
    permissions: list[str]

def authorized_node(state, runtime: Runtime[UserContext]):
    if "admin" not in runtime.context.permissions:
        raise PermissionError("Admin required")
    
    # Lógica admin...
    return state

# Middleware de autorização
config = {"configurable": {"thread_id": "thread-1"}}

graph.invoke(
    {"request": "delete_all"},
    config=config,
    context=UserContext(
        user_id="user-123",
        locale="pt-BR",
        timezone="America/Sao_Paulo",
        permissions=["read", "write"]
    )
)
```
