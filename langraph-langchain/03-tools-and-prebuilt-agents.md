# 03 - Tools & Prebuilt Agents

O LangGraph facilita a integração de LLMs com ferramentas (Functions) e fornece abstrações prontas para padrões comuns como Agentes ReAct.

## 1. Definindo Tools

Tools são funções Python decoradas com `@tool`. A docstring é crucial, pois é o que o LLM usa para entender quando chamar a ferramenta.

```python
from langchain.tools import tool

@tool
def get_weather(location: str):
    """Obtém o clima atual para uma localização específica."""
    return f"22°C em {location}"
```

### Injeção de Contexto
Tools podem acessar o estado do grafo ou o Store automaticamente:

```python
from langgraph.prebuilt import InjectedState
from typing import Annotated

@tool
def custom_tool(query: str, state: Annotated[dict, InjectedState]):
    # Acessa mensagens ou dados do grafo diretamente
    return f"Resultado para {query} com {len(state['messages'])} msgs"
```

---

## 2. ToolNode & conditions

O `ToolNode` é um componente pré-construído que executa as ferramentas solicitadas pelo LLM.

```python
from langgraph.prebuilt import ToolNode, tools_condition

tools = [get_weather, custom_tool]
tool_node = ToolNode(tools)

# No grafo:
builder.add_node("tools", tool_node)
builder.add_conditional_edges("agent", tools_condition)
```

---

## 3. Prebuilt Agents (create_react_agent)

Para 90% dos casos de uso de agentes de conversação, o LangGraph oferece um construtor pronto.

```python
from langgraph.prebuilt import create_react_agent

model = ChatOpenAI(model="gpt-4")
agent = create_react_agent(
    model, 
    tools=tools,
    checkpointer=checkpointer,
    state_modifier="Você é um assistente prestativo." # System message
)

# Já vem com o loop Agent -> Tools -> Agent configurado.
```

---

## 4. Manipulação de Mensagens

- **`add_messages`**: Reducer padrão que acumula mensagens e gerencia atualizações/deleções via IDs.
- **`RemoveMessage`**: Envie uma instância de `RemoveMessage(id="...")` para limpar mensagens do histórico (útil para sumarização ou truncamento).
- **`trim_messages`**: Utilitário para manter o histórico dentro do limite de tokens do modelo.

```python
from langchain_core.messages import trim_messages

# Manter apenas as últimas 10 mensagens
trimmed = trim_messages(state["messages"], strategy="last", max_tokens=10, token_counter=len)
```
