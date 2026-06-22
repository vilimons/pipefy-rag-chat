# Arquitetura — Pipefy RAG Chat

Este documento descreve a arquitetura técnica do projeto Pipefy RAG Chat, incluindo os principais componentes, fluxos de dados, decisões técnicas, estratégia de retrieval, observabilidade e possíveis evoluções para produção.

## 1. Visão geral

O Pipefy RAG Chat é uma aplicação full-stack que permite o upload de documentos e a realização de perguntas sobre o conteúdo indexado.

A aplicação segue uma arquitetura RAG, Retrieval-Augmented Generation, onde o modelo de linguagem não responde apenas com conhecimento próprio. Antes da geração da resposta, o backend recupera trechos relevantes dos documentos indexados, monta um contexto controlado e envia esse contexto para o LLM.

O objetivo é garantir que as respostas sejam fundamentadas nos documentos enviados pelo usuário.

## 2. Componentes principais

A solução é composta por quatro blocos principais:

```text
Frontend React
  -> interface de upload, listagem de documentos e chat

FastAPI Backend
  -> API REST, streaming SSE, ingestão, retrieval e orquestração RAG

Redis Stack
  -> armazenamento de documentos, chunks, embeddings, histórico e índice vetorial

Ollama
  -> execução local do modelo open-source usado para geração das respostas
```

Além desses componentes, o projeto possui integração opcional com LangSmith para tracing do fluxo RAG.

## 3. Diagrama de alto nível

```text
Usuário
  |
  v
Browser
  |
  | HTTP / SSE
  v
Frontend React + Nginx
  |
  | proxy /api
  v
FastAPI Backend
  |
  | upload / chat / streaming
  v
Serviços internos do backend
  |
  | document loading
  | chunking
  | embeddings
  | retrieval
  | prompt building
  | LLM call
  v
Redis Stack + Ollama
```

## 4. Responsabilidades por camada

### Frontend

O frontend é responsável por:

* permitir upload de documentos;
* listar documentos indexados;
* iniciar conversas;
* manter múltiplas sessões de chat;
* consumir respostas em streaming via Server-Sent Events;
* exibir fontes usadas pelo RAG;
* apresentar estados de loading, erro e resposta.

### Backend

O backend é responsável por:

* expor os endpoints HTTP;
* validar uploads;
* extrair texto de documentos;
* dividir documentos em chunks;
* gerar embeddings;
* salvar documentos e chunks no Redis;
* executar busca vetorial;
* aplicar estratégia de retrieval;
* orquestrar o fluxo RAG com LangGraph;
* chamar o modelo via Ollama;
* registrar histórico de conversa;
* retornar resposta e fontes.

### Redis Stack

O Redis Stack é responsável por:

* armazenar metadados dos documentos;
* armazenar chunks;
* armazenar embeddings binários;
* manter o índice vetorial com RedisSearch;
* armazenar histórico de mensagens por sessão;
* persistir dados localmente via volume Docker.

### Ollama

O Ollama é responsável por:

* disponibilizar localmente o modelo LLM;
* receber prompts do backend;
* gerar respostas completas ou em streaming.

## 5. Fluxo de upload e indexação

O fluxo de upload transforma um arquivo enviado pelo usuário em chunks pesquisáveis por similaridade vetorial.

```text id="o5x3zp"
Usuário faz upload
  |
  v
POST /upload
  |
  v
Validação do arquivo
  |
  | formatos aceitos: TXT, PDF, DOCX
  v
Extração de texto
  |
  v
Chunking
  |
  | chunk_size configurável
  | chunk_overlap configurável
  v
Geração de embeddings
  |
  v
Persistência no Redis
  |
  | document:{file_id}
  | doc:{file_id}:chunk:{chunk_index}
  v
Índice RedisSearch
```

### 5.1 Extração de texto

A aplicação suporta documentos textuais nos formatos:

* TXT
* PDF
* DOCX

Cada tipo de arquivo é processado pelo serviço de carregamento de documentos. Caso o arquivo não possua texto legível ou esteja em formato inválido, a API retorna uma mensagem controlada de erro.

### 5.2 Chunking

Após a extração, o texto é dividido em trechos menores.

Essa etapa é importante porque enviar documentos inteiros para o modelo seria ineficiente e poderia ultrapassar o limite de contexto do LLM.

Os principais parâmetros são:

```text id="hxdb81"
CHUNK_SIZE
CHUNK_OVERLAP
```

O overlap ajuda a preservar continuidade semântica entre chunks vizinhos.

### 5.3 Embeddings

Cada chunk recebe um embedding gerado localmente com Sentence Transformers.

O modelo configurado por padrão é:

```text id="f59xeo"
sentence-transformers/all-MiniLM-L6-v2
```

Esse modelo gera vetores de dimensão 384, configurados em:

```text id="giqh3x"
REDIS_VECTOR_DIM=384
```

### 5.4 Estrutura no Redis

Os metadados do documento são armazenados em uma chave:

```text id="ld6zzq"
document:{file_id}
```

Exemplo de campos:

```text id="wyztzs"
file_id
name
uploaded_at
chunks
```

Os chunks são armazenados em chaves:

```text id="blfnu6"
doc:{file_id}:chunk:{chunk_index}
```

Exemplo de campos:

```text id="2lvwpx"
file_id
source
chunk_index
content
uploaded_at
embedding
```

O campo `embedding` é armazenado em formato binário, pois o RedisSearch utiliza esse valor para a busca vetorial.

## 6. Fluxo de pergunta e resposta

O fluxo de chat recebe uma pergunta do usuário, recupera contexto relevante, chama o modelo e retorna uma resposta fundamentada.

```text id="8sw6kk"
Usuário envia pergunta
  |
  v
POST /chat ou POST /chat/stream
  |
  v
Geração do embedding da pergunta
  |
  v
Retrieval no Redis
  |
  v
Carregamento do histórico da sessão
  |
  v
Construção do prompt
  |
  v
Chamada ao Ollama
  |
  v
Resposta final + fontes
  |
  v
Persistência no histórico da sessão
```

### 6.1 Chat sem streaming

No endpoint `POST /chat`, a API retorna a resposta completa após a finalização da chamada ao LLM.

Esse modo é mais simples e útil para testes via API ou documentação interativa.

### 6.2 Chat com streaming

No endpoint `POST /chat/stream`, a API usa Server-Sent Events para enviar partes da resposta conforme o modelo gera o texto.

O frontend consome esses eventos e atualiza a mensagem do assistente progressivamente.

Esse fluxo melhora a experiência do usuário, principalmente quando o modelo local demora alguns segundos para concluir a resposta.

## 7. Orquestração com LangGraph

O fluxo RAG é representado como um grafo de execução usando LangGraph.

A separação em nós deixa o pipeline mais modular e facilita manutenção, tracing e evolução.

```text id="lu016t"
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

### 7.1 retriever_node

Responsável por recuperar os chunks relevantes no Redis.

Ele gera o embedding da pergunta e aplica a estratégia de retrieval apropriada.

### 7.2 history_node

Responsável por carregar as últimas mensagens da sessão.

O histórico é limitado por configuração para evitar prompts muito longos.

### 7.3 context_builder_node

Responsável por montar o contexto que será enviado ao modelo.

Esse contexto inclui:

* chunks recuperados;
* fontes;
* pergunta atual;
* histórico recente da sessão.

### 7.4 llm_node

Responsável por chamar o modelo configurado no Ollama.

### 7.5 response_formatter_node

Responsável por montar a resposta final da API, incluindo:

* resposta textual;
* fontes utilizadas;
* session_id;
* metadados de execução.

## 8. Estratégia de retrieval

A estratégia de retrieval foi ajustada para evitar dependência exclusiva de busca vetorial pura.

A busca vetorial é eficiente para perguntas específicas, mas pode apresentar comportamento ruim em perguntas amplas, como:

```text id="khfzgj"
Sobre o que tratam os documentos?
```

Nesse tipo de pergunta, a busca vetorial pode retornar vários chunks de apenas um documento, mesmo quando existem múltiplos documentos indexados.

Para resolver isso, o retriever aplica estratégias diferentes conforme o tipo da pergunta.

### 8.1 Perguntas amplas sobre a base

Quando a pergunta indica intenção de visão geral, o sistema recupera chunks representativos de múltiplos documentos.

Exemplos:

```text id="jzzun1"
Sobre o que tratam os documentos?
Resuma os arquivos.
O que existe na base de conhecimento?
Quais documentos estão indexados?
```

Nesse caso, o objetivo não é encontrar apenas o chunk semanticamente mais parecido com a pergunta, mas dar uma visão geral do conjunto de documentos.

### 8.2 Perguntas específicas de conteúdo

Quando a pergunta é sobre um tema específico, o sistema utiliza busca vetorial por similaridade.

Exemplos:

```text id="dlany4"
O que é Pipefy?
Qual experiência profissional aparece no currículo?
O que o artigo diz sobre Marte?
```

Nesse caso, a busca vetorial é adequada porque a pergunta possui intenção semântica clara.

### 8.3 Perguntas sobre arquivo específico

Quando a pergunta menciona explicitamente um nome de arquivo, o sistema prioriza chunks daquele documento.

Exemplo:

```text id="kqszsd"
O que você pode dizer sobre o arquivo exemplo.pdf?
```

Esse comportamento é válido porque o usuário direcionou a pergunta para um documento específico.

### 8.4 Por que essa estratégia foi necessária

Durante os testes, uma pergunta ampla sobre os documentos recuperava informações de apenas um arquivo, ignorando outros documentos indexados.

A correção não foi criar regras sobre conteúdos específicos. A solução foi tornar o retrieval mais consciente da intenção da pergunta:

```text id="5uhv7p"
pergunta ampla
  -> visão geral da coleção

pergunta específica
  -> busca vetorial

pergunta com nome de arquivo
  -> priorização daquele documento
```

Essa abordagem mantém o comportamento genérico e permite processar qualquer conteúdo suportado, como currículos, artigos, documentos técnicos, textos sobre esportes, tecnologia ou qualquer outro tema.

## 9. Histórico de conversa

O histórico de conversa é armazenado no Redis por `session_id`.

Cada sessão mantém as últimas mensagens trocadas entre usuário e assistente.

O número máximo de mensagens consideradas no prompt é controlado por:

```text id="5amhbb"
MAX_HISTORY_MESSAGES
```

Esse limite evita crescimento excessivo do prompt e reduz o risco de o histórico dominar a resposta atual.

O prompt também instrui o modelo a usar o contexto recuperado da pergunta atual como fonte principal.

## 10. Observabilidade com LangSmith

A integração com LangSmith é opcional e controlada por variável de ambiente.

```env id="tfuas6"
LANGSMITH_TRACING=true
```

Quando habilitado, o backend registra etapas importantes do fluxo RAG, como:

* recuperação de documentos;
* construção de contexto;
* chamada ao LLM;
* formatação da resposta.

Durante testes automatizados, o tracing é desativado para evitar poluição do projeto no LangSmith:

```bash id="xx0sel"
LANGSMITH_TRACING=false
```

## 11. Streaming com Server-Sent Events

O endpoint de streaming usa Server-Sent Events para enviar a resposta progressivamente ao frontend.

O fluxo envia eventos como:

```text id="n9be6m"
metadata
sources
token
done
error
```

Esse modelo permite que o usuário veja a resposta sendo construída em tempo real.

Em caso de erro durante o retrieval ou geração, o backend retorna um evento controlado de erro em vez de quebrar a conexão abruptamente.

## 12. Persistência

O Redis Stack utiliza volume Docker para persistência local.

Isso permite que documentos, chunks, embeddings e histórico sobrevivam a reinícios normais dos containers.

Para parar os containers mantendo os dados:

```bash id="xmhpza"
make down
```

Para remover containers e volumes:

```bash id="0ky8hp"
make down-volumes
```

O comando `down-volumes` deve ser usado apenas quando se deseja limpar completamente o ambiente local.

## 13. Testes e validação

O projeto possui testes automatizados no backend usando `pytest`.

Os testes cobrem pontos como:

* extração e carregamento de documentos;
* ingestão e chunking;
* persistência e recuperação no Redis;
* estratégia de retrieval;
* fluxo RAG;
* histórico de conversa;
* tratamento de erros;
* endpoints principais da API.

A validação local pode ser executada com:

```bash
make validate
```

Esse comando executa:

```text
backend tests
backend lint
frontend build
```

Os testes do backend são executados com LangSmith desativado:

```bash
LANGSMITH_TRACING=false
```

Isso evita envio de traces de teste para o projeto no LangSmith.

## 14. CI com GitHub Actions

O projeto possui workflow de CI configurado em:

```text
.github/workflows/ci.yml
```

O pipeline é executado em push e pull request.

Ele valida:

* build das imagens Docker da API e do frontend;
* testes automatizados do backend;
* lint do backend com Ruff;
* build do frontend.

Esse processo garante que alterações no projeto passem por uma validação mínima antes da entrega ou evolução do código.

## 15. Decisões técnicas

### 15.1 FastAPI

O FastAPI foi escolhido por ser leve, produtivo e adequado para APIs Python modernas. Ele também fornece documentação automática via Swagger em `/docs`.

### 15.2 Redis Stack

O Redis Stack foi utilizado porque o case técnico solicita Redis/RedisSearch e porque ele permite concentrar armazenamento de metadados, chunks, embeddings, histórico e índice vetorial em um único serviço.

### 15.3 Sentence Transformers

Os embeddings são gerados localmente com Sentence Transformers, evitando dependência de APIs externas pagas e mantendo o projeto executável em ambiente local.

### 15.4 Ollama

O Ollama permite utilizar um modelo open-source local para geração das respostas. Essa escolha reduz dependência de provedores externos e facilita a execução do projeto sem credenciais de LLM pagas.

### 15.5 LangGraph

O LangGraph foi utilizado para tornar o fluxo RAG explícito, modular e observável. A separação em nós facilita manutenção, tracing e evolução futura.

### 15.6 Server-Sent Events

Server-Sent Events foram utilizados para streaming por serem simples de implementar e suficientes para o caso de uso de resposta progressiva do assistente.

### 15.7 Docker Compose

Docker Compose foi utilizado para simplificar a execução local da stack completa, incluindo API, frontend e Redis.

## 16. Trade-offs

### 16.1 Modelo local

O uso de um modelo local via Ollama facilita a execução sem custos externos, mas a qualidade das respostas pode ser inferior à de modelos proprietários mais avançados.

### 16.2 Redis como vector store

Redis Stack é suficiente para o escopo do case e simplifica a arquitetura. Em um cenário de grande escala, poderia ser necessário avaliar soluções gerenciadas ou bancos vetoriais especializados.

### 16.3 Ingestão síncrona

A ingestão dos documentos ocorre de forma síncrona. Para arquivos muito grandes ou alto volume de usuários, seria melhor mover essa etapa para jobs assíncronos.

### 16.4 PDFs sem OCR

A solução suporta PDFs com texto extraível. PDFs escaneados não são processados porque OCR não foi implementado.

### 16.5 Estratégia de retrieval

A estratégia atual melhora perguntas amplas e perguntas específicas, mas ainda poderia evoluir com reranking, avaliação automática e métricas de qualidade de retrieval.

## 17. Limitações conhecidas

* A qualidade final da resposta depende do modelo configurado no Ollama.
* PDFs escaneados não são suportados.
* Arquivos muito grandes podem exigir otimizações de chunking e ingestão.
* O projeto não implementa autenticação de usuários.
* O projeto não implementa controle de permissões por documento.
* O Redis roda localmente via Docker Compose.
* A aplicação foi construída para o escopo do case técnico, não para alto volume de produção.

## 18. Possíveis evoluções para produção

Para um ambiente produtivo, o projeto poderia evoluir com:

* autenticação e autorização;
* controle de acesso por documento;
* jobs assíncronos para ingestão;
* fila para processamento de arquivos;
* OCR para PDFs escaneados;
* reranking dos chunks recuperados;
* avaliação automatizada da qualidade do RAG;
* logs estruturados;
* métricas de latência, erro e uso;
* rate limiting;
* secrets manager;
* deploy em cloud;
* Redis gerenciado ou vector database dedicado;
* suporte a múltiplos provedores de LLM;
* pipeline CI/CD com deploy automatizado.

## 19. Fluxo esperado para execução local

O fluxo recomendado para validar o projeto localmente é:

```bash
cp .env.example .env
make up
```

Depois acessar:

```text
http://localhost:3000
```

Em seguida:

1. Fazer upload de documentos TXT, PDF ou DOCX.
2. Perguntar sobre o conteúdo dos documentos.
3. Verificar se a resposta apresenta fontes.
4. Testar perguntas amplas sobre todos os documentos.
5. Testar perguntas específicas sobre um tema.
6. Testar perguntas direcionadas a um arquivo.
7. Validar múltiplas sessões de chat.
8. Executar a validação final com `make validate`.

## 20. Conclusão

A arquitetura do Pipefy RAG Chat foi desenhada para atender ao case técnico com uma solução funcional, modular e extensível.

O projeto cobre o fluxo completo de uma aplicação RAG:

```text
upload de documentos
  -> extração de texto
  -> chunking
  -> embeddings
  -> indexação vetorial
  -> retrieval
  -> geração com LLM
  -> resposta com fontes
```

Além do fluxo principal, o projeto inclui diferenciais como LangGraph, LangSmith opcional, streaming com SSE, múltiplas sessões, suporte a DOCX, CI com GitHub Actions e comandos padronizados de validação.

A solução permanece genérica em relação ao conteúdo dos documentos, permitindo processar diferentes tipos de texto dentro dos formatos suportados.
