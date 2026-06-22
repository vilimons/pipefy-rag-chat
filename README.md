# Pipefy RAG Chat

Aplicação full-stack de chatbot RAG desenvolvida para o case técnico da Pipefy.

O projeto permite o upload de documentos, indexa o conteúdo no Redis Vector Search e disponibiliza uma interface conversacional para perguntas e respostas com base nos documentos enviados. O backend recupera trechos relevantes, monta um contexto fundamentado, chama um modelo open-source local via Ollama e retorna a resposta com as fontes utilizadas.

## Funcionalidades

* Upload de documentos nos formatos TXT, PDF e DOCX
* Extração automática de texto
* Divisão dos documentos em chunks
* Geração local de embeddings com Sentence Transformers
* Indexação vetorial com Redis Stack / RedisSearch
* API conversacional com FastAPI
* Orquestração do fluxo RAG com LangGraph
* Tracing opcional com LangSmith
* Integração com modelo open-source local via Ollama
* Respostas em streaming com Server-Sent Events
* Histórico de conversa por sessão
* Interface com múltiplas sessões de chat
* Exibição das fontes usadas na resposta
* Interface React para upload, listagem e chat
* Docker Compose para frontend, API e Redis
* Testes automatizados com pytest
* Validação de qualidade com Ruff
* Makefile com comandos padronizados de execução e validação

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
* Redis com volume persistente

## Arquitetura

```text
Browser
  |
  | HTTP / SSE
  v
Frontend - React + Nginx
  |
  | proxy /api
  v
FastAPI Backend
  |
  | upload de documentos
  v
Document Loader
  |
  | extração TXT / PDF / DOCX
  v
Chunking + Embeddings
  |
  v
Redis Stack
  |
  | Redis Hashes + RedisSearch Vector Index
  v
Fluxo RAG com LangGraph
  |
  | recuperação de fontes
  | construção de contexto
  | chamada ao LLM
  | formatação da resposta
  v
Ollama LLM
  |
  v
Resposta + Fontes + Histórico da Sessão
```

## Fluxo RAG

O pipeline RAG é orquestrado com LangGraph e dividido em nós explícitos:

```text
retriever_node
  -> recupera chunks relevantes no Redis

history_node
  -> carrega as mensagens recentes da sessão

context_builder_node
  -> monta o contexto do prompt usando fontes e histórico

llm_node
  -> chama o modelo configurado no Ollama

response_formatter_node
  -> formata resposta, fontes e metadados da sessão
```

O retriever usa estratégias diferentes conforme o tipo da pergunta:

* Para perguntas amplas sobre os documentos indexados, recupera chunks representativos de múltiplos documentos.
* Para perguntas específicas de conteúdo, usa busca vetorial por similaridade.
* Para perguntas que mencionam explicitamente um nome de arquivo, prioriza os chunks daquele documento.

Essa abordagem evita um problema comum em sistemas RAG: quando uma pergunta ampla retorna apenas chunks de um único documento, mesmo existindo vários arquivos indexados.

## Formatos suportados

* `.txt`
* `.pdf`
* `.docx`

Cada chunk é armazenado com metadados:

```text
file_id
source
chunk_index
content
uploaded_at
embedding
```

## Pré-requisitos

* Docker
* Docker Compose
* Ollama instalado localmente para uso do modelo open-source
* Node.js apenas se desejar executar comandos do frontend localmente fora do Docker

## Variáveis de ambiente

Crie um arquivo `.env` com base no `.env.example`.

Principais variáveis:

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
LANGSMITH_API_KEY=sua_api_key
LANGSMITH_PROJECT=pipefy-rag-chat
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

## Configuração do Ollama

Instale o Ollama e baixe o modelo:

```bash
ollama pull llama3:8b
```

No Windows com WSL/Docker, exponha o Ollama para os containers:

```powershell
$env:OLLAMA_HOST="0.0.0.0:11434"
ollama serve
```

A API usa por padrão:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3:8b
```

## Como executar o projeto

Suba a stack completa:

```bash
make up
```

Ou diretamente com Docker Compose:

```bash
docker compose up --build
```

Acesse a aplicação:

```text
http://localhost:3000
```

Documentação da API:

```text
http://localhost:8000/docs
```

RedisInsight:

```text
http://localhost:8001
```

Para parar os containers mantendo os volumes:

```bash
make down
```

Para parar os containers e remover volumes persistidos:

```bash
make down-volumes
```

## Comandos úteis

```bash
make help
```

Lista os comandos disponíveis.

```bash
make up
```

Sobe frontend, API e Redis.

```bash
make down
```

Para os containers mantendo os volumes.

```bash
make build
```

Builda as imagens Docker da API e do frontend.

```bash
make test
```

Executa os testes do backend com o tracing do LangSmith desativado.

```bash
make lint
```

Executa validação de qualidade com Ruff.

```bash
make format
```

Formata o código do backend e aplica correções seguras do Ruff.

```bash
make frontend-build
```

Executa o build do frontend.

```bash
make validate
```

Executa a validação completa do projeto:

* testes do backend
* lint do backend
* build do frontend

## Endpoints principais

### Health check

```http
GET /health
```

Retorna o status da API e da conexão com Redis.

### Upload de documento

```http
POST /upload
```

Faz upload e indexação de um documento TXT, PDF ou DOCX.

### Listagem de documentos

```http
GET /documents
```

Lista os documentos indexados.

### Remoção de documento

```http
DELETE /documents/{file_id}
```

Remove um documento e seus chunks.

### Recuperação de chunks

```http
POST /chat/retrieve
```

Retorna os chunks mais relevantes para uma pergunta.

### Chat

```http
POST /chat
```

Retorna uma resposta completa do RAG com fontes.

### Chat com streaming

```http
POST /chat/stream
```

Retorna a resposta em streaming usando Server-Sent Events.

### Histórico de sessão

```http
GET /chat/sessions/{session_id}/history
DELETE /chat/sessions/{session_id}/history
```

Carrega ou limpa o histórico de uma sessão.

## Exemplo de uso

Após subir a aplicação, envie documentos pela interface web e faça perguntas como:

```text
Sobre o que tratam os documentos?
```

Nesse caso, o sistema recupera trechos representativos dos documentos indexados e gera uma resposta baseada nas fontes disponíveis.

Para uma pergunta específica:

```text
O que é Pipefy?
```

O sistema utiliza busca semântica para encontrar os chunks mais relevantes.

Para uma pergunta sobre um arquivo específico:

```text
O que você pode dizer sobre o arquivo exemplo.pdf?
```

O sistema prioriza os chunks daquele arquivo.

## LangSmith

O tracing com LangSmith é opcional.

Para habilitar:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=sua_api_key
LANGSMITH_PROJECT=pipefy-rag-chat
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

Quando habilitado, o backend registra etapas importantes do fluxo RAG, como recuperação de contexto, construção do prompt e chamada ao modelo.

Os testes são executados com `LANGSMITH_TRACING=false` para evitar envio de traces de teste.

## Testes e validação

Executar testes do backend:

```bash
make test
```

Executar lint:

```bash
make lint
```

Executar build do frontend:

```bash
make frontend-build
```

Executar validação completa:

```bash
make validate
```

Resultado esperado:

```text
testes do backend passam
lint do backend passa
build do frontend passa
```

## Decisões técnicas

### Redis Stack como base vetorial

O Redis Stack foi utilizado porque o case solicita Redis/RedisSearch e porque ele permite armazenar metadados, chunks, embeddings e índice vetorial em um único serviço.

### Embeddings locais

O projeto usa Sentence Transformers para gerar embeddings localmente, evitando dependência de APIs pagas de embeddings.

### Ollama como provedor de LLM

O Ollama permite executar o projeto com um modelo open-source local. A integração com o LLM está isolada em um serviço próprio, permitindo troca futura por OpenAI, Claude ou outro provedor.

### LangGraph para orquestração

O LangGraph torna o fluxo RAG mais explícito, modular e fácil de observar, testar e evoluir.

### Estratégia de retrieval

O retriever não depende apenas de busca vetorial pura. Ele também detecta perguntas amplas sobre a base de documentos e recupera chunks representativos de múltiplos arquivos. Isso melhora respostas para perguntas como "sobre o que tratam os documentos?".

### Streaming

A interface usa Server-Sent Events para exibir a resposta progressivamente enquanto o modelo gera o texto.

## Limitações conhecidas

* A qualidade das respostas depende do modelo local configurado no Ollama.
* PDFs escaneados não são suportados, pois OCR não foi implementado.
* Arquivos muito grandes podem exigir uma estratégia mais robusta de ingestão e chunking.
* A extração atual é voltada para documentos textuais em TXT, PDF e DOCX.
* O Redis Stack roda localmente via Docker Compose nesta versão.
* O projeto foi otimizado para o escopo do case técnico, não para alto volume de produção.

## Possíveis evoluções para produção

* Deploy em cloud para API e frontend
* Redis gerenciado ou vector database dedicado
* Gerenciamento de secrets
* Autenticação e autorização
* Rate limiting
* Jobs assíncronos para ingestão de documentos
* Logs estruturados e observabilidade
* Avaliação automatizada da qualidade do retrieval
* Suporte a OCR
* Pipeline CI/CD completo
* Suporte a múltiplos provedores de LLM

## Validação antes da entrega

Antes de submeter o projeto, execute:

```bash
make validate
```

Resultado esperado:

```text
backend tests pass
backend lint pass
frontend build pass
```
