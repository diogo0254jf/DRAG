# 04 - Advanced Workflows (Streaming, Subgraphs, Commands)

Para interfaces complexas e escalabilidade, o LangGraph oferece controle refinado sobre streaming, modularização e controle de fluxo.

## 1. Streaming

O LangGraph suporta 5 modos de streaming principais:

| Modo | O que retorna | Caso de uso |
|------|---------------|-------------|
| `values` | Estado completo | Debugging e sync de UI |
| `updates` | Apenas o que mudou | Notificações de progresso |
| `messages` | **Tokens do LLM (tempo real)** | Chat UX fluido |
| `custom` | Dados via `get_stream_writer` | Barras de progresso customizadas |
| `debug` | Logs internos do grafo | Desenvolvimento profundo |

```python
# Exemplo de streaming de tokens
async for msg_chunk, metadata in graph.astream(input, stream_mode="messages"):
    if msg_chunk.content:
        print(msg_chunk.content, end="")
```

---

## 2. Subgraphs (Modularização)

Subgrafos permitem que você isole agências ou lógica complexa. Um subgrafo pode ter seu próprio schema de estado.

- **Encapsulamento**: Variáveis do subgrafo não poluem o grafo pai.
- **Multi-agentes**: Cada agente (Pesquisador, Escritor, Revisor) pode ser um subgrafo focado em sua tarefa.

```python
# Adicione um grafo compilado como se fosse um node
builder.add_node("researcher_agent", compiled_researcher_subgraph)
```

---

## 3. Command e Send (Controle Dinâmico)

### Command
Permite que um node controle para onde o grafo vai a seguir, ignorando edges estáticas.

```python
from langgraph.types import Command

def my_node(state):
    # Atualiza o estado E pula para outro node dinamicamente
    return Command(update={"status": "ok"}, goto="special_node")
```

### Send (Map-Reduce)
Permite disparar múltiplas instâncias de um node em paralelo. Útil para processar uma lista de itens separadamente.

```python
from langgraph.types import Send

def fan_out(state):
    # Cria uma tarefa paralela para cada documento
    return [Send("process_doc", {"doc": d}) for d in state["docs"]]
```

---

## 4. Human-in-the-Loop (Interrupts)

Pausar a execução para revisão humana é nativo.

```python
from langgraph.types import interrupt

def sensitive_task(state):
    # Pausa e aguarda resposta externa
    confirm = interrupt({"msg": "Aprovar envio?"})
    if confirm == "yes":
        send_data()
```

Para retomar: `graph.invoke(Command(resume="yes"), config)`
