# Pipefy RAG Chat

Aplicação full-stack de chatbot RAG desenvolvida para o case técnico da Pipefy.

O projeto permite fazer upload de documentos, indexar o conteúdo em uma base vetorial no Redis e conversar com os arquivos enviados. O backend recupera trechos relevantes, monta um contexto fundamentado, chama um modelo open-source via Ollama e retorna a resposta junto com as fontes utilizadas.

A aplicação pode ser executada de duas formas:

* **Localmente**, com Docker Compose, Redis Stack e Ollama rodando no ambiente do desenvolvedor.
* **Em cloud**, com Cloud Run, Memorystore Redis e Ollama em um serviço privado com GPU.

> A instância cloud pública é um ambiente compartilhado de demonstração. Não envie documentos sensíveis, confidenciais, pessoais ou proprietários.

## Funcionalidades

* Upload de documentos nos formatos `.txt`, `.pdf` e `.docx`.
* Extração automática de texto.
* Divisão dos documentos em chunks com overlap.
* Geração de embeddings com Sentence Transformers.
* Indexação vetorial com Redis Stack / RedisSearch.
* Busca semântica com Redis Vector Search.
* Estratégia RAG com recuperação metadata-aware.
* Priorização de chunks por documento mencionado.
* Deduplicação de chunks recuperados.
* Respostas com base nos documentos enviados.
* Exibição das fontes usadas na resposta.
* Chat com histórico por sessão.
* Múltiplas conversas no frontend.
* Renomear, excluir e limpar sessões de chat.
* Respostas em streaming com Server-Sent Events.
* API FastAPI com documentação Swagger.
* Orquestração do fluxo RAG com LangGraph.
* Integração com modelos open-source via Ollama.
* Observabilidade opcional com LangSmith.
* Execução local com Docker Compose.
* Deploy cloud com Cloud Run e Memorystore Redis.
* Ollama cloud em serviço privado com GPU.
* Testes automatizados com pytest.
* Validação de qualidade com Ruff.
* Build do frontend com Vite.
* Makefile com comandos padronizados.
* GitHub Actions para validação contínua.

## Stack utilizada

### Backend

* Python
* FastAPI
* LangChain
* LangGraph
* LangSmith
* Redis Stack / RedisSearch
* Sentence Transformers
* Ollama
* httpx
* pytest
* Ruff

### Frontend

* React
* TypeScript
* Vite
* Nginx

### Infraestrutura

* Docker
* Docker Compose
* Redis Stack local
* Google Cloud Run
* Cloud Run GPU
* Cloud Build
* Artifact Registry
* Memorystore Redis
* Secret Manager
* GitHub Actions

## Arquitetura

A aplicação foi organizada em três camadas principais:

```text
Frontend React
  |
  v
Backend FastAPI
  |
  v
Redis Vector Search
```

O frontend permite enviar documentos, listar arquivos indexados, criar sessões de conversa e fazer perguntas.

O backend recebe os arquivos, extrai texto, gera chunks, cria embeddings, persiste os dados no Redis e executa o fluxo RAG para responder às perguntas.

O Redis armazena documentos, chunks, embeddings, metadados e histórico de sessão.

## Arquitetura local

Na execução local, os serviços principais são orquestrados com Docker Compose.

```text
Browser
  |
  v
Frontend React + Nginx
  |
  v
FastAPI
  |
  +--> Redis Stack / RedisSearch
  |
  +--> Ollama local
```

Configuração local típica:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_AUTH_AUDIENCE=
```

No ambiente local, o Ollama roda fora do container da API e é acessado via `OLLAMA_BASE_URL`.

Como `OLLAMA_AUTH_AUDIENCE` fica vazio localmente, a API chama o Ollama sem autenticação adicional.

## Arquitetura cloud

Na execução cloud, a aplicação roda em Google Cloud Run.

```text
Browser
  |
  | HTTPS
  v
Cloud Run - Frontend React/Nginx
  |
  | HTTPS
  v
Cloud Run - API FastAPI
  |
  | private network
  v
Memorystore Redis

Cloud Run - API FastAPI
  |
  | HTTPS + identity token
  v
Cloud Run - Ollama GPU privado
  |
  v
qwen2.5:7b
```

Na versão cloud:

* o frontend é público;
* a API é pública para permitir uso pela interface;
* o Redis é acessado pela API em rede privada;
* o Ollama GPU fica privado;
* a API chama o Ollama GPU usando um identity token do Cloud Run;
* o modelo cloud atual é `qwen2.5:7b`.

Mais detalhes sobre a arquitetura cloud estão em [`docs/cloud-run-deploy.md`](docs/cloud-run-deploy.md).

## Fluxo de ingestão

```text
Upload do arquivo
  |
  v
Validação de formato
  |
  v
Extração de texto
  |
  v
Divisão em chunks
  |
  v
Geração de embeddings
  |
  v
Persistência no Redis
  |
  v
Indexação vetorial
```

Cada documento enviado recebe um `file_id`.

Metadados principais:

* `file_id`;
* `source`;
* `chunk_index`;
* `content`;
* `uploaded_at`.

## Fluxo RAG

```text
Pergunta do usuário
  |
  v
Análise da pergunta
  |
  v
Busca vetorial + regras de retrieval
  |
  v
Recuperação dos chunks mais relevantes
  |
  v
Deduplicação
  |
  v
Construção do contexto
  |
  v
Chamada ao LLM via Ollama
  |
  v
Resposta final com fontes
```

O backend não envia o documento inteiro para o modelo. Apenas os chunks mais relevantes são recuperados e usados como contexto para geração da resposta.

## Estratégia de retrieval

O projeto usa uma estratégia híbrida de recuperação.

Além da busca vetorial padrão, o backend aplica regras para melhorar respostas em cenários comuns.

### Busca vetorial

Para perguntas gerais, o sistema gera embedding da pergunta e busca os chunks semanticamente mais próximos no Redis.

Exemplo:

```text
What problem does the document describe?
```

### Priorização por documento

Quando a pergunta menciona um arquivo específico, o sistema prioriza chunks daquele documento.

Exemplo:

```text
In pipefy.txt, what platform helps with workflow management?
```

### Perguntas de visão geral

Quando o usuário pede uma visão geral dos documentos indexados, o sistema inclui chunks representativos dos arquivos disponíveis.

Exemplo:

```text
Resuma os documentos indexados.
```

### Perguntas metadata-aware

Perguntas sobre título, autores, data de publicação ou informações que normalmente aparecem no início de um documento recebem tratamento especial.

Exemplos:

```text
Who are the authors of the article?
```

```text
What is the publication date?
```

```text
What is the title of the paper?
```

Nesses casos, o sistema inclui chunks iniciais dos documentos relevantes e combina esses trechos com a busca vetorial.

Isso reduz falhas comuns de RAG em perguntas sobre metadados.

### Deduplicação

Antes de montar o prompt, os chunks recuperados são deduplicados para evitar repetir o mesmo conteúdo no contexto.

A deduplicação considera:

* identificador do documento;
* índice do chunk;
* origem;
* assinatura textual normalizada.

## Orquestração com LangGraph

O fluxo RAG foi organizado com LangGraph para separar as etapas principais do pipeline.

Fluxo lógico:

```text
retriever_node
  |
  v
history_node
  |
  v
context_builder_node
  |
  v
llm_node
  |
  v
response_formatter_node
```

Essa separação deixa o pipeline mais modular e facilita evoluções futuras, como reranking, validação de respostas, troca de modelo ou políticas de fallback.

## Idioma da resposta

O prompt orienta o modelo a responder no mesmo idioma principal usado pelo usuário.

Exemplos:

| Pergunta                        | Resposta esperada               |
| ------------------------------- | ------------------------------- |
| `What is this document about?`  | Inglês                          |
| `Sobre o que é este documento?` | Português                       |
| `Resuma this article`           | Idioma predominante da pergunta |

## Estrutura do projeto

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   ├── core/
│   │   ├── rag/
│   │   ├── repositories/
│   │   ├── services/
│   │   └── main.py
│   ├── tests/
│   ├── Dockerfile
│   ├── Dockerfile.cloud
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── types/
│   │   └── main.tsx
│   ├── Dockerfile
│   ├── Dockerfile.cloud
│   ├── nginx.conf
│   ├── nginx.cloud.conf
│   └── package.json
│
├── docs/
│   ├── architecture.md
│   └── cloud-run-deploy.md
│
├── .github/
│   └── workflows/
│
├── docker-compose.yml
├── Makefile
├── .env.example
└── README.md
```

## Pré-requisitos

Para execução local:

* Docker
* Docker Compose
* Ollama
* Git

Modelo recomendado para execução local:

```bash
ollama pull llama3.1:8b
```

Também é possível usar outro modelo compatível com Ollama, ajustando `OLLAMA_MODEL` no `.env`.

## Configuração de ambiente

Crie o arquivo `.env` a partir do exemplo:

```bash
cp .env.example .env
```

Exemplo de configuração local:

```env
APP_NAME=pipefy-rag-chat
APP_ENV=development

API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_PORT=3000

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_INDEX_NAME=docs
REDIS_VECTOR_DIM=384

CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K=5
MAX_HISTORY_MESSAGES=6

EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2

OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_AUTH_AUDIENCE=

LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=pipefy-rag-chat
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

## Variáveis principais

| Variável               | Descrição                                                                                                              |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `APP_ENV`              | Define o ambiente da aplicação.                                                                                        |
| `API_PORT`             | Porta local da API.                                                                                                    |
| `FRONTEND_PORT`        | Porta local do frontend.                                                                                               |
| `REDIS_HOST`           | Host do Redis.                                                                                                         |
| `REDIS_PORT`           | Porta do Redis.                                                                                                        |
| `REDIS_INDEX_NAME`     | Nome do índice vetorial.                                                                                               |
| `REDIS_VECTOR_DIM`     | Dimensão dos embeddings.                                                                                               |
| `CHUNK_SIZE`           | Tamanho dos chunks.                                                                                                    |
| `CHUNK_OVERLAP`        | Sobreposição entre chunks.                                                                                             |
| `TOP_K`                | Número padrão de chunks recuperados.                                                                                   |
| `MAX_HISTORY_MESSAGES` | Quantidade máxima de mensagens usadas como histórico.                                                                  |
| `EMBEDDING_MODEL_NAME` | Modelo de embeddings usado pela API.                                                                                   |
| `OLLAMA_BASE_URL`      | URL do serviço Ollama.                                                                                                 |
| `OLLAMA_MODEL`         | Modelo usado para geração de respostas.                                                                                |
| `OLLAMA_AUTH_AUDIENCE` | Audience usada para gerar identity token quando a API chama um serviço Cloud Run privado. Deve ficar vazia localmente. |
| `LANGSMITH_TRACING`    | Ativa ou desativa tracing com LangSmith.                                                                               |
| `LANGSMITH_PROJECT`    | Projeto usado para organizar traces no LangSmith.                                                                      |
| `LANGSMITH_ENDPOINT`   | Endpoint da API LangSmith.                                                                                             |

## Executando localmente

Com o `.env` configurado e o modelo baixado no Ollama, suba os serviços com Docker Compose:

```bash
docker compose up --build
```

Ou usando o Makefile:

```bash
make up
```

A aplicação ficará disponível em:

```text
Frontend: http://localhost:3000
API:      http://localhost:8000
Swagger:  http://localhost:8000/docs
Redis UI: http://localhost:8001
```

Para verificar a saúde da API:

```bash
curl http://localhost:8000/health
```

Exemplo de resposta:

```json
{
  "status": "ok",
  "app": "pipefy-rag-chat",
  "environment": "development",
  "redis": "connected",
  "llm": {
    "provider": "ollama",
    "model": "llama3.1:8b"
  }
}
```

## Comandos úteis

O projeto inclui um `Makefile` com comandos para execução, validação e manutenção.

```bash
make help
```

Principais comandos:

| Comando                  | Descrição                                 |
| ------------------------ | ----------------------------------------- |
| `make up`                | Sobe frontend, API e Redis.               |
| `make down`              | Para os containers mantendo volumes.      |
| `make down-volumes`      | Para containers e remove volumes.         |
| `make restart`           | Reinicia a stack.                         |
| `make ps`                | Lista containers ativos.                  |
| `make logs`              | Mostra logs de todos os serviços.         |
| `make api-logs`          | Mostra logs da API.                       |
| `make frontend-logs`     | Mostra logs do frontend.                  |
| `make redis-logs`        | Mostra logs do Redis.                     |
| `make test`              | Executa os testes do backend.             |
| `make lint`              | Executa Ruff no backend.                  |
| `make format`            | Formata o backend com Ruff.               |
| `make frontend-build`    | Executa o build do frontend.              |
| `make validate`          | Executa testes, lint e build do frontend. |
| `make build`             | Rebuilda as imagens Docker.               |
| `make clean-model-cache` | Remove cache local de modelos Docker.     |

## Demo pública

Uma versão da aplicação pode ser disponibilizada via Cloud Run para avaliação técnica.

A URL pública deve ser compartilhada diretamente com os avaliadores no momento da entrega.

Por segurança, ela não precisa ficar exposta no README do repositório.

> A instância pública é um ambiente compartilhado de demonstração. Não envie documentos sensíveis, confidenciais, pessoais ou proprietários.

Como testar:

1. Acesse a URL do frontend fornecida na entrega.
2. Opcionalmente, remova documentos de exemplo.
3. Envie um arquivo `.txt`, `.pdf` ou `.docx`.
4. Aguarde a indexação do documento.
5. Faça perguntas sobre o conteúdo enviado.
6. Abra a seção **Fontes recuperadas** para validar os trechos usados na resposta.
7. Remova o documento após o teste, se desejar.

Sugestões de perguntas:

```text
Resuma os documentos indexados.
```

```text
What are the main points of the uploaded document?
```

```text
Who are the authors of the article?
```

```text
According to the document, what problem does the article try to solve?
```

Mais detalhes sobre arquitetura cloud, smoke tests, custos e teardown estão em [`docs/cloud-run-deploy.md`](docs/cloud-run-deploy.md).

## Endpoints da API

### Health check

```http
GET /health
```

Retorna o status da API, a conexão com Redis e os metadados do LLM ativo.

Exemplo cloud:

```json
{
  "status": "ok",
  "app": "pipefy-rag-chat",
  "environment": "production",
  "redis": "connected",
  "llm": {
    "provider": "ollama",
    "model": "qwen2.5:7b"
  }
}
```

### Upload de documento

```http
POST /upload
```

Recebe um arquivo `.txt`, `.pdf` ou `.docx`, extrai o texto, gera chunks, cria embeddings e indexa o conteúdo no Redis.

Exemplo:

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@exemplo.txt"
```

Resposta:

```json
{
  "file_id": "uuid-do-documento",
  "filename": "exemplo.txt",
  "chunks_indexed": 3,
  "status": "indexed"
}
```

### Listar documentos

```http
GET /documents
```

Retorna os documentos indexados.

Exemplo:

```json
[
  {
    "file_id": "uuid-do-documento",
    "name": "exemplo.txt",
    "uploaded_at": "2026-06-22T22:33:35.942854Z",
    "chunks": 3
  }
]
```

### Remover documento

```http
DELETE /documents/{file_id}
```

Remove o documento e seus chunks do Redis.

### Chat RAG

```http
POST /chat
```

Executa o fluxo completo de RAG:

1. embedding da pergunta;
2. recuperação de chunks;
3. montagem de contexto;
4. chamada ao LLM;
5. resposta final com fontes.

Exemplo:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Resuma os documentos indexados.",
    "session_id": "demo",
    "top_k": 5
  }'
```

Resposta:

```json
{
  "answer": "Resposta gerada com base nos documentos.",
  "sources": [
    {
      "chunk": "Trecho recuperado do documento.",
      "source": "exemplo.txt",
      "score": 0.42,
      "chunk_index": 0,
      "file_id": "uuid-do-documento"
    }
  ],
  "session_id": "demo"
}
```

### Recuperação sem LLM

```http
POST /chat/retrieve
```

Retorna apenas os chunks recuperados, sem chamar o LLM.

Esse endpoint é útil para validar a busca vetorial e depurar o comportamento do RAG.

Exemplo:

```bash
curl -X POST http://localhost:8000/chat/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quais informações aparecem no arquivo exemplo.txt?",
    "session_id": "debug",
    "top_k": 5
  }'
```

### Streaming

```http
POST /chat/stream
```

Retorna a resposta do chat em streaming usando Server-Sent Events.

### Histórico de conversa

```http
GET /chat/sessions/{session_id}/history
```

Retorna o histórico de mensagens da sessão informada.

### Limpar histórico

```http
DELETE /chat/sessions/{session_id}/history
```

Remove o histórico de uma sessão específica.

## Testes e validação

O backend possui testes automatizados com `pytest`, cobrindo serviços de ingestão, extração, chunking, integração com Redis, endpoints principais e fluxo RAG.

Para executar os testes:

```bash
make test
```

Para executar lint:

```bash
make lint
```

Para executar a validação completa:

```bash
make validate
```

O comando `make validate` executa:

* testes do backend;
* lint com Ruff;
* build do frontend.

## Integração contínua

O projeto possui workflow de CI com GitHub Actions.

A validação é executada em pushes e pull requests para garantir que o projeto continue funcional após mudanças no código.

O pipeline valida:

* build das imagens Docker;
* testes do backend;
* lint do backend;
* build do frontend.

## Observabilidade com LangSmith

O LangSmith pode ser habilitado para rastrear o fluxo RAG.

Quando habilitado, permite observar:

* pergunta do usuário;
* chunks recuperados;
* scores de retrieval;
* prompt montado;
* chamada ao LLM;
* modelo usado;
* resposta final;
* latência.

Configuração local opcional:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<sua-chave>
LANGSMITH_PROJECT=pipefy-rag-chat
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

Na cloud, a chave do LangSmith é armazenada no Secret Manager e exposta para a API como variável de ambiente.

## Decisões técnicas

### FastAPI

FastAPI foi escolhido por oferecer boa produtividade para APIs Python, validação automática de contratos, documentação Swagger e integração simples com serviços HTTP.

### Redis Stack / RedisSearch

Redis foi usado como base vetorial e armazenamento de metadados por atender ao escopo do case e permitir uma arquitetura simples para busca semântica.

Na execução local, o projeto usa Redis Stack via Docker Compose.

Na execução cloud, usa Memorystore Redis.

### Sentence Transformers

A geração de embeddings usa `sentence-transformers/all-MiniLM-L6-v2`, um modelo leve e open-source que gera vetores de 384 dimensões.

Isso reduz custo computacional e facilita execução local e cloud.

Na imagem cloud da API, o modelo é baixado durante o build e salvo dentro da imagem para evitar download em runtime.

### Ollama

Ollama foi escolhido para permitir uso de modelos open-source sem dependência obrigatória de APIs pagas.

No ambiente local, o projeto usa Ollama instalado no host.

Na cloud, a API chama um serviço separado do Ollama com GPU, privado, executando `qwen2.5:7b`.

A integração com o LLM está isolada em um client próprio, permitindo troca futura por outros modelos ou provedores.

### Cloud Run GPU privado

O serviço de inferência foi separado da API para:

* manter o endpoint do modelo privado;
* isolar runtime pesado de LLM;
* facilitar troubleshooting;
* trocar modelo sem redesenhar a API;
* melhorar a qualidade das respostas;
* controlar custo com `min-instances=0` e `max-instances=1`.

### LangGraph

LangGraph foi usado para organizar o fluxo RAG em etapas explícitas:

* recuperação de chunks;
* leitura de histórico;
* construção de contexto;
* chamada ao LLM;
* formatação da resposta.

Essa abordagem deixa o fluxo mais modular e facilita futuras evoluções.

### LangSmith

LangSmith foi incluído como tracing opcional.

Quando habilitado, permite observar chamadas do pipeline RAG e depurar etapas como recuperação, construção de contexto e resposta do LLM.

### Frontend React

O frontend foi construído com React, TypeScript e Vite.

Ele permite:

* upload de arquivos;
* listagem de documentos;
* exclusão de documentos;
* múltiplas sessões de chat;
* renomear e excluir conversas;
* visualização de fontes;
* interação com streaming.

## Limitações conhecidas

* A qualidade das respostas depende do modelo configurado no Ollama.
* Perguntas muito curtas ou ambíguas podem gerar respostas menos precisas.
* Para melhor resultado, recomenda-se citar o nome do arquivo ou fazer perguntas explícitas.
* PDFs escaneados não são suportados, pois OCR não foi implementado.
* Arquivos muito grandes podem exigir uma estratégia mais robusta de ingestão assíncrona.
* A demo pública é compartilhada e não possui autenticação por usuário.
* Não há isolamento multi-tenant dos documentos na demo pública.
* O serviço cloud de GPU pode ter cold start.
* A primeira chamada ao modelo em cloud pode demorar mais.
* O projeto foi otimizado para o escopo do case técnico, não para alto volume de produção.

## Evoluções futuras

Possíveis melhorias para uma versão de produção:

* Autenticação de usuários.
* Isolamento de documentos por usuário ou organização.
* Código de acesso para ambientes públicos de demonstração.
* Fila assíncrona para ingestão de arquivos grandes.
* Suporte a OCR para PDFs escaneados.
* Reranking dos chunks recuperados.
* Avaliação automática de qualidade das respostas.
* Métricas de latência, custo e taxa de erro.
* Observabilidade com dashboards.
* Políticas de expiração automática para documentos enviados.
* Persistência de arquivos originais em object storage.
* Suporte a outros provedores de LLM, como OpenAI, Claude ou Vertex AI.
* Testes end-to-end no frontend.
* Deploy automatizado via pipeline CI/CD.

## Documentação adicional

* [`docs/architecture.md`](docs/architecture.md): detalhes da arquitetura, fluxo RAG, retrieval e decisões técnicas.
* [`docs/cloud-run-deploy.md`](docs/cloud-run-deploy.md): passo a passo de deploy cloud, smoke tests, troubleshooting, custos e teardown.

## Resumo

O Pipefy RAG Chat entrega uma aplicação full-stack de RAG com upload de documentos, indexação vetorial, chat contextualizado e exibição de fontes.

Principais pontos implementados:

* backend Python com FastAPI;
* frontend React com TypeScript;
* upload e parsing de TXT, PDF e DOCX;
* chunking e geração de embeddings;
* Redis Vector Search;
* retrieval metadata-aware;
* fluxo RAG orquestrado com LangGraph;
* LLM open-source via Ollama;
* cloud com Ollama GPU privado;
* respostas com fontes recuperadas;
* streaming de respostas;
* histórico por sessão;
* múltiplas conversas no frontend;
* testes automatizados;
* CI com GitHub Actions;
* execução local com Docker Compose;
* deploy cloud com Cloud Run, Memorystore Redis e Cloud Run GPU.

O projeto foi desenvolvido para atender ao escopo do case técnico, priorizando clareza arquitetural, modularidade, rastreabilidade das respostas e facilidade de execução local ou cloud.
