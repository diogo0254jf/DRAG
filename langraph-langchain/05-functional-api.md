# Functional API - @entrypoint e @task

## Quando Usar

| Graph API | Functional API |
|-----------|----------------|
| Workflows complexos com múltiplos caminhos | Workflows lineares simples |
| Visualização importante | Controle de fluxo Python puro |
| Estado compartilhado entre nodes | Estado local nas funções |

## Conceitos Básicos

- **@entrypoint**: Define o ponto de entrada do workflow
- **@task**: Define unidades de trabalho checkpointáveis

## Exemplo Básico

```python
from langgraph.func import entrypoint, task
from langgraph.checkpoint.memory import InMemorySaver

@task
def fetch_data(url: str) -> str:
    """Task: resultado é salvo em checkpoint"""
    return requests.get(url).text

@task
def process_data(data: str) -> dict:
    """Task: pode ser resumida se falhar após fetch"""
    return {"processed": data.upper()}

@entrypoint(checkpointer=InMemorySaver())
def my_workflow(urls: list[str]) -> list[dict]:
    # Tasks executam em paralelo
    futures = [fetch_data(url) for url in urls]
    data = [f.result() for f in futures]
    
    results = [process_data(d).result() for d in data]
    return results

# Executar
config = {"configurable": {"thread_id": "workflow-1"}}
result = my_workflow.invoke(["http://example.com"], config)
```

## @entrypoint

### Definição

```python
@entrypoint(checkpointer=checkpointer)
def workflow(input_data, *, previous=None):
    # previous: estado salvo anteriormente (short-term memory)
    if previous:
        return continue_from(previous)
    return start_fresh(input_data)
```

### Parâmetros Injetáveis

```python
@entrypoint()
def workflow(
    input_data,
    *,
    config: RunnableConfig,  # Configuração runtime
    store: BaseStore,         # Memory store
    previous = None           # Estado anterior
):
    thread_id = config["configurable"]["thread_id"]
    memories = store.search(...)
    return result
```

### Short-term Memory

```python
@entrypoint(checkpointer=checkpointer)
def chat(message: str, *, previous: list = None) -> list:
    messages = previous or []
    messages.append({"role": "user", "content": message})
    
    response = llm.invoke(messages)
    messages.append({"role": "assistant", "content": response})
    
    # Retornar para próxima invocação
    return entrypoint.final(
        value=response,        # Valor retornado
        save=messages          # Salvo para 'previous'
    )
```

## @task

### Definição

```python
@task
def my_task(arg1: str, arg2: int) -> str:
    """Resultado é checkpointado automaticamente"""
    return expensive_operation(arg1, arg2)
```

### Execução

```python
# Sincrono
result = my_task("a", 1).result()

# Paralelo
futures = [my_task(url) for url in urls]
results = [f.result() for f in futures]
```

### Quando Usar Task

1. **Operações com side effects** (API calls, file writes)
2. **Operações não-determinísticas** (random, timestamps)
3. **Operações caras** (LLM calls, computação pesada)

```python
@task
def call_external_api(data):
    """Resultado cachado - não reexecuta em resume"""
    return requests.post("https://api.example.com", json=data)

@task  
def generate_response(prompt):
    """LLM call não será repetida em resume"""
    return llm.invoke(prompt)
```

## Comparação: Graph API vs Functional API

```python
# Graph API
class State(TypedDict):
    urls: list[str]
    results: list[str]

def fetch_node(state):
    results = [requests.get(url).text for url in state["urls"]]
    return {"results": results}

builder = StateGraph(State)
builder.add_node("fetch", fetch_node)
builder.add_edge(START, "fetch")
builder.add_edge("fetch", END)
graph = builder.compile(checkpointer=checkpointer)

# Functional API (equivalente)
@task
def fetch(url):
    return requests.get(url).text

@entrypoint(checkpointer=checkpointer)
def workflow(urls):
    futures = [fetch(url) for url in urls]
    return [f.result() for f in futures]
```

## Boas Práticas

1. **Use @task para idempotência**: Tasks não reexecutam em resume
2. **Mantenha tasks atômicas**: Uma responsabilidade por task
3. **Não misture side effects fora de tasks**: Podem reexecutar
4. **Use Functional API para fluxos simples**: Menos boilerplate
5. **Use Graph API para fluxos complexos**: Melhor visualização e debugging
