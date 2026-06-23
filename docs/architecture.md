# Arquitetura

Este documento descreve a arquitetura técnica do **Pipefy RAG Chat**, uma aplicação full-stack para upload de documentos, indexação semântica e perguntas/respostas usando RAG com modelos open-source.

O projeto foi desenvolvido como um case técnico com foco em:

* backend Python com FastAPI;
* frontend React;
* RAG com embeddings e busca vetorial;
* Redis Stack local e Memorystore Redis em cloud;
* Ollama como runtime de LLM open-source;
* LangSmith para observabilidade;
* execução local via Docker Compose;
* deploy cloud em Google Cloud Run.

## Objetivo

A aplicação permite que um usuário envie documentos e faça perguntas sobre o conteúdo indexado.

O sistema:

1. recebe arquivos enviados pelo usuário;
2. extrai texto dos documentos;
3. divide o conteúdo em chunks;
4. gera embeddings;
5. armazena chunks, metadados e vetores no Redis;
6. recupera trechos relevantes para uma pergunta;
7. monta um prompt com contexto;
8. chama um modelo LLM open-source;
9. retorna a resposta e as fontes utilizadas.

## Visão geral

```text id="ft484j"
Usuário
  |
  v
Frontend React
  |
  v
API FastAPI
  |
  +--> Document ingestion
  |      |
  |      v
  |    Text extraction
  |      |
  |      v
  |    Chunking
  |      |
  |      v
  |    Embeddings
  |      |
  |      v
  |    Redis Vector Store
  |
  +--> Chat / Retrieval
         |
         v
       Semantic search + metadata-aware retrieval
         |
         v
       Prompt assembly
         |
         v
       Ollama LLM
         |
         v
       Answer + sources
```

## Componentes principais

| Componente        | Responsabilidade                                                                 |
| ----------------- | -------------------------------------------------------------------------------- |
| Frontend React    | Interface de upload, listagem de documentos, chat, sessões e fontes recuperadas. |
| FastAPI           | API HTTP para upload, listagem, remoção, recuperação e chat.                     |
| Document loader   | Extração de texto de arquivos `.txt`, `.pdf` e `.docx`.                          |
| Chunker           | Divisão do texto em partes menores com overlap.                                  |
| Embedding service | Geração de embeddings usando Sentence Transformers.                              |
| Redis             | Armazenamento de documentos, chunks, vetores e histórico de sessão.              |
| Retrieval service | Busca semântica, priorização por documento e recuperação metadata-aware.         |
| RAG pipeline      | Montagem do contexto, prompt e chamada ao LLM.                                   |
| Ollama            | Runtime local ou cloud para modelo open-source.                                  |
| LangSmith         | Observabilidade dos traces do fluxo RAG.                                         |

## Arquitetura local

No ambiente local, todos os serviços principais são executados via Docker Compose, exceto o Ollama, que pode rodar localmente no host.

```text id="8957ks"
Browser
  |
  v
React Frontend
  |
  v
FastAPI Backend
  |
  +--> Redis Stack
  |
  +--> Ollama local
```

Fluxo local típico:

```text id="mqzo71"
Frontend container
  |
  v
API container
  |
  +--> Redis Stack container
  |
  +--> Ollama no host
```

Configuração local típica:

```env id="wxon1u"
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.1:8b
OLLAMA_AUTH_AUDIENCE=
```

No ambiente local, `OLLAMA_AUTH_AUDIENCE` fica vazio. Dessa forma, o backend chama o Ollama sem autenticação adicional.

## Arquitetura cloud

Na cloud, a aplicação roda em Google Cloud Run com separação entre API, frontend, Redis e LLM.

```text id="jbtymb"
Browser
  |
  v
Cloud Run - Frontend
  |
  v
Cloud Run - API
  |
  +--> Memorystore Redis
  |
  +--> Cloud Run - Ollama GPU privado
```

O serviço do Ollama GPU não é público. A API chama esse serviço usando um identity token emitido pelo metadata server do Cloud Run.

```text id="84lr3i"
API Cloud Run
  |
  | Authorization: Bearer <identity-token>
  v
Ollama GPU Cloud Run privado
  |
  v
qwen2.5:7b
```

Configuração cloud típica:

```env id="6t1hun"
OLLAMA_BASE_URL=<ollama-gpu-cloud-run-url>
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_AUTH_AUDIENCE=<ollama-gpu-cloud-run-url>
```

Quando `OLLAMA_AUTH_AUDIENCE` está preenchido, o backend gera um identity token e adiciona o header `Authorization` nas chamadas para o Ollama.

## Modelo LLM

O projeto usa modelos open-source via Ollama.

### Local

O ambiente local foi pensado para usar um modelo disponível na máquina do desenvolvedor, por exemplo:

```text id="tcx9r2"
llama3.1:8b
```

ou outro modelo compatível com Ollama.

### Cloud

A versão cloud usa:

```text id="hy7c6k"
qwen2.5:7b
```

Esse modelo roda em um serviço Cloud Run separado com GPU NVIDIA L4.

A separação entre API e LLM foi escolhida para:

* isolar o runtime pesado do modelo;
* reduzir acoplamento entre API e inferência;
* facilitar troubleshooting;
* manter o endpoint do modelo privado;
* permitir evolução do modelo sem redesenhar a API;
* melhorar a qualidade das respostas em relação a modelos menores.

## Ingestão de documentos

O fluxo de ingestão começa no endpoint de upload.

```text id="src6dr"
POST /upload
  |
  v
Validate file
  |
  v
Extract text
  |
  v
Split into chunks
  |
  v
Generate embeddings
  |
  v
Store document metadata
  |
  v
Store chunks + vectors
```

Cada documento indexado recebe:

* `file_id`;
* nome do arquivo;
* timestamp de upload;
* quantidade de chunks;
* chunks textuais;
* embeddings;
* metadados de origem.

## Extração de texto

Formatos suportados:

| Formato | Estratégia                           |
| ------- | ------------------------------------ |
| `.txt`  | Leitura direta do conteúdo textual.  |
| `.pdf`  | Extração de texto com parser PDF.    |
| `.docx` | Extração de texto do documento Word. |

Limitações conhecidas:

* PDFs escaneados sem camada textual podem não ser extraídos corretamente.
* O projeto não implementa OCR.
* Arquivos vazios são rejeitados.
* Documentos muito grandes podem exigir ajustes de timeout e chunking.

## Chunking

O texto extraído é dividido em chunks menores antes de gerar embeddings.

Configuração padrão:

```env id="chhjtp"
CHUNK_SIZE=500
CHUNK_OVERLAP=50
```

O overlap ajuda a preservar contexto entre chunks consecutivos.

Exemplo:

```text id="ypd530"
Documento original
  |
  v
Chunk 0: caracteres 0-500
Chunk 1: caracteres 450-950
Chunk 2: caracteres 900-1400
```

## Embeddings

O projeto usa Sentence Transformers para gerar embeddings semânticos.

Modelo padrão:

```text id="2mwkbb"
sentence-transformers/all-MiniLM-L6-v2
```

Dimensão vetorial:

```env id="n3rfdp"
REDIS_VECTOR_DIM=384
```

No ambiente cloud, o modelo de embeddings é salvo dentro da imagem da API para evitar download em runtime:

```text id="lsn96e"
/models/sentence-transformers/all-MiniLM-L6-v2
```

## Armazenamento no Redis

O Redis armazena:

* metadados dos documentos;
* chunks;
* embeddings;
* índice vetorial;
* histórico de sessões de chat.

Em ambiente local é usado Redis Stack.

Em cloud é usado Memorystore Redis.

## Busca vetorial

Para perguntas gerais, o backend gera embedding da pergunta e executa busca vetorial contra os chunks armazenados.

```text id="jpv9jg"
Pergunta
  |
  v
Embedding da pergunta
  |
  v
Redis vector search
  |
  v
Top K chunks relevantes
```

Configuração padrão:

```env id="q6woki"
TOP_K=5
```

A resposta inclui as fontes recuperadas para que o usuário consiga auditar quais trechos foram usados.

## Estratégia de retrieval

O retrieval não depende apenas de similaridade vetorial pura. O projeto aplica regras adicionais para melhorar a recuperação em cenários comuns de RAG.

### 1. Perguntas gerais

Quando a pergunta não menciona um arquivo específico e não parece pedir metadados, o sistema usa busca vetorial padrão.

Exemplo:

```text id="1fwr61"
What problem does the article try to solve?
```

Fluxo:

```text id="e6vv4l"
question embedding
  |
  v
vector search
  |
  v
top relevant chunks
```

### 2. Perguntas sobre um documento específico

Quando a pergunta menciona um documento existente, o sistema prioriza chunks daquele arquivo.

Exemplo:

```text id="jcyd2p"
In pipefy.txt, what platform helps with workflow management?
```

Fluxo:

```text id="uug7az"
identify mentioned document
  |
  v
prioritize chunks from that document
  |
  v
merge with vector results
```

Isso reduz ruído quando há múltiplos documentos indexados.

### 3. Perguntas de visão geral

Quando a pergunta pede resumo ou visão geral dos documentos, o sistema inclui chunks representativos dos documentos indexados.

Exemplos:

```text id="x4x9dg"
Resuma os documentos indexados.
```

```text id="38n7st"
What documents are available?
```

### 4. Perguntas metadata-aware

Perguntas sobre título, autores, data de publicação ou informações normalmente presentes no início do documento recebem tratamento especial.

Exemplos:

```text id="k31pqh"
Who are the authors of the article?
```

```text id="krc1cs"
What is the publication date?
```

```text id="h2z3kd"
What is the title of the paper?
```

Nesses casos, o sistema inclui chunks iniciais dos documentos relevantes, porque metadados costumam aparecer no começo do arquivo e podem não ser recuperados corretamente por similaridade vetorial pura.

Fluxo:

```text id="gvbzhp"
detect metadata question
  |
  v
include initial chunks
  |
  v
merge with vector results
  |
  v
deduplicate chunks
```

## Deduplicação de chunks

O sistema deduplica chunks recuperados antes de montar o contexto.

A deduplicação considera:

* `file_id`;
* `chunk_index`;
* origem do chunk;
* assinatura textual normalizada.

Isso evita repetir o mesmo conteúdo no prompt, especialmente quando o usuário envia cópias iguais ou muito parecidas de um documento.

## Montagem do prompt

Após recuperar os chunks, o backend monta um prompt com:

* instruções do sistema;
* pergunta do usuário;
* histórico recente da sessão;
* contexto recuperado;
* fontes disponíveis.

O prompt orienta o modelo a:

* responder usando somente o contexto fornecido;
* admitir quando a informação não estiver no contexto;
* responder no mesmo idioma da pergunta;
* ser direto;
* mencionar o documento usado como fonte quando possível.

## Idioma da resposta

O sistema tenta responder no mesmo idioma principal usado pelo usuário.

Exemplos:

| Pergunta                        | Resposta esperada               |
| ------------------------------- | ------------------------------- |
| `What is this document about?`  | Inglês                          |
| `Sobre o que é este documento?` | Português                       |
| `Resuma this article`           | Idioma predominante da pergunta |

Essa decisão melhora a experiência em cenários bilíngues e evita forçar sempre português.

## Histórico de sessão

O chat suporta sessões com histórico.

Configuração padrão:

```env id="i4qi2b"
MAX_HISTORY_MESSAGES=6
```

O histórico ajuda o modelo a manter contexto conversacional sem deixar o prompt excessivamente grande.

O frontend também permite:

* criar nova conversa;
* renomear conversa;
* excluir conversa;
* limpar conversa atual;
* alternar entre sessões.

## Endpoints principais

### Health check

```http id="oqa1km"
GET /health
```

Retorna status da API, Redis e configuração do LLM.

### Listar documentos

```http id="81d6ir"
GET /documents
```

Retorna documentos indexados.

### Upload

```http id="l75xg1"
POST /upload
```

Recebe arquivo e indexa o conteúdo.

### Remover documento

```http id="c90m4t"
DELETE /documents/{file_id}
```

Remove documento, chunks e vetores associados.

### Retrieval

```http id="awvrvo"
POST /chat/retrieve
```

Retorna chunks recuperados para uma pergunta, sem chamar o LLM.

Esse endpoint é útil para debug e validação do RAG.

### Chat

```http id="y70fx6"
POST /chat
```

Executa o fluxo completo:

```text id="f0gkr0"
question
  |
  v
retrieval
  |
  v
prompt
  |
  v
LLM
  |
  v
answer + sources
```

### Chat streaming

```http id="rw6v1p"
POST /chat/stream
```

Retorna a resposta do modelo em streaming.

## Observabilidade

O projeto usa LangSmith para observabilidade do fluxo RAG.

Quando habilitado, os traces incluem:

* pergunta do usuário;
* documentos recuperados;
* chunks usados;
* score de retrieval;
* prompt montado;
* chamada ao LLM;
* modelo usado;
* resposta final;
* latência.

Configuração:

```env id="9w4loa"
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=pipefy-rag-chat-cloud
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=<secret>
```

Em ambiente local, o LangSmith pode ficar desabilitado.

## Segurança

A aplicação foi construída como demo técnica, não como produto multiusuário em produção.

Decisões aplicadas:

* o serviço Ollama GPU fica privado;
* a API usa identity token para chamar o serviço privado;
* a chave LangSmith fica no Secret Manager;
* a demo pública não deve receber documentos sensíveis;
* os documentos podem ser removidos pela interface;
* `min-instances=0` reduz exposição e custo quando sem uso.

Limitações:

* não há autenticação por usuário no frontend;
* usuários da demo compartilham o mesmo backend e Redis;
* não há isolamento por tenant;
* não há criptografia em nível de documento;
* não há política avançada de retenção.

## Escalabilidade

A arquitetura atual é suficiente para um case técnico e uma demo controlada.

Pontos de escala:

* API Cloud Run pode aumentar instâncias.
* Frontend Cloud Run escala automaticamente.
* Ollama GPU fica limitado a `max-instances=1` para controle de custo.
* Redis centraliza o armazenamento vetorial.
* O chunking e embedding ocorrem de forma síncrona no upload.

Possíveis melhorias futuras:

* fila assíncrona para ingestão de documentos grandes;
* processamento em background;
* autenticação por usuário;
* isolamento por workspace ou tenant;
* armazenamento durável dos arquivos originais;
* OCR para PDFs escaneados;
* avaliação automática de qualidade do RAG;
* reranking;
* suporte a modelos externos via provider abstraction;
* cache de respostas;
* métricas de uso por sessão.

## Trade-offs técnicos

### Redis como vector store

Redis foi escolhido por simplicidade e velocidade no contexto do case.

Vantagens:

* fácil execução local com Redis Stack;
* baixa complexidade operacional;
* busca vetorial integrada;
* boa performance para demo e datasets pequenos/médios;
* permite armazenar metadados, chunks e vetores no mesmo serviço.

Trade-offs:

* não é a opção mais especializada para grandes volumes;
* requer cuidado com modelagem de chaves e índices;
* em produção de larga escala, uma vector database dedicada poderia ser considerada.

### Ollama

Ollama foi escolhido para executar modelos open-source com baixa complexidade.

Vantagens:

* simples para ambiente local;
* permite uso de modelos open-source;
* evita dependência direta de APIs proprietárias;
* fácil troca de modelo.

Trade-offs:

* cold start maior em cloud;
* uso de GPU aumenta custo;
* tuning de CUDA/runtime pode exigir ajustes;
* modelos locais podem ser menos previsíveis que APIs gerenciadas.

### Cloud Run GPU separado

O Ollama em serviço separado foi escolhido no cloud.

Vantagens:

* separa API e inferência;
* mantém modelo privado;
* melhora observabilidade;
* permite escalar/trocar o modelo separadamente;
* evita acoplar o ciclo de vida da API ao carregamento do modelo.

Trade-offs:

* adiciona chamada HTTP interna;
* exige autenticação serviço-a-serviço;
* aumenta complexidade de deploy;
* primeira resposta pode sofrer cold start.

### Retrieval metadata-aware

A estratégia metadata-aware foi adicionada porque perguntas sobre título, autores e data muitas vezes falham com busca vetorial pura.

Vantagens:

* melhora respostas sobre metadados;
* reduz risco de ignorar os primeiros chunks;
* melhora comportamento com artigos e documentos técnicos.

Trade-offs:

* adiciona heurísticas ao retrieval;
* exige manutenção das regras de detecção;
* pode incluir contexto extra em perguntas ambíguas.

## Limitações conhecidas

* Não há OCR.
* Não há autenticação por usuário.
* Não há isolamento multi-tenant.
* Documentos enviados por diferentes avaliadores ficam no mesmo ambiente.
* O Redis não deve ser usado como armazenamento permanente de documentos críticos.
* PDFs muito complexos podem ter extração parcial.
* A qualidade da resposta depende da qualidade do texto extraído.
* O serviço GPU pode ter cold start.
* O modelo pode responder “não sei” quando o contexto recuperado for insuficiente.

## Resumo da arquitetura final

```text id="1wqayu"
Local:
React + FastAPI + Redis Stack + Ollama local

Cloud:
Cloud Run Frontend
  -> Cloud Run API pública
      -> Memorystore Redis
      -> Cloud Run Ollama GPU privado
          -> qwen2.5:7b
```

O projeto entrega um fluxo RAG completo, observável, reproduzível localmente e demonstrável em cloud, mantendo o modelo open-source e o serviço de inferência privado.
