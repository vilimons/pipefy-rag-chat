import { useEffect, useState } from "react";

import { listDocuments } from "./api/client";
import { ChatPanel } from "./components/ChatPanel";
import { DocumentsPanel } from "./components/DocumentsPanel";
import { UploadPanel } from "./components/UploadPanel";
import type { DocumentItem } from "./types/api";

export function App() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [error, setError] = useState("");

  async function refreshDocuments() {
    try {
      setError("");
      const result = await listDocuments();
      setDocuments(result);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Failed to load documents."
      );
    }
  }

  useEffect(() => {
    void refreshDocuments();
  }, []);

  return (
    <main className="app">
      <header className="hero">
        <div>
          <p className="eyebrow">Pipefy technical case</p>
          <h1>RAG Chat</h1>
          <p>
            Upload documents, index them in Redis Vector Search, and ask
            questions using a local Ollama LLM.
          </p>
        </div>
      </header>

      {error && <p className="error">{error}</p>}

      <div className="grid">
        <div className="sidebar">
          <UploadPanel onUploaded={refreshDocuments} />
          <DocumentsPanel documents={documents} onChanged={refreshDocuments} />
        </div>

        <ChatPanel />
      </div>
    </main>
  );
}
