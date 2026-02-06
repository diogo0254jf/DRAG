# Durable Execution

## O que é?

Durable Execution permite que workflows:
- **Persistam através de falhas** (crash, restart)
- **Rodem por longos períodos** (horas, dias)
- **Retomem exatamente de onde pararam**

## Requisitos

1. **Checkpointer habilitado**
2. **Thread ID especificado**
3. **Operações com side effects em @task** (Functional API) ou idempotentes

## Determinismo e Replay

Quando um workflow é resumido, LangGraph **re-executa** o código até o ponto onde parou, usando resultados salvos. Por isso:

### ❌ Problema: Non-deterministic code

```python
def bad_node(state):
    # Cada execução gera valor diferente!
    timestamp = datetime.now()  # ❌
    random_id = uuid.uuid4()    # ❌
    return {"id": random_id, "time": timestamp}
```

### ✅ Solução: Wrap em @task

```python
from langgraph.func import task

@task
def get_timestamp():
    return datetime.now().isoformat()

@task
def generate_id():
    return str(uuid.uuid4())

def good_node(state):
    # Resultados são salvos e reutilizados em replay
    timestamp = get_timestamp().result()
    id = generate_id().result()
    return {"id": id, "time": timestamp}
```

## Side Effects

### ❌ Problema: Side effects duplicados

```python
def bad_node(state):
    # Se node reexecutar, envia email duplicado!
    send_email(state["email"], state["message"])  # ❌
    return state
```

### ✅ Solução 1: Wrap em @task

```python
@task
def send_email_task(email, message):
    send_email(email, message)
    return {"sent": True}

def good_node(state):
    send_email_task(state["email"], state["message"]).result()
    return state
```

### ✅ Solução 2: Idempotência

```python
def idempotent_node(state):
    # Verificar se já foi enviado
    if not email_already_sent(state["email_id"]):
        send_email(state["email"], state["message"])
        mark_as_sent(state["email_id"])
    return state
```

## Usando Tasks em Nodes (Graph API)

```python
from langgraph.func import task
from langgraph.graph import StateGraph

@task
def call_api(url: str) -> str:
    return requests.get(url).text

def api_node(state):
    """Node que usa tasks para operações não-determinísticas"""
    # Tasks executam em paralelo
    futures = [call_api(url) for url in state["urls"]]
    results = [f.result() for f in futures]
    return {"results": results}

builder = StateGraph(State)
builder.add_node("api", api_node)
# ...
graph = builder.compile(checkpointer=checkpointer)
```

## Resumindo Workflows

### Após Interrupt

```python
from langgraph.types import Command

# Primeira execução para em interrupt
result = graph.invoke(input, config)

# Retomar
graph.invoke(Command(resume="user_response"), config)
```

### Após Falha/Crash

```python
# Workflow foi interrompido (crash, timeout, etc)
# Simplesmente invoke novamente com mesmo config
result = graph.invoke(None, config)  # None = continuar
# ou
result = graph.invoke(input, config)  # Novo input
```

### Starting Points

| Cenário | Como Retomar |
|---------|--------------|
| Interrupt | `Command(resume=value)` |
| Crash/falha | `invoke(None, config)` |
| Novo input na mesma thread | `invoke(new_input, config)` |
| Time travel | `invoke(None, config_with_checkpoint_id)` |

## Boas Práticas

1. **Sempre use task para API calls**
   ```python
   @task
   def llm_call(prompt):
       return llm.invoke(prompt)
   ```

2. **Identifique operações não-determinísticas**
   - `datetime.now()`
   - `uuid.uuid4()`
   - `random.random()`
   - API calls que podem retornar diferente

3. **Use idempotency keys para side effects**
   ```python
   def payment_node(state):
       # Mesmo key = não duplica
       process_payment(
           amount=state["amount"],
           idempotency_key=state["order_id"]
       )
   ```

4. **Teste replay manualmente**
   ```python
   # Simular crash
   result = graph.invoke(input, config)
   # Limpar memória do processo
   # Retomar
   result = graph.invoke(None, config)
   assert result == expected
   ```

5. **Escolha durability mode apropriado**
   - Development: `"exit"` (performance)
   - Production crítica: `"sync"` (segurança)
   - Production normal: `"async"` (balanço)
