# LangGraph & LangChain - Documentação Consolidada

Este diretório contém a referência técnica essencial para o desenvolvimento de agentes stateful utilizando LangGraph.

## 📚 Índice de Referência

### 1. [Arquitetura Core](./01-core-architecture.md)
Conceitos fundamentais, Graph API vs Functional API, Nodes, Edges e gerenciamento de Estado.

### 2. [Persistência e Memória](./02-persistence-and-memory.md)
Como manter o estado entre conversas, checkpointers para produção (Postgres/Redis) e memória de curto/longo prazo.

### 3. [Tools e Agentes Pré-construídos](./03-tools-and-prebuilt-agents.md)
Definição de ferramentas (Functions), uso do `ToolNode` e como instanciar Agentes ReAct prontos com `create_react_agent`.

### 4. [Workflows Avançados](./04-advanced-workflows.md)
Streaming de tokens em tempo real, modularização com subgrafos, controle dinâmico com `Command`/`Send` e Human-in-the-loop.

### 5. [Produção e Boas Práticas](./05-production-best-practices.md)
Guia de deployment, observabilidade com LangSmith, segurança, resiliência e checklist de lançamento.

---

## 🎓 Tutorial de Implementação

### [Agentic RAG Completo](./13-agentic-rag.md)
Um guia passo a passo de como construímos o sistema de RAG (Retrieval-Augmented Generation) deste projeto.

---

## 🔗 Atalhos
- **Repositório**: [LangChain GitHub](https://github.com/langchain-ai/langgraph)
- **Docs Oficiais**: [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
