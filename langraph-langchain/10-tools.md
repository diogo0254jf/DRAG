# Tools e ToolNode

## Criando Tools

### Definição Básica

```python
from langchain.tools import tool

@tool
def search_database(query: str, limit: int = 10) -> str:
    """Search the customer database for records matching the query.
    
    Args:
        query: Search terms to look for
        limit: Maximum number of results to return
    """
    return f"Found {limit} results for '{query}'"
```

### Nome e Descrição Customizados

```python
@tool("web_search")  # Nome customizado
def search(query: str) -> str:
    """Search the web for information."""
    return f"Results for: {query}"

@tool("calculator", description="Performs arithmetic calculations.")
def calc(expression: str) -> str:
    """Evaluate mathematical expressions."""
    return str(eval(expression))
```

### Schema Avançado com Pydantic

```python
from pydantic import BaseModel, Field
from typing import Literal

class WeatherInput(BaseModel):
    """Input for weather queries."""
    location: str = Field(description="City name or coordinates")
    units: Literal["celsius", "fahrenheit"] = Field(
        default="celsius",
        description="Temperature unit preference"
    )
    include_forecast: bool = Field(
        default=False,
        description="Include 5-day forecast"
    )

@tool(args_schema=WeatherInput)
def get_weather(
    location: str, 
    units: str = "celsius", 
    include_forecast: bool = False
) -> str:
    """Get current weather and optional forecast."""
    temp = 22 if units == "celsius" else 72
    return f"Weather in {location}: {temp}°{units[0].upper()}"
```

## Argumentos Reservados

Tools podem receber contexto especial:

```python
from langchain_core.runnables import RunnableConfig
from langchain.tools import tool, ToolRuntime

@tool
def tool_with_config(query: str, config: RunnableConfig) -> str:
    """Tool that accesses configuration."""
    thread_id = config["configurable"]["thread_id"]
    return f"Thread: {thread_id}"

@tool
def tool_with_runtime(query: str, runtime: ToolRuntime) -> str:
    """Tool that accesses runtime context."""
    user_id = runtime.context.user_id
    store = runtime.store
    return f"User: {user_id}"
```

## ToolNode

Executa tools automaticamente baseado em tool_calls do LLM:

```python
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, MessagesState, START, END

@tool
def search(query: str) -> str:
    """Search for information."""
    return f"Results for: {query}"

@tool
def calculator(expression: str) -> str:
    """Evaluate a math expression."""
    return str(eval(expression))

# Criar ToolNode
tool_node = ToolNode([search, calculator])

# Usar no grafo
builder = StateGraph(MessagesState)
builder.add_node("tools", tool_node)
```

### Error Handling

```python
from langgraph.prebuilt import ToolNode

# Default: captura erros de invocação
tool_node = ToolNode(tools)

# Capturar todos os erros e retornar mensagem para LLM
tool_node = ToolNode(tools, handle_tool_errors=True)

# Mensagem de erro customizada
tool_node = ToolNode(
    tools, 
    handle_tool_errors="Something went wrong, please try again."
)

# Handler customizado
def handle_error(e: ValueError) -> str:
    return f"Invalid input: {e}"

tool_node = ToolNode(tools, handle_tool_errors=handle_error)

# Apenas tipos específicos de exceção
tool_node = ToolNode(
    tools, 
    handle_tool_errors=(ValueError, TypeError)
)
```

## tools_condition

Roteador que decide se deve chamar tools ou finalizar:

```python
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, MessagesState, START, END

def call_llm(state: MessagesState):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

builder = StateGraph(MessagesState)
builder.add_node("llm", call_llm)
builder.add_node("tools", ToolNode(tools))

builder.add_edge(START, "llm")
builder.add_conditional_edges("llm", tools_condition)  # → "tools" ou END
builder.add_edge("tools", "llm")

graph = builder.compile()
```

## Acessando Contexto em Tools

### Short-term Memory (State)

```python
from langgraph.prebuilt import InjectedState
from typing import Annotated

@tool
def get_context(
    query: str,
    state: Annotated[dict, InjectedState]
) -> str:
    """Tool that accesses graph state."""
    history = state.get("messages", [])
    return f"Query: {query}, History length: {len(history)}"
```

### Long-term Memory (Store)

```python
from langgraph.store.base import BaseStore
from langgraph.prebuilt import InjectedStore
from typing import Annotated

@tool
def remember_fact(
    fact: str,
    store: Annotated[BaseStore, InjectedStore],
    user_id: str
) -> str:
    """Save a fact to long-term memory."""
    store.put(
        namespace=("user", user_id),
        key=str(uuid.uuid4()),
        value={"fact": fact}
    )
    return "Fact saved!"
```

### Stream Writer

```python
from langgraph.config import get_stream_writer

@tool
def process_with_progress(data: str) -> str:
    """Process data with progress updates."""
    writer = get_stream_writer()
    
    writer({"progress": 0, "status": "Starting..."})
    result = step_1(data)
    
    writer({"progress": 50, "status": "Halfway..."})
    result = step_2(result)
    
    writer({"progress": 100, "status": "Done!"})
    return result
```

## Pattern: Agent com Tools

```python
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, MessagesState, START, END

model = init_chat_model("gpt-4")
tools = [search, calculator, get_weather]
model_with_tools = model.bind_tools(tools)

def agent_node(state: MessagesState):
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}

builder = StateGraph(MessagesState)
builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(tools))

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)
builder.add_edge("tools", "agent")

graph = builder.compile()
```
