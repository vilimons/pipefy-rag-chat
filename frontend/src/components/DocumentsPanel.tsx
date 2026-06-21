import type { DocumentItem } from "../types/api";
import { deleteDocument } from "../api/client";

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
    <section className="card">
      <h2>Indexed documents</h2>

      {documents.length === 0 ? (
        <p>No documents indexed yet.</p>
      ) : (
        <ul className="document-list">
          {documents.map((document) => (
            <li key={document.file_id}>
              <div>
                <strong>{document.name}</strong>
                <span>
                  {document.chunks} chunk(s) ·{" "}
                  {new Date(document.uploaded_at).toLocaleString()}
                </span>
              </div>

              <button
                type="button"
                className="danger"
                onClick={() => handleDelete(document.file_id)}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
