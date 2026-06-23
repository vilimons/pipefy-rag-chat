# Deploy em Cloud Run

Este documento descreve a arquitetura cloud usada para disponibilizar uma versão pública temporária do **Pipefy RAG Chat**.

A aplicação também pode ser executada localmente com Docker Compose, Redis Stack e Ollama. O deploy cloud foi criado para permitir uma demonstração técnica em ambiente público, com frontend acessível via browser, API pública, Redis gerenciado e modelo LLM open-source rodando em Cloud Run com GPU.

> Importante: a demo pública é um ambiente compartilhado e não possui autenticação por usuário. Não envie documentos sensíveis, confidenciais, pessoais ou proprietários.

## Visão geral

A arquitetura cloud atual utiliza:

* Cloud Run para o frontend.
* Cloud Run para a API FastAPI.
* Cloud Run GPU privado para o Ollama.
* Modelo `qwen2.5:7b` executado via Ollama.
* Memorystore Redis para armazenamento de documentos, chunks, embeddings e busca vetorial.
* Artifact Registry para armazenar imagens Docker.
* Cloud Build para build das imagens.
* Secret Manager para armazenar a chave do LangSmith.
* LangSmith para observabilidade dos traces do fluxo RAG.

## Arquitetura cloud

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
  |
  | chunks + embeddings + metadados
  v
Redis Vector Search

Cloud Run - API FastAPI
  |
  | HTTPS + identity token
  v
Cloud Run - Ollama GPU privado
  |
  v
qwen2.5:7b
```

## Serviços

| Serviço                 | Função                             |
| ----------------------- | ---------------------------------- |
| `pipefy-rag-frontend`   | Frontend público da aplicação.     |
| `pipefy-rag-api`        | API pública FastAPI.               |
| `pipefy-rag-ollama-gpu` | Serviço privado do Ollama com GPU. |
| `pipefy-rag-redis`      | Instância Memorystore Redis.       |

O frontend público chama a API. A API chama o serviço privado do Ollama GPU usando um identity token do Cloud Run.

## Fluxo cloud

```text
Usuário envia documento
  |
  v
Frontend Cloud Run
  |
  v
API Cloud Run
  |
  v
Extração de texto
  |
  v
Chunking
  |
  v
Embeddings
  |
  v
Memorystore Redis
```

```text
Usuário faz pergunta
  |
  v
Frontend Cloud Run
  |
  v
API Cloud Run
  |
  v
Busca vetorial + estratégia RAG
  |
  v
Contexto recuperado
  |
  v
Ollama GPU privado
  |
  v
Resposta + fontes
```

## Modelo LLM em cloud

A versão cloud usa:

```text
qwen2.5:7b
```

O modelo roda em um serviço Cloud Run separado com GPU, e não como sidecar da API.

Essa arquitetura foi escolhida porque:

* isola a API do runtime pesado do LLM;
* facilita trocar o modelo sem alterar a API;
* permite manter o serviço do modelo privado;
* evita expor diretamente o endpoint do Ollama;
* melhora a qualidade das respostas em relação ao modelo menor usado anteriormente;
* facilita depuração dos logs do LLM separadamente.

## Serviço Ollama GPU

O serviço `pipefy-rag-ollama-gpu` executa Ollama com GPU e modelo `qwen2.5:7b`.

Variáveis relevantes:

```env
OLLAMA_DEBUG=1
OLLAMA_LLM_LIBRARY=cuda_v13
OLLAMA_FLASH_ATTENTION=false
OLLAMA_HOST=0.0.0.0:8080
OLLAMA_MODELS=/models
OLLAMA_KEEP_ALIVE=-1
OLLAMA_NUM_PARALLEL=1
NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility
GGML_CUDA_ENABLE_UNIFIED_MEMORY=1
```

Durante os testes, o backend CUDA v12 apresentou erro de runtime. O serviço funcionou corretamente ao forçar:

```env
OLLAMA_LLM_LIBRARY=cuda_v13
OLLAMA_FLASH_ATTENTION=false
```

O serviço foi implantado sem acesso público:

```text
--no-allow-unauthenticated
```

A API recebe permissão para chamá-lo com:

```text
roles/run.invoker
```

## Deploy do Ollama GPU

Exemplo de variáveis:

```bash
export PROJECT_ID="project-0aab3e64-5191-4bc7-8fa"
export REGION="us-central1"
export AR_REPO="pipefy-rag"
export MODEL_NAME="qwen2.5:7b"
export OLLAMA_GPU_SERVICE="pipefy-rag-ollama-gpu"

gcloud config set project "$PROJECT_ID"
```

Exemplo de Dockerfile para o serviço Ollama GPU:

```Dockerfile
FROM ollama/ollama:latest

ENV OLLAMA_HOST=0.0.0.0:8080
ENV OLLAMA_MODELS=/models
ENV OLLAMA_KEEP_ALIVE=-1
ENV OLLAMA_NUM_PARALLEL=1

ARG MODEL_NAME=qwen2.5:7b

RUN ollama serve & \
    sleep 10 && \
    ollama pull ${MODEL_NAME} && \
    pkill ollama

EXPOSE 8080

CMD ["serve"]
```

Build da imagem:

```bash
export OLLAMA_GPU_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/ollama-gpu-qwen25-7b:latest"

cat > cloudbuild.yaml <<EOF
timeout: "1800s"
steps:
  - name: "gcr.io/cloud-builders/docker"
    args:
      - "build"
      - "--build-arg"
      - "MODEL_NAME=$MODEL_NAME"
      - "-t"
      - "$OLLAMA_GPU_IMAGE"
      - "."
images:
  - "$OLLAMA_GPU_IMAGE"
EOF

gcloud builds submit . --config cloudbuild.yaml
```

Deploy do serviço GPU:

```bash
gcloud run deploy "$OLLAMA_GPU_SERVICE" \
  --image "$OLLAMA_GPU_IMAGE" \
  --region "$REGION" \
  --platform managed \
  --execution-environment gen2 \
  --no-allow-unauthenticated \
  --gpu 1 \
  --gpu-type nvidia-l4 \
  --no-gpu-zonal-redundancy \
  --cpu 4 \
  --memory 16Gi \
  --no-cpu-throttling \
  --concurrency 1 \
  --timeout 900 \
  --min-instances 0 \
  --max-instances 1 \
  --port 8080
```

Após o primeiro deploy, atualizar as variáveis do serviço:

```bash
cat > /tmp/ollama-gpu-env.yaml <<'EOF'
OLLAMA_DEBUG: "1"
OLLAMA_LLM_LIBRARY: "cuda_v13"
OLLAMA_FLASH_ATTENTION: "false"
OLLAMA_HOST: "0.0.0.0:8080"
OLLAMA_MODELS: "/models"
OLLAMA_KEEP_ALIVE: "-1"
OLLAMA_NUM_PARALLEL: "1"
NVIDIA_VISIBLE_DEVICES: "all"
NVIDIA_DRIVER_CAPABILITIES: "compute,utility"
GGML_CUDA_ENABLE_UNIFIED_MEMORY: "1"
EOF

gcloud run services update "$OLLAMA_GPU_SERVICE" \
  --region "$REGION" \
  --env-vars-file /tmp/ollama-gpu-env.yaml
```

## Teste do Ollama GPU

Obter URL:

```bash
export OLLAMA_GPU_URL="$(gcloud run services describe "$OLLAMA_GPU_SERVICE" \
  --region "$REGION" \
  --format='value(status.url)')"

echo "$OLLAMA_GPU_URL"
```

Gerar identity token:

```bash
export ID_TOKEN="$(gcloud auth print-identity-token --audiences="$OLLAMA_GPU_URL")"
```

Listar modelos:

```bash
curl -s "$OLLAMA_GPU_URL/api/tags" \
  -H "Authorization: Bearer $ID_TOKEN" | jq
```

Testar geração:

```bash
curl -s "$OLLAMA_GPU_URL/api/generate" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:7b",
    "prompt": "Answer in one sentence: what is retrieval augmented generation?",
    "stream": false
  }' | jq
```

Resposta esperada:

```json
{
  "model": "qwen2.5:7b",
  "response": "Retrieval-Augmented Generation ...",
  "done": true
}
```

## API cloud

A API roda no serviço:

```text
pipefy-rag-api
```

Ela é pública para permitir acesso pelo frontend, mas o serviço do Ollama GPU permanece privado.

A API usa:

```env
OLLAMA_BASE_URL=<OLLAMA_GPU_URL>
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_AUTH_AUDIENCE=<OLLAMA_GPU_URL>
```

Quando `OLLAMA_AUTH_AUDIENCE` está configurado, a API busca um identity token no metadata server do Cloud Run e envia o header:

```http
Authorization: Bearer <token>
```

Esse comportamento permite que a API chame o serviço privado do Ollama GPU sem expor o endpoint do modelo publicamente.

## Permissão para a API chamar o Ollama GPU

Descobrir a service account da API:

```bash
export API_SERVICE="pipefy-rag-api"

export API_RUNTIME_SA="$(gcloud run services describe "$API_SERVICE" \
  --region "$REGION" \
  --format='value(spec.template.spec.serviceAccountName)')"

if [ -z "$API_RUNTIME_SA" ]; then
  export PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" \
    --format='value(projectNumber)')"
  export API_RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
fi

echo "$API_RUNTIME_SA"
```

Conceder permissão de invoker no serviço GPU:

```bash
gcloud run services add-iam-policy-binding "$OLLAMA_GPU_SERVICE" \
  --region "$REGION" \
  --member="serviceAccount:$API_RUNTIME_SA" \
  --role="roles/run.invoker"
```

## Variáveis de ambiente da API

Exemplo:

```env
APP_NAME=pipefy-rag-chat
APP_ENV=production

REDIS_HOST=<memorystore-host>
REDIS_PORT=6379
REDIS_INDEX_NAME=docs
REDIS_VECTOR_DIM=384

CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K=5
MAX_HISTORY_MESSAGES=6

EMBEDDING_MODEL_NAME=/models/sentence-transformers/all-MiniLM-L6-v2

OLLAMA_BASE_URL=<ollama-gpu-cloud-run-url>
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_AUTH_AUDIENCE=<ollama-gpu-cloud-run-url>

LANGSMITH_TRACING=true
LANGSMITH_PROJECT=pipefy-rag-chat-cloud
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=<secret-manager:langsmith-api-key>

HF_HOME=/tmp/huggingface
SENTENCE_TRANSFORMERS_HOME=/tmp/sentence-transformers
```

## Build da API

A imagem cloud da API usa:

```text
backend/Dockerfile.cloud
```

Esse Dockerfile salva o modelo de embeddings dentro da imagem em:

```text
/models/sentence-transformers/all-MiniLM-L6-v2
```

Isso evita download do modelo em runtime.

Build:

```bash
export API_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/api:latest"

cat > /tmp/cloudbuild-api.yaml <<EOF
steps:
  - name: "gcr.io/cloud-builders/docker"
    args:
      - "build"
      - "-f"
      - "Dockerfile.cloud"
      - "-t"
      - "$API_IMAGE"
      - "."
images:
  - "$API_IMAGE"
EOF

gcloud builds submit ./backend \
  --config /tmp/cloudbuild-api.yaml
```

## Deploy da API

Obter Redis:

```bash
export REDIS_INSTANCE="pipefy-rag-redis"

export REDIS_HOST="$(gcloud redis instances describe "$REDIS_INSTANCE" \
  --region="$REGION" \
  --format='value(host)')"

export REDIS_PORT="$(gcloud redis instances describe "$REDIS_INSTANCE" \
  --region="$REGION" \
  --format='value(port)')"
```

Obter URL do Ollama GPU:

```bash
export OLLAMA_GPU_URL="$(gcloud run services describe "$OLLAMA_GPU_SERVICE" \
  --region "$REGION" \
  --format='value(status.url)')"
```

Deploy:

```bash
gcloud run deploy "$API_SERVICE" \
  --image "$API_IMAGE" \
  --region "$REGION" \
  --platform managed \
  --execution-environment gen2 \
  --allow-unauthenticated \
  --network default \
  --subnet default \
  --vpc-egress private-ranges-only \
  --port 8080 \
  --cpu 2 \
  --memory 4Gi \
  --timeout 900 \
  --concurrency 10 \
  --min-instances 0 \
  --max-instances 2 \
  --ingress all \
  --set-env-vars "APP_NAME=pipefy-rag-chat,APP_ENV=production,REDIS_HOST=$REDIS_HOST,REDIS_PORT=$REDIS_PORT,REDIS_INDEX_NAME=docs,REDIS_VECTOR_DIM=384,CHUNK_SIZE=500,CHUNK_OVERLAP=50,TOP_K=5,MAX_HISTORY_MESSAGES=6,EMBEDDING_MODEL_NAME=/models/sentence-transformers/all-MiniLM-L6-v2,OLLAMA_BASE_URL=$OLLAMA_GPU_URL,OLLAMA_MODEL=qwen2.5:7b,OLLAMA_AUTH_AUDIENCE=$OLLAMA_GPU_URL,LANGSMITH_TRACING=true,LANGSMITH_PROJECT=pipefy-rag-chat-cloud,LANGSMITH_ENDPOINT=https://api.smith.langchain.com,HF_HOME=/tmp/huggingface,SENTENCE_TRANSFORMERS_HOME=/tmp/sentence-transformers" \
  --update-secrets "LANGSMITH_API_KEY=langsmith-api-key:latest"
```

Garantir acesso público à API:

```bash
gcloud run services add-iam-policy-binding "$API_SERVICE" \
  --region "$REGION" \
  --member="allUsers" \
  --role="roles/run.invoker"
```

## Frontend cloud

O frontend é construído com:

```env
VITE_API_BASE_URL=<api-cloud-run-url>
```

Build:

```bash
export FRONTEND_SERVICE="pipefy-rag-frontend"

export API_URL="$(gcloud run services describe "$API_SERVICE" \
  --region "$REGION" \
  --format='value(status.url)')"

export FRONTEND_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/frontend:latest"

cat > /tmp/cloudbuild-frontend.yaml <<EOF
steps:
  - name: "gcr.io/cloud-builders/docker"
    args:
      - "build"
      - "-f"
      - "Dockerfile.cloud"
      - "--build-arg"
      - "VITE_API_BASE_URL=$API_URL"
      - "-t"
      - "$FRONTEND_IMAGE"
      - "."
images:
  - "$FRONTEND_IMAGE"
EOF

gcloud builds submit ./frontend \
  --config /tmp/cloudbuild-frontend.yaml
```

Deploy:

```bash
gcloud run deploy "$FRONTEND_SERVICE" \
  --image "$FRONTEND_IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 3000 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2 \
  --ingress all
```

Garantir acesso público ao frontend:

```bash
gcloud run services add-iam-policy-binding "$FRONTEND_SERVICE" \
  --region "$REGION" \
  --member="allUsers" \
  --role="roles/run.invoker"
```

## Smoke tests

### API health check

```bash
export API_URL="$(gcloud run services describe pipefy-rag-api \
  --region "$REGION" \
  --format='value(status.url)')"

curl -s "$API_URL/health" | jq
```

Resposta esperada:

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

### Upload

```bash
cat > /tmp/rag_cloud_test.txt <<'EOF'
Pipefy is a platform for process automation, workflow management and business operations.
This file is used to validate the cloud RAG flow.
EOF

curl -s -X POST "$API_URL/upload" \
  -F "file=@/tmp/rag_cloud_test.txt" | jq
```

### Retrieval

```bash
curl -s -X POST "$API_URL/chat/retrieve" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What platform helps with workflow management?",
    "session_id": "cloud-retrieve-smoke",
    "top_k": 5
  }' | jq
```

### Chat

```bash
curl -s -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What platform helps with workflow management?",
    "session_id": "cloud-chat-smoke",
    "top_k": 5
  }' | jq
```

## Demo pública

A URL pública do frontend deve ser compartilhada diretamente com os avaliadores no momento da entrega.

Por segurança, ela não precisa ficar exposta no README do repositório.

> A instância pública é um ambiente compartilhado de demonstração. Não envie documentos sensíveis, confidenciais, pessoais ou proprietários.

Como testar:

1. Acesse a URL do frontend fornecida na entrega.
2. Opcionalmente, remova documentos de exemplo.
3. Envie um arquivo `.txt`, `.pdf` ou `.docx`.
4. Aguarde a indexação.
5. Faça perguntas sobre o conteúdo enviado.
6. Abra **Fontes recuperadas** para validar os trechos usados na resposta.
7. Remova o documento após o teste, se desejar.

Sugestões:

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

## LangSmith

A API cloud pode enviar traces para o projeto:

```text
pipefy-rag-chat-cloud
```

Configuração:

```env
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=pipefy-rag-chat-cloud
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=<secret-manager:langsmith-api-key>
```

A chave é armazenada no Secret Manager e montada como variável de ambiente no serviço da API.

Os traces ajudam a observar:

* busca vetorial;
* construção do prompt;
* chamada ao LLM;
* modelo usado;
* fontes recuperadas;
* latência da resposta.

## Custos e exposição pública

A demo cloud foi pensada para avaliação técnica temporária, não para produção.

Medidas usadas para reduzir custo e risco:

* `min-instances=0` no frontend.
* `min-instances=0` na API.
* `min-instances=0` no serviço GPU.
* `max-instances=1` no serviço GPU.
* Modelo GPU privado, sem acesso público direto.
* API pública apenas para permitir uso via frontend.
* Budget alert configurado no projeto GCP.
* Documentos de demonstração sem dados sensíveis.

Pontos de atenção:

* O Memorystore Redis continua gerando custo enquanto a instância existir.
* O serviço GPU pode ter cold start alto.
* A primeira chamada ao modelo pode demorar mais por carregamento do runtime/modelo.
* A demo não possui autenticação por usuário.

## Troubleshooting

### API retorna HTML ou erro no `jq`

Se `curl "$API_URL/health" | jq` falhar, veja o corpo real:

```bash
curl -i "$API_URL/health"
```

Possíveis causas:

* API com ingress interno;
* API sem `allUsers` como invoker;
* URL incorreta;
* serviço sem revisão ativa.

### API não consegue chamar o Ollama GPU

Verifique:

* `OLLAMA_BASE_URL`;
* `OLLAMA_AUTH_AUDIENCE`;
* permissão `roles/run.invoker` no serviço GPU;
* service account usada pela API;
* logs da API;
* logs do serviço GPU.

### Ollama GPU retorna erro CUDA

Verifique se as variáveis estão aplicadas:

```env
OLLAMA_LLM_LIBRARY=cuda_v13
OLLAMA_FLASH_ATTENTION=false
```

Também verificar logs:

```bash
gcloud run services logs read pipefy-rag-ollama-gpu \
  --region "$REGION" \
  --limit=120
```

### Upload falha

Possíveis causas:

* arquivo vazio;
* formato não suportado;
* PDF escaneado sem texto extraível;
* falha de conexão com Redis;
* timeout em arquivo grande.

### Resposta não encontra informação

Verifique:

* se o documento foi indexado;
* se `/chat/retrieve` retorna chunks relevantes;
* se a pergunta cita o arquivo correto;
* se o documento contém texto extraível;
* se há documentos duplicados causando ruído no contexto.

## Teardown

Após a avaliação, os serviços podem ser removidos para evitar custos.

```bash
gcloud run services delete pipefy-rag-frontend \
  --region "$REGION" \
  --quiet

gcloud run services delete pipefy-rag-api \
  --region "$REGION" \
  --quiet

gcloud run services delete pipefy-rag-ollama-gpu \
  --region "$REGION" \
  --quiet
```

Opcionalmente, remover Redis:

```bash
gcloud redis instances delete pipefy-rag-redis \
  --region "$REGION" \
  --quiet
```

> Atenção: remover o Redis apaga os documentos, chunks e embeddings indexados.
