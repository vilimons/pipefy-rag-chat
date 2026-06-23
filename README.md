# Pipefy RAG Chat

Aplicação full-stack de chatbot RAG desenvolvida para o case técnico da Pipefy.

O projeto permite o upload de documentos, indexa o conteúdo em uma base vetorial no Redis e disponibiliza uma interface conversacional para perguntas e respostas com base nos arquivos enviados. O backend recupera trechos relevantes, monta um contexto fundamentado, chama um modelo open-source via Ollama e retorna a resposta junto com as fontes utilizadas.

A aplicação pode ser executada de duas formas:

* **Localmente**, com Docker Compose, Redis Stack e Ollama rodando no ambiente do desenvolvedor.
* **Em cloud**, com Cloud Run, Memorystore Redis e Ollama como sidecar da API.

A versão cloud foi preparada para demonstração pública temporária, permitindo que avaliadores façam upload de seus próprios arquivos `.txt`, `.pdf` ou `.docx` e testem o fluxo completo de RAG.

> Observação: a instância pública é um ambiente compartilhado de demonstração. Não envie documentos sensíveis, confidenciais, pessoais ou proprietários.

## Funcionalidades

* Upload de documentos nos formatos TXT, PDF e DOCX.
* Extração automática de texto.
* Divisão dos documentos em chunks.
* Geração de embeddings com Sentence Transformers.
* Indexação vetorial com Redis Stack / RedisSearch.
* API conversacional com FastAPI.
* Orquestração do fluxo RAG com LangGraph.
* Tracing opcional com LangSmith.
* Integração com modelos open-source via Ollama.
* Respostas em streaming com Server-Sent Events.
* Histórico de conversa por sessão.
* Interface com múltiplas sessões de chat.
* Exibição das fontes usadas na resposta.
* Interface React para upload, listagem e chat.
* Docker Compose para execução local.
* Deploy cloud com Cloud Run, Memorystore Redis e Ollama sidecar.
* Demo pública para upload e teste de documentos não sensíveis.
* Health check com metadados do LLM ativo.
* Testes automatizados com pytest.
* Validação de qualidade com Ruff.
* Build do frontend com Vite.
* Makefile com comandos padronizados de execução e validação.
* GitHub Actions para validação contínua.

## Stack utilizada

### Backend

* Python 3.11
* FastAPI
* LangChain
* LangGraph
* LangSmith
* Redis Stack / RedisSearch
* Sentence Transformers
* Ollama
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
* Cloud Run
* Cloud Build
* Artifact Registry
* Memorystore Redis
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

O frontend permite enviar documentos, listar arquivos indexados, criar sessões de conversa e fazer perguntas. O backend recebe os arquivos, extrai texto, gera chunks, cria embeddings, persiste os dados no Redis e executa o fluxo RAG para responder às perguntas. O Redis armazena documentos, chunks, embeddings e metadados.

## Arquitetura local

Na execução local, todos os serviços são orquestrados com Docker Compose.

```text
Browser
  |
  v
Frontend React + Nginx
  |
  v
FastAPI
  |
  v
Redis Stack / RedisSearch

FastAPI
  |
  v
Ollama local
  |
  v
llama3:8b
```

No ambiente local, o Ollama roda fora do container da API e é acessado via `OLLAMA_BASE_URL`. Esse modo permite testar o projeto com modelo open-source local, sem depender de APIs externas de LLM.

## Arquitetura cloud

Na execução cloud, a aplicação foi adaptada para Cloud Run e Memorystore Redis.

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
  | Private network
  v
Memorystore Redis

Cloud Run - API FastAPI
  |
  | localhost:11434
  v
Sidecar Ollama CPU
  |
  v
gemma2:2b
```

Na versão cloud, o frontend e a API rodam como serviços Cloud Run. A API acessa o Memorystore Redis por rede privada e chama o Ollama como sidecar no mesmo serviço, usando `localhost:11434`.

O modelo de embeddings é incluído na imagem cloud da API durante o build, evitando download em runtime e reduzindo risco de falhas por rate limit externo.

Mais detalhes sobre o deploy cloud estão em [`docs/cloud-run-deploy.md`](docs/cloud-run-deploy.md).

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

Cada documento enviado recebe um `file_id`. Os chunks são armazenados com metadados como nome do arquivo, índice do chunk, conteúdo e data de upload.

Metadados principais:

* `file_id`
* `source`
* `chunk_index`
* `content`
* `uploaded_at`

## Fluxo RAG

```text
Pergunta do usuário
  |
  v
Geração do embedding da pergunta
  |
  v
Busca vetorial no Redis
  |
  v
Recuperação dos chunks mais relevantes
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

O backend não envia o documento inteiro para o modelo. Apenas os chunks mais relevantes são recuperados e usados como contexto para a geração da resposta.

## Orquestração com LangGraph

O fluxo RAG foi organizado com LangGraph para separar as etapas de recuperação, montagem de contexto, chamada ao LLM e formatação da resposta.

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

Essa separação torna o pipeline mais modular e facilita evoluções futuras, como reranking, validação de resposta, troca de modelo ou adição de políticas de fallback.

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
ollama pull llama3:8b
```

Para deploy cloud:

* Conta GCP ativa
* Projeto GCP configurado
* APIs necessárias habilitadas
* Cloud Run
* Cloud Build
* Artifact Registry
* Memorystore Redis
* Permissões de deploy no projeto

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
OLLAMA_MODEL=llama3:8b

LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=pipefy-rag-chat
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

## Variáveis principais

| Variável               | Descrição                                             |
| ---------------------- | ----------------------------------------------------- |
| `APP_ENV`              | Define o ambiente da aplicação.                       |
| `REDIS_HOST`           | Host do Redis.                                        |
| `REDIS_PORT`           | Porta do Redis.                                       |
| `REDIS_INDEX_NAME`     | Nome do índice vetorial.                              |
| `REDIS_VECTOR_DIM`     | Dimensão dos embeddings.                              |
| `CHUNK_SIZE`           | Tamanho dos chunks.                                   |
| `CHUNK_OVERLAP`        | Sobreposição entre chunks.                            |
| `TOP_K`                | Número padrão de chunks recuperados.                  |
| `MAX_HISTORY_MESSAGES` | Quantidade máxima de mensagens usadas como histórico. |
| `EMBEDDING_MODEL_NAME` | Modelo de embeddings usado pela API.                  |
| `OLLAMA_BASE_URL`      | URL do serviço Ollama.                                |
| `OLLAMA_MODEL`         | Modelo usado para geração de respostas.               |
| `LANGSMITH_TRACING`    | Ativa ou desativa tracing com LangSmith.              |

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
    "model": "llama3:8b"
  }
}
```

## Comandos úteis

O projeto inclui um `Makefile` com comandos para execução, validação e manutenção.

```bash
make help
```

Principais comandos:

| Comando               | Descrição                                 |
| --------------------- | ----------------------------------------- |
| `make up`             | Sobe os serviços com Docker Compose.      |
| `make down`           | Para os serviços.                         |
| `make restart`        | Reinicia os serviços.                     |
| `make ps`             | Lista containers ativos.                  |
| `make logs`           | Exibe logs dos serviços.                  |
| `make api-logs`       | Exibe logs da API.                        |
| `make frontend-logs`  | Exibe logs do frontend.                   |
| `make redis-logs`     | Exibe logs do Redis.                      |
| `make test`           | Executa os testes do backend.             |
| `make lint`           | Executa Ruff no backend.                  |
| `make format`         | Formata o backend com Ruff.               |
| `make frontend-build` | Executa o build do frontend.              |
| `make validate`       | Executa testes, lint e build do frontend. |
| `make build`          | Rebuilda os containers.                   |

## Demo pública

Uma versão da aplicação pode ser disponibilizada via Cloud Run para avaliação técnica.

A URL pública deve ser compartilhada diretamente com os avaliadores no momento da entrega. Por segurança, ela não precisa ficar exposta no README do repositório.

> Importante: a instância pública é um ambiente compartilhado de demonstração. Não envie documentos sensíveis, confidenciais, pessoais ou proprietários.

Como testar:

1. Acesse a URL do frontend fornecida na entrega.
2. Opcionalmente, remova os documentos de exemplo.
3. Envie um arquivo `.txt`, `.pdf` ou `.docx`.
4. Aguarde a indexação do documento.
5. Faça perguntas sobre o conteúdo enviado.
6. Abra a seção **Fontes recuperadas** para validar os trechos usados na resposta.
7. Remova o documento após o teste, se desejar.

Mais detalhes sobre arquitetura cloud, smoke tests, custos e teardown estão em [`docs/cloud-run-deploy.md`](docs/cloud-run-deploy.md).

## Endpoints da API

### Health check

```http
GET /health
```

Retorna o status da API, a conexão com Redis e os metadados do LLM ativo.

Exemplo:

```json
{
  "status": "ok",
  "app": "pipefy-rag-chat",
  "environment": "production",
  "redis": "connected",
  "llm": {
    "provider": "ollama",
    "model": "gemma2:2b"
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

Executa o fluxo completo de RAG: embedding da pergunta, recuperação de chunks, montagem de contexto, chamada ao LLM e resposta final com fontes.

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

Retorna apenas os chunks recuperados, sem chamar o LLM. Esse endpoint é útil para validar a busca vetorial e depurar o comportamento do RAG.

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

* Testes do backend.
* Validação de lint com Ruff.
* Build do frontend.

## Integração contínua

O projeto possui workflow de CI com GitHub Actions.

A validação é executada em pushes e pull requests para garantir que o projeto continue funcional após mudanças no código.

O pipeline valida:

* Build das imagens Docker.
* Testes do backend.
* Lint do backend.
* Build do frontend.

## Decisões técnicas

### FastAPI

O FastAPI foi escolhido por oferecer boa produtividade para APIs Python, validação automática de contratos, suporte a documentação via Swagger e boa integração com serviços assíncronos.

### Redis Stack / RedisSearch

O Redis foi usado como base vetorial e armazenamento dos metadados por atender ao requisito do case e permitir uma arquitetura simples para busca semântica.

Na execução local, o projeto usa Redis Stack via Docker Compose. Na execução cloud, usa Memorystore Redis.

### Sentence Transformers

A geração de embeddings usa `sentence-transformers/all-MiniLM-L6-v2`, um modelo leve e open-source. Ele gera vetores de 384 dimensões, o que reduz custo computacional e simplifica a execução local e cloud.

Na imagem cloud da API, o modelo é baixado durante o build e salvo localmente dentro da imagem. Isso evita download em runtime.

### Ollama

O Ollama foi escolhido para permitir uso de modelos open-source sem dependência obrigatória de APIs pagas.

Na execução local, o projeto usa `llama3:8b`.

Na execução cloud, a API usa um sidecar Ollama CPU com `gemma2:2b`. Essa escolha prioriza estabilidade da demo pública e menor complexidade operacional.

A integração com o LLM está isolada em um serviço próprio, permitindo troca futura por OpenAI, Claude, Vertex AI ou outro provedor.

O nome do modelo ativo não é hardcoded no frontend. A interface consulta o endpoint `/health` da API ativa e exibe dinamicamente o modelo configurado no backend.

### LangGraph

O LangGraph foi usado para organizar o fluxo RAG em etapas explícitas:

* recuperação de chunks;
* leitura de histórico;
* construção de contexto;
* chamada ao LLM;
* formatação da resposta.

Essa abordagem deixa o fluxo mais modular e facilita futuras evoluções.

### LangSmith

O LangSmith foi incluído como tracing opcional. Quando habilitado, permite observar chamadas do pipeline RAG e depurar etapas como recuperação, construção de contexto e resposta do LLM.

### Frontend React

O frontend foi construído com React, TypeScript e Vite. Ele permite:

* upload de arquivos;
* listagem de documentos;
* exclusão de documentos;
* múltiplas sessões de chat;
* visualização de fontes;
* interação com streaming.

## Limitações conhecidas

* A qualidade das respostas depende do modelo configurado no Ollama.
* Na demo cloud, o modelo `gemma2:2b` é menor que o modelo local `llama3:8b`.
* Perguntas muito curtas ou ambíguas podem gerar respostas menos precisas.
* Para melhor resultado, recomenda-se citar o nome do arquivo ou fazer perguntas explícitas.
* PDFs escaneados não são suportados, pois OCR não foi implementado.
* Arquivos muito grandes podem exigir uma estratégia mais robusta de ingestão assíncrona.
* A demo pública é compartilhada e não possui autenticação por usuário.
* Não há isolamento multi-tenant dos documentos na demo pública.
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

## Resumo

O Pipefy RAG Chat entrega uma aplicação full-stack de RAG com upload de documentos, indexação vetorial, chat contextualizado e exibição de fontes.

Principais pontos implementados:

* Backend Python com FastAPI.
* Frontend React com TypeScript.
* Upload e parsing de TXT, PDF e DOCX.
* Chunking e geração de embeddings.
* Redis Vector Search.
* Fluxo RAG orquestrado com LangGraph.
* LLM open-source via Ollama.
* Respostas com fontes recuperadas.
* Streaming de respostas.
* Histórico por sessão.
* Testes automatizados.
* CI com GitHub Actions.
* Execução local com Docker Compose.
* Deploy cloud com Cloud Run, Memorystore Redis e Ollama sidecar.

O projeto foi desenvolvido para atender ao escopo do case técnico, priorizando clareza arquitetural, modularidade, rastreabilidade das respostas e facilidade de execução local ou cloud.
