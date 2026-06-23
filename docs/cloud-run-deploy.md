# Deploy em Cloud Run

Este documento descreve a arquitetura e os procedimentos usados para disponibilizar uma versão cloud do **Pipefy RAG Chat**.

A aplicação também pode ser executada localmente com Docker Compose, Redis Stack e Ollama. O deploy cloud foi criado para permitir uma demonstração pública temporária, onde avaliadores podem acessar a interface, enviar documentos próprios não sensíveis e testar o fluxo completo de RAG.

> Importante: a instância pública é um ambiente compartilhado de demonstração. Não envie documentos sensíveis, confidenciais, pessoais ou proprietários.

## Visão geral

A versão cloud utiliza:

* Cloud Run para o frontend.
* Cloud Run para a API.
* Ollama como sidecar da API.
* Memorystore Redis para persistência e busca vetorial.
* Artifact Registry para armazenar imagens Docker.
* Cloud Build para build das imagens.
* GitHub Actions para validação contínua do código.

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
  | Private network
  v
Memorystore Redis
  |
  | Hashes + embeddings + metadados
  v
Documentos indexados

Cloud Run - API FastAPI
  |
  | localhost:11434
  v
Sidecar Ollama CPU
  |
  v
gemma2:2b
```

## Componentes

### Frontend

O frontend é uma aplicação React com TypeScript e Vite, servida por Nginx em Cloud Run.

Responsabilidades:

* upload de arquivos;
* listagem de documentos;
* exclusão de documentos;
* criação de sessões de chat;
* envio de perguntas;
* exibição de respostas;
* exibição das fontes recuperadas;
* leitura dinâmica do modelo ativo via `/health`.

O frontend é construído com a variável `VITE_API_BASE_URL`, apontando para a API cloud ativa.

### API

A API é construída com FastAPI e executa o fluxo de ingestão e RAG.

Responsabilidades:

* receber arquivos `.txt`, `.pdf` e `.docx`;
* extrair texto dos documentos;
* dividir o conteúdo em chunks;
* gerar embeddings;
* salvar chunks e metadados no Redis;
* executar busca vetorial;
* montar o contexto;
* chamar o LLM via Ollama;
* retornar resposta com fontes.

### Redis

Na versão cloud, o Redis é fornecido pelo Memorystore Redis.

Ele é usado para:

* armazenar metadados de documentos;
* armazenar chunks;
* armazenar embeddings;
* executar busca vetorial.

### Ollama sidecar

O Ollama roda como sidecar no mesmo serviço Cloud Run da API.

A API acessa o Ollama por:

```text
http://127.0.0.1:11434
```

Na versão cloud, o modelo utilizado é:

```text
gemma2:2b
```

Esse modelo foi escolhido por ser mais leve e mais estável para uma demonstração cloud em CPU.

## Diferenças entre execução local e cloud

### Execução local

A execução local usa:

* Docker Compose;
* Redis Stack;
* API FastAPI;
* frontend React/Nginx;
* Ollama local;
* modelo `llama3:8b`;
* embeddings com `sentence-transformers/all-MiniLM-L6-v2`.

### Execução cloud

A execução cloud usa:

* Cloud Run para frontend;
* Cloud Run para API;
* Memorystore Redis;
* Ollama sidecar CPU;
* modelo `gemma2:2b`;
* embeddings salvos dentro da imagem Docker da API.

Na cloud, o modelo de embeddings é salvo durante o build em:

```text
/models/sentence-transformers/all-MiniLM-L6-v2
```

Isso evita que a API precise baixar o modelo da Hugging Face durante o primeiro upload.

## Serviços Cloud Run

A demonstração cloud pode usar os seguintes serviços:

| Serviço                 | Descrição                             |
| ----------------------- | ------------------------------------- |
| `pipefy-rag-frontend`   | Frontend público da aplicação.        |
| `pipefy-rag-api-ollama` | API principal com sidecar Ollama CPU. |
| `pipefy-rag-api`        | API base/fallback sem sidecar Ollama. |

O frontend público deve apontar para `pipefy-rag-api-ollama`, pois esse serviço executa o fluxo completo:

```text
upload → embeddings → Redis → retrieval → Ollama → resposta com fontes
```

## Variáveis de ambiente da API cloud

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

OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma2:2b

LANGSMITH_TRACING=false
HF_HOME=/tmp/huggingface
SENTENCE_TRANSFORMERS_HOME=/tmp/sentence-transformers
```

## Variáveis de ambiente do frontend cloud

Exemplo:

```env
VITE_API_BASE_URL=<url-da-api-cloud-run>
```

O frontend não possui o nome do modelo hardcoded. Ele consulta o endpoint `/health` da API ativa e exibe dinamicamente o modelo retornado.

Exemplo de resposta do `/health`:

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

## Build da imagem da API

A imagem cloud da API usa `backend/Dockerfile.cloud`.

O Dockerfile cloud instala as dependências e baixa o modelo de embeddings durante o build.

Exemplo de build com Cloud Build:

```bash
export PROJECT_ID="<gcp-project-id>"
export REGION="us-central1"
export AR_REPO="pipefy-rag"

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

## Deploy da API com Ollama sidecar

Exemplo de deploy da API com Ollama CPU:

```bash
export PROJECT_ID="<gcp-project-id>"
export REGION="us-central1"
export AR_REPO="pipefy-rag"
export REDIS_INSTANCE="<memorystore-instance-name>"

export API_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/api:latest"

export REDIS_HOST="$(gcloud redis instances describe "$REDIS_INSTANCE" \
  --region="$REGION" \
  --format='value(host)')"

export REDIS_PORT="$(gcloud redis instances describe "$REDIS_INSTANCE" \
  --region="$REGION" \
  --format='value(port)')"

gcloud beta run deploy pipefy-rag-api-ollama \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --platform managed \
  --execution-environment gen2 \
  --allow-unauthenticated \
  --network default \
  --subnet default \
  --vpc-egress private-ranges-only \
  --min-instances 0 \
  --max-instances 1 \
  --timeout 900 \
  --concurrency 1 \
  --no-cpu-throttling \
  --container api \
  --image "$API_IMAGE" \
  --port 8080 \
  --cpu 2 \
  --memory 4Gi \
  --depends-on ollama \
  --set-env-vars "APP_NAME=pipefy-rag-chat,APP_ENV=production,REDIS_HOST=$REDIS_HOST,REDIS_PORT=$REDIS_PORT,REDIS_INDEX_NAME=docs,REDIS_VECTOR_DIM=384,CHUNK_SIZE=500,CHUNK_OVERLAP=50,TOP_K=5,MAX_HISTORY_MESSAGES=6,EMBEDDING_MODEL_NAME=/models/sentence-transformers/all-MiniLM-L6-v2,OLLAMA_BASE_URL=http://127.0.0.1:11434,OLLAMA_MODEL=gemma2:2b,LANGSMITH_TRACING=false,HF_HOME=/tmp/huggingface,SENTENCE_TRANSFORMERS_HOME=/tmp/sentence-transformers" \
  --container ollama \
  --image ollama/ollama:latest \
  --cpu 4 \
  --memory 8Gi \
  --startup-probe "tcpSocket.port=11434,initialDelaySeconds=60,failureThreshold=1,timeoutSeconds=60,periodSeconds=60" \
  --set-env-vars "OLLAMA_HOST=0.0.0.0:11434,OLLAMA_NUM_PARALLEL=1,OLLAMA_KEEP_ALIVE=-1,OLLAMA_DEBUG=false,CUDA_VISIBLE_DEVICES=-1" \
  --command "bash" \
  --args "-c,ollama serve & sleep 10 && ollama pull gemma2:2b && wait"
```

## Build do frontend

A imagem cloud do frontend usa `frontend/Dockerfile.cloud`.

Exemplo:

```bash
export PROJECT_ID="<gcp-project-id>"
export REGION="us-central1"
export AR_REPO="pipefy-rag"

export OLLAMA_API_URL="$(gcloud run services describe pipefy-rag-api-ollama \
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
      - "VITE_API_BASE_URL=$OLLAMA_API_URL"
      - "-t"
      - "$FRONTEND_IMAGE"
      - "."
images:
  - "$FRONTEND_IMAGE"
EOF

gcloud builds submit ./frontend \
  --config /tmp/cloudbuild-frontend.yaml
```

## Deploy do frontend

```bash
gcloud run deploy pipefy-rag-frontend \
  --image "$FRONTEND_IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 3000 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2
```

## Demo pública

A URL pública do frontend deve ser compartilhada diretamente com os avaliadores no momento da entrega.

Por segurança, ela não precisa ficar exposta no README do repositório.

> A instância pública é um ambiente compartilhado de demonstração. Não envie documentos sensíveis, confidenciais, pessoais ou proprietários.

### Como testar

1. Acesse a URL do frontend fornecida na entrega.
2. Opcionalmente, remova os documentos de exemplo.
3. Envie um arquivo `.txt`, `.pdf` ou `.docx`.
4. Aguarde a indexação do documento.
5. Faça perguntas sobre o conteúdo enviado.
6. Abra a seção **Fontes recuperadas** para validar os trechos usados na resposta.
7. Remova o documento após o teste, se desejar.

### Sugestões de perguntas

```text
Resuma os documentos indexados.
```

```text
Resuma o arquivo nome_do_arquivo.pdf usando apenas as fontes recuperadas.
```

```text
Quais são os principais pontos do arquivo nome_do_arquivo.docx?
```

```text
Segundo o arquivo nome_do_arquivo.txt, quais informações são apresentadas?
```

Perguntas muito curtas ou ambíguas podem gerar respostas menos precisas, especialmente na versão cloud com modelo menor. Para melhores resultados, mencione o nome do arquivo ou faça uma pergunta explícita.

## Smoke tests

Defina a URL da API:

```bash
export OLLAMA_API_URL="<url-da-api-cloud-run>"
```

### Health check

```bash
curl -s "$OLLAMA_API_URL/health" | python3 -m json.tool
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
    "model": "gemma2:2b"
  }
}
```

### Listar documentos

```bash
curl -s "$OLLAMA_API_URL/documents" | python3 -m json.tool
```

### Upload

```bash
cat > /tmp/exemplo.txt <<'EOF'
Este documento contém informações de exemplo para testar o fluxo RAG.
EOF

curl -i -X POST "$OLLAMA_API_URL/upload" \
  -F "file=@/tmp/exemplo.txt"
```

### Retrieval sem LLM

```bash
curl -s -X POST "$OLLAMA_API_URL/chat/retrieve" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Resuma o arquivo exemplo.txt usando apenas as fontes recuperadas.",
    "session_id": "smoke-retrieve",
    "top_k": 5
  }' | python3 -m json.tool
```

### Chat completo

```bash
curl -s -X POST "$OLLAMA_API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Resuma os documentos indexados.",
    "session_id": "smoke-chat",
    "top_k": 5
  }' | python3 -m json.tool
```

## Custos e exposição pública

A demo pública foi pensada para avaliação técnica temporária, não para produção.

Medidas usadas para reduzir custo e risco:

* `min-instances=0` para reduzir custo quando não houver uso.
* `max-instances=1` na API com Ollama.
* `max-instances=2` no frontend.
* Documentos de demonstração sem dados sensíveis.
* Budget alert configurado no projeto GCP.
* Possibilidade de remover os serviços após avaliação.

Como a API pública não possui autenticação por usuário, a URL da demo deve ser compartilhada apenas com os avaliadores e mantida ativa somente durante o período necessário.

## Limitações da demo cloud

* A instância pública é compartilhada.
* Não há autenticação por usuário.
* Não há isolamento multi-tenant dos documentos.
* O modelo cloud `gemma2:2b` é menor que o modelo local `llama3:8b`.
* Perguntas ambíguas podem exigir formulação mais explícita.
* PDFs escaneados não são suportados, pois OCR não foi implementado.
* Arquivos muito grandes podem exigir ingestão assíncrona.

## Troubleshooting

### A API está fora do ar

Verifique o health check:

```bash
curl -s "$OLLAMA_API_URL/health" | python3 -m json.tool
```

Se o Redis aparecer como `disconnected`, verifique as variáveis `REDIS_HOST` e `REDIS_PORT`.

### Upload falha na versão cloud

Possíveis causas:

* arquivo vazio;
* formato não suportado;
* timeout em arquivo grande;
* falha de conexão com Redis;
* modelo de embeddings ausente na imagem.

Na versão cloud, o modelo de embeddings deve estar disponível em:

```text
/models/sentence-transformers/all-MiniLM-L6-v2
```

### O chat responde, mas usa o documento errado

Use perguntas mais explícitas com o nome do arquivo:

```text
Resuma o arquivo nome_do_arquivo.docx usando apenas as fontes recuperadas.
```

Também é possível validar a recuperação diretamente pelo endpoint:

```bash
curl -s -X POST "$OLLAMA_API_URL/chat/retrieve" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Resuma o arquivo nome_do_arquivo.docx.",
    "session_id": "debug",
    "top_k": 5
  }' | python3 -m json.tool
```

### O modelo cloud demora para responder

A versão cloud usa Cloud Run com `min-instances=0`, então pode haver cold start.

O primeiro acesso após um período sem uso pode demorar mais porque a API e o sidecar Ollama precisam inicializar.

### A resposta diz que não encontrou informação

Verifique:

* se o documento foi realmente indexado;
* se a pergunta menciona o nome correto do arquivo;
* se `/chat/retrieve` retorna chunks relevantes;
* se o documento contém texto extraível.

PDFs escaneados não são processados porque OCR não foi implementado.

## Teardown

Após a avaliação, os serviços cloud podem ser removidos para evitar custos.

Exemplo:

```bash
gcloud run services delete pipefy-rag-frontend \
  --region "$REGION" \
  --quiet

gcloud run services delete pipefy-rag-api-ollama \
  --region "$REGION" \
  --quiet

gcloud run services delete pipefy-rag-api \
  --region "$REGION" \
  --quiet
```

Também é possível remover recursos auxiliares, como repositórios do Artifact Registry e instâncias Redis gerenciadas, se eles não forem mais necessários.
