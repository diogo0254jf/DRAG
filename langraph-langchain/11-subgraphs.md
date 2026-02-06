# Subgraphs

Subgraphs permitem modularizar workflows complexos, encapsulando lógica em grafos separados.

## Duas Abordagens

1. **Invocar grafo dentro de um node**: Transformação de estado explícita
2. **Adicionar grafo como node**: Estado compartilhado automático

## 1. Invocar Grafo de Dentro de um Node

Útil quando states são **diferentes** entre parent e subgraph:

```python
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START

# Subgraph com estado próprio
class SubgraphState(TypedDict):
    bar: str
    baz: str

def subgraph_node_1(state: SubgraphState):
    return {"baz": "baz"}

def subgraph_node_2(state: SubgraphState):
    return {"bar": state["bar"] + state["baz"]}

subgraph_builder = StateGraph(SubgraphState)
subgraph_builder.add_node(subgraph_node_1)
subgraph_builder.add_node(subgraph_node_2)
subgraph_builder.add_edge(START, "subgraph_node_1")
subgraph_builder.add_edge("subgraph_node_1", "subgraph_node_2")
subgraph = subgraph_builder.compile()

# Parent graph com estado diferente
class ParentState(TypedDict):
    foo: str

def call_subgraph(state: ParentState):
    # Transformar estado para subgraph
    subgraph_output = subgraph.invoke({"bar": state["foo"]})
    # Transformar resposta de volta
    return {"foo": subgraph_output["bar"]}

builder = StateGraph(ParentState)
builder.add_node("node_1", call_subgraph)
builder.add_edge(START, "node_1")
graph = builder.compile()
```

## 2. Adicionar Grafo como Node

Útil quando states **compartilham campos**:

```python
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START

# Subgraph com estado que inclui campo compartilhado
class SubgraphState(TypedDict):
    foo: str  # Compartilhado com parent
    bar: str  # Privado do subgraph

def subgraph_node_1(state: SubgraphState):
    return {"bar": "bar"}

def subgraph_node_2(state: SubgraphState):
    return {"foo": state["foo"] + state["bar"]}

subgraph_builder = StateGraph(SubgraphState)
subgraph_builder.add_node(subgraph_node_1)
subgraph_builder.add_node(subgraph_node_2)
subgraph_builder.add_edge(START, "subgraph_node_1")
subgraph_builder.add_edge("subgraph_node_1", "subgraph_node_2")
subgraph = subgraph_builder.compile()

# Parent graph
class ParentState(TypedDict):
    foo: str

def node_1(state: ParentState):
    return {"foo": "hi! " + state["foo"]}

builder = StateGraph(ParentState)
builder.add_node("node_1", node_1)
builder.add_node("node_2", subgraph)  # Subgraph como node!
builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
graph = builder.compile()

# Output
for chunk in graph.stream({"foo": "foo"}):
    print(chunk)
# {'node_1': {'foo': 'hi! foo'}}
# {'node_2': {'foo': 'hi! foobar'}}
```

## Persistência com Subgraphs

Subgraphs podem usar o checkpointer do parent:

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()

# Subgraph
subgraph = subgraph_builder.compile()  # Sem checkpointer próprio

# Parent com checkpointer
graph = builder.compile(checkpointer=checkpointer)

# Subgraph herda checkpointer do parent automaticamente
```

## Visualizar Estado do Subgraph

```python
config = {"configurable": {"thread_id": "1"}}
result = graph.invoke({"foo": "test"}, config)

# Ver estado incluindo subgraphs
state = graph.get_state(config, subgraphs=True)
print(state)
```

## Streaming de Subgraphs

```python
# Incluir outputs de subgraphs no stream
for chunk in graph.stream(
    {"foo": "test"},
    stream_mode="updates",
    subgraphs=True
):
    print(chunk)
```

Saída inclui namespace do subgraph:

```python
((), {'node_1': {'foo': 'hi! test'}})
(('node_2:abc123',), {'subgraph_node_1': {'bar': 'bar'}})
(('node_2:abc123',), {'subgraph_node_2': {'foo': 'hi! testbar'}})
((), {'node_2': {'foo': 'hi! testbar'}})
```

## Navegar para Node do Parent

Do subgraph, use `Command` para ir ao parent:

```python
from langgraph.types import Command
from langgraph.constants import PARENT

def subgraph_node(state):
    if state["should_exit"]:
        # Navegar para node no parent graph
        return Command(
            update={"result": "done"},
            goto=PARENT,  # Volta ao parent
            graph=PARENT
        )
    return state
```

## Casos de Uso

1. **Multi-agent**: Cada agente é um subgraph
2. **Modularização**: Separar lógica complexa
3. **Reutilização**: Subgraph pode ser usado em múltiplos parents
4. **Encapsulamento**: Estado privado do subgraph

## Pattern: Multi-Agent com Subgraphs

```python
# Agente pesquisador
researcher_builder = StateGraph(AgentState)
researcher_builder.add_node("research", research_node)
researcher_builder.add_node("tools", ToolNode([search_tool]))
# ... edges
researcher = researcher_builder.compile()

# Agente escritor
writer_builder = StateGraph(AgentState)
writer_builder.add_node("write", write_node)
writer_builder.add_node("tools", ToolNode([editor_tool]))
# ... edges
writer = writer_builder.compile()

# Orquestrador
class OrchestratorState(TypedDict):
    task: str
    research: str
    draft: str

def router(state):
    if not state.get("research"):
        return "researcher"
    return "writer"

orchestrator = StateGraph(OrchestratorState)
orchestrator.add_node("researcher", researcher)
orchestrator.add_node("writer", writer)
orchestrator.add_conditional_edges(START, router)
# ...
graph = orchestrator.compile()
```
