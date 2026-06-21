import { useState } from "react";

import { uploadDocument } from "../api/client";

type UploadPanelProps = {
  onUploaded: () => Promise<void>;
};

export function UploadPanel({ onUploaded }: UploadPanelProps) {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string>("");

  async function handleUpload() {
    if (!file) {
      setStatus("Select a TXT or PDF file first.");
      return;
    }

    setStatus("Uploading and indexing document...");

    try {
      const result = await uploadDocument(file);
      setStatus(
        `Indexed ${result.filename} with ${result.chunks_indexed} chunk(s).`
      );
      setFile(null);
      await onUploaded();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Upload failed.");
    }
  }

  return (
    <section className="card">
      <h2>Upload document</h2>
      <p>Upload a TXT or PDF file to index it in Redis Vector Search.</p>

      <input
        type="file"
        accept=".txt,.pdf"
        onChange={(event) => setFile(event.target.files?.[0] ?? null)}
      />

      <button type="button" onClick={handleUpload}>
        Upload
      </button>

      {status && <p className="status">{status}</p>}
    </section>
  );
}
