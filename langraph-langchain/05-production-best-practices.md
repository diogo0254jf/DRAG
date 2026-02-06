# 05 - Production & Best Practices

Transformar um protótipo LangGraph em um sistema de produção resiliente requer atenção à observabilidade, infraestrutura e tratamento de erros.

## 1. Infraestrutura de Produção

### Persistência Real
Nunca use `InMemorySaver` em produção. Utilize checkpointers robustos:
- **PostgreSQL**: `PostgresSaver` (Recomendado).
- **Redis**: `RedisSaver` (Para alta frequência de leitura/escrita).

### Memory Store Semântico
Use o `PostgresStore` com suporte a indexação vetorial para buscas semânticas em memórias de longo prazo.

---

## 2. Observabilidade (LangSmith)

O LangSmith é essencial para depurar grafos complexos. Ele permite visualizar exatamente o que aconteceu em cada node e cada chamada de LLM.

```python
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "ls__..."
```

---

## 3. Resiliência e Error Handling

### Retry Policies
Configure políticas de retentativa automáticas para falhas de rede ou de API.

```python
@task(retry_policy={"max_attempts": 3, "backoff": 2.0})
def call_flaky_api(data):
    ...
```

### Fallbacks
Sempre tenha um plano B (ex: um modelo menor ou uma resposta padrão) quando o LLM principal falhar.

---

## 4. Integração com Web APIs (FastAPI)

Padrão para expor seu grafo como uma API:

```python
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    config = {"configurable": {"thread_id": request.conversation_id}}
    result = await graph.ainvoke({"messages": [request.message]}, config)
    return {"response": result["messages"][-1].content}
```

---

## 5. Checklist de Lançamento

1. [ ] **Recusion Limit**: Aumente `recursion_limit` se seu grafo tiver muitos loops.
2. [ ] **Timeouts**: Configure timeouts em todas as chamadas de ferramentas e LLMs.
3. [ ] **Sanitização de Estado**: Garanta que dados sensíveis (senhas, keys) não fiquem persistidos no estado sem necessidade.
4. [ ] **Monitoramento de Custos**: Acompanhe o uso de tokens por thread/usuário.
5. [ ] **Testes de Replay**: Verifique se o workflow retoma corretamente após falhas simuladas.
