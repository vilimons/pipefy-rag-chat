import { deleteDocument } from "../api/client";
import type { DocumentItem } from "../types/api";

type DocumentsPanelProps = {
  documents: DocumentItem[];
  onChanged: () => Promise<void>;
};

export function DocumentsPanel({ documents, onChanged }: DocumentsPanelProps) {
  async function handleDelete(fileId: string) {
    await deleteDocument(fileId);
    await onChanged();
  }

  return (
    <section className="panel">
      <div className="panel-heading">
        <span className="panel-icon">◆</span>
        <div>
          <h2>Documentos indexados</h2>
          <p>Base de conhecimento disponível para o chat.</p>
        </div>
      </div>

      {documents.length === 0 ? (
        <div className="empty-state">
          <strong>Nenhum documento enviado</strong>
          <span>Envie um arquivo para começar a conversar.</span>
        </div>
      ) : (
        <ul className="document-list">
          {documents.map((document) => (
            <li key={document.file_id}>
              <div>
                <strong>{document.name}</strong>
                <span>
                  {document.chunks} chunk(s) ·{" "}
                  {new Date(document.uploaded_at).toLocaleString("pt-BR")}
                </span>
              </div>

              <button
                type="button"
                className="danger compact"
                onClick={() => handleDelete(document.file_id)}
              >
                Remover
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
