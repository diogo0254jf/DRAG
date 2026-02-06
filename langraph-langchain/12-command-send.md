# Command e Send

## Command

`Command` permite combinar **atualização de estado** e **controle de fluxo** em uma única operação.

### Uso Básico

```python
from langgraph.types import Command
from typing import Literal

def my_node(state: State) -> Command[Literal["next_node"]]:
    return Command(
        update={"foo": "bar"},     # Atualização de estado
        goto="next_node"           # Próximo node
    )
```

### Vs Conditional Edges

```python
# COM conditional edges (tradicional)
def router(state: State) -> str:
    if state["condition"]:
        return "node_a"
    return "node_b"

def my_node(state: State):
    return {"result": "done"}

builder.add_node("my_node", my_node)
builder.add_conditional_edges("my_node", router)

# COM Command (mais conciso)
def my_node(state: State) -> Command[Literal["node_a", "node_b"]]:
    if state["condition"]:
        return Command(update={"result": "done"}, goto="node_a")
    return Command(update={"result": "done"}, goto="node_b")

builder.add_node("my_node", my_node)
# Não precisa de add_conditional_edges!
```

### Múltiplos Destinos

```python
def fan_out_node(state: State) -> Command[Literal["node_a", "node_b", "node_c"]]:
    return Command(
        update={"status": "processing"},
        goto=["node_a", "node_b", "node_c"]  # Executa todos em paralelo
    )
```

### Com HITL (Human-in-the-Loop)

```python
from langgraph.types import Command, interrupt

def approval_node(state: State):
    approval = interrupt({"action": state["action"]})
    
    if approval == "approved":
        return Command(update={"approved": True}, goto="execute")
    return Command(update={"approved": False}, goto="reject")
```

### Navegar para Parent Graph

```python
from langgraph.types import Command
from langgraph.constants import PARENT

def subgraph_node(state):
    if state["should_return"]:
        return Command(
            update={"result": "from_subgraph"},
            goto="parent_node",  # Nome do node no parent
            graph=PARENT         # Indica que é no parent
        )
    return state
```

### Cuidado com Static Edges

```python
# ⚠️ Command NÃO previne static edges de executar!
def node_a(state) -> Command[Literal["node_c"]]:
    return Command(goto="node_c")

builder.add_edge("node_a", "node_b")  # ← Ainda executa!
# Resultado: node_b E node_c são chamados
```

### Type Hints

Inclua os destinos possíveis no type hint:

```python
from typing import Literal
from langgraph.types import Command

# Correto: destinos declarados
def my_node(state) -> Command[Literal["node_a", "node_b"]]:
    if condition:
        return Command(goto="node_a")
    return Command(goto="node_b")
```

---

## Send

`Send` permite enviar **múltiplas instâncias** para um node com estados diferentes (map-reduce pattern).

### Uso Básico

```python
from langgraph.types import Send

def continue_to_jokes(state: OverallState):
    """Envia cada subject para o node generate_joke separadamente"""
    return [
        Send("generate_joke", {"subject": s}) 
        for s in state["subjects"]
    ]

builder.add_conditional_edges("node_a", continue_to_jokes)
```

### Map-Reduce Pattern

```python
from typing import Annotated
from operator import add
from langgraph.types import Send

class OverallState(TypedDict):
    subjects: list[str]
    jokes: Annotated[list[str], add]  # Reducer para acumular

class JokeState(TypedDict):
    subject: str

def generate_subjects(state: OverallState):
    return {"subjects": ["cats", "dogs", "programming"]}

def generate_joke(state: JokeState):
    joke = llm.invoke(f"Tell a joke about {state['subject']}")
    return {"jokes": [joke]}

def collect_jokes(state: OverallState):
    return {"final_output": "\n".join(state["jokes"])}

def fan_out(state: OverallState):
    return [Send("generate_joke", {"subject": s}) for s in state["subjects"]]

builder = StateGraph(OverallState)
builder.add_node("generate_subjects", generate_subjects)
builder.add_node("generate_joke", generate_joke)
builder.add_node("collect_jokes", collect_jokes)

builder.add_edge(START, "generate_subjects")
builder.add_conditional_edges("generate_subjects", fan_out, ["generate_joke"])
builder.add_edge("generate_joke", "collect_jokes")
builder.add_edge("collect_jokes", END)

graph = builder.compile()
```

### Diferença entre Send e Command

| Aspecto | Send | Command |
|---------|------|---------|
| **Propósito** | Fan-out/Map-reduce | Roteamento + update |
| **Uso** | Múltiplas instâncias paralelas | Uma próxima etapa |
| **Estado** | Cada Send tem estado próprio | Atualiza estado global |
| **Retorno** | Lista de Sends | Um Command |

### Combinando Send com Estado Global

```python
class State(TypedDict):
    items: list[str]
    results: Annotated[list[str], add]
    global_config: dict

class ItemState(TypedDict):
    item: str
    global_config: dict  # Passa config global para cada item

def process_items(state: State):
    return [
        Send("process_item", {
            "item": item, 
            "global_config": state["global_config"]
        }) 
        for item in state["items"]
    ]
```

### Send com Async

```python
async def parallel_processing(state):
    """Mesmo padrão funciona com async"""
    return [
        Send("async_node", {"data": d}) 
        for d in state["data_list"]
    ]
```
