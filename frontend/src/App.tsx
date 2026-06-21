import { useEffect, useMemo, useState } from "react";

import { listDocuments } from "./api/client";
import { ChatPanel } from "./components/ChatPanel";
import { DocumentsPanel } from "./components/DocumentsPanel";
import { UploadPanel } from "./components/UploadPanel";
import type { DocumentItem } from "./types/api";

export function App() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [error, setError] = useState("");
  const [documentQuery, setDocumentQuery] = useState("");

  const filteredDocuments = useMemo(() => {
    const query = documentQuery.trim().toLowerCase();

    if (!query) {
      return documents;
    }

    return documents.filter((document) =>
      document.name.toLowerCase().includes(query)
    );
  }, [documents, documentQuery]);

  const totalChunks = documents.reduce(
    (currentTotal, document) => currentTotal + document.chunks,
    0
  );

  async function refreshDocuments() {
    try {
      setError("");
      const result = await listDocuments();
      setDocuments(result);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível carregar os documentos."
      );
    }
  }

  useEffect(() => {
    void refreshDocuments();
  }, []);

  return (
    <main className="app-frame">
      <aside className="app-sidebar">
        <div className="brand">
          <div className="brand-mark">✦</div>
          <span>Pipefy RAG</span>
        </div>

        <section className="workspace-card">
          <strong>Workspace local</strong>
          <span>Ambiente de desenvolvimento</span>
        </section>

        <nav className="sidebar-nav" aria-label="Navegação principal">
          <a
            className="active"
            href="https://smith.langchain.com/"
            target="_blank"
            rel="noreferrer"
          >
            <span>◌</span>
            LangSmith
          </a>
        </nav>
      </aside>

      <section className="app-main">
        <header className="top-search">
          <div className="search-box">
            <span>⌕</span>
            <input
              value={documentQuery}
              onChange={(event) => setDocumentQuery(event.target.value)}
              placeholder="Buscar documentos indexados..."
            />
          </div>
        </header>

        <section className="page-heading">
          <p>Case técnico Pipefy</p>
          <h1>Assistente RAG para documentos</h1>
          <span>
            Envie documentos, recupere fontes relevantes e converse com uma
            base de conhecimento vetorizada no Redis.
          </span>
        </section>

        <section className="summary-strip two-columns" aria-label="Resumo da aplicação">
          <div>
            <strong>{documents.length}</strong>
            <span>Documentos</span>
          </div>
          <div>
            <strong>{totalChunks}</strong>
            <span>Chunks indexados</span>
          </div>
        </section>

        {error && <p className="error banner">{error}</p>}

        <div className="workspace-grid">
          <aside className="left-rail" id="documentos">
            <UploadPanel onUploaded={refreshDocuments} />
            <DocumentsPanel
              documents={filteredDocuments}
              onChanged={refreshDocuments}
            />
          </aside>

          <section id="chat">
            <ChatPanel />
          </section>
        </div>
      </section>
    </main>
  );
}
