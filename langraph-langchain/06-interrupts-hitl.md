# Interrupts - Human-in-the-Loop

## Conceito

Interrupts pausam a execução do grafo para:
- Aguardar aprovação humana
- Coletar input adicional
- Revisar/editar estado
- Debugging

## Usando interrupt()

```python
from langgraph.types import interrupt

def sensitive_action_node(state):
    # Pausar e mostrar informação para o humano
    human_response = interrupt(
        value={
            "action": "send_email",
            "to": state["email"],
            "content": state["message"]
        }
    )
    
    # Código abaixo só executa após resume
    if human_response == "approve":
        send_email(state["email"], state["message"])
        return {"status": "sent"}
    else:
        return {"status": "cancelled"}
```

## Resumindo Após Interrupt

```python
from langgraph.types import Command

# Primeira execução - para no interrupt
config = {"configurable": {"thread_id": "test"}}
result = graph.invoke({"email": "user@example.com"}, config)
# result contém informação do interrupt

# Retomar com resposta
graph.invoke(
    Command(resume="approve"),  # Valor passado para interrupt()
    config
)
```

## Padrões Comuns

### Approve/Reject

```python
def approval_node(state):
    approval = interrupt({
        "question": "Approve this action?",
        "details": state["action_details"]
    })
    
    if approval["approved"]:
        return execute_action(state)
    return {"status": "rejected", "reason": approval.get("reason")}

# Resume
graph.invoke(Command(resume={"approved": True}), config)
# ou
graph.invoke(Command(resume={"approved": False, "reason": "Too risky"}), config)
```

### Review and Edit State

```python
def review_node(state):
    # Mostra estado atual para edição
    edited = interrupt({
        "message": "Review and edit if needed",
        "current_value": state["draft"]
    })
    
    return {"draft": edited["new_value"]}

# Resume com edição
graph.invoke(
    Command(resume={"new_value": "Edited draft content"}),
    config
)
```

### Interrupt em Tools

```python
from langchain_core.tools import tool

@tool
def send_email_tool(to: str, subject: str, body: str):
    """Send email with human approval"""
    approval = interrupt({
        "tool": "send_email",
        "to": to,
        "subject": subject,
        "body": body
    })
    
    if approval == "approve":
        return send_email(to, subject, body)
    return "Email cancelled by user"
```

### Validação de Input

```python
def collect_info_node(state):
    while True:
        user_input = interrupt({
            "prompt": "Enter your email address"
        })
        
        if validate_email(user_input):
            return {"email": user_input}
        
        # Loop continua se inválido
        # Próximo interrupt mostrará erro
```

## Regras Importantes

### ❌ NÃO faça:

```python
# NÃO envolva interrupt em try/except
def bad_node(state):
    try:
        result = interrupt({"question": "?"})  # ❌
    except:
        pass

# NÃO reordene interrupts
def bad_node(state):
    if condition:
        a = interrupt("first")
        b = interrupt("second")
    else:
        b = interrupt("second")  # ❌ Ordem diferente
        a = interrupt("first")

# NÃO retorne objetos complexos não-serializáveis
def bad_node(state):
    return interrupt({"file": open("f.txt")})  # ❌
```

### ✅ FAÇA:

```python
# Mantenha ordem consistente
def good_node(state):
    a = interrupt("first")
    b = interrupt("second")
    return {"a": a, "b": b}

# Retorne valores serializáveis
def good_node(state):
    return interrupt({
        "data": state["serializable_data"],
        "options": ["approve", "reject"]
    })

# Side effects antes de interrupt devem ser idempotentes
def good_node(state):
    # Se reexecutar, não duplica
    if not already_logged(state["id"]):
        log_action(state["id"])
    
    return interrupt({"confirm": "Proceed?"})
```

## Streaming com HITL

```python
async for event in graph.astream(input, config, stream_mode="updates"):
    if "__interrupt__" in event:
        # Interrupt detectado
        interrupt_info = event["__interrupt__"]
        
        # Coletar resposta do usuário
        user_response = await get_user_input(interrupt_info)
        
        # Continuar
        async for event in graph.astream(
            Command(resume=user_response), 
            config
        ):
            yield event
```
