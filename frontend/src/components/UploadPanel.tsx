import { DragEvent, useState } from "react";

import { uploadDocument } from "../api/client";

type UploadPanelProps = {
  onUploaded: () => Promise<void>;
};

const ALLOWED_EXTENSIONS = [".txt", ".pdf", ".docx"];

export function UploadPanel({ onUploaded }: UploadPanelProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [status, setStatus] = useState<string>("");
  const [isDragging, setIsDragging] = useState(false);

  async function handleUpload() {
    if (files.length === 0) {
      setStatus("Selecione pelo menos um arquivo TXT, PDF ou DOCX.");
      return;
    }

    setStatus(`Enviando ${files.length} documento(s)...`);

    try {
      let indexedChunks = 0;

      for (const file of files) {
        setStatus(`Enviando ${file.name}...`);
        const result = await uploadDocument(file);
        indexedChunks += result.chunks_indexed;
      }

      setStatus(
        `${files.length} documento(s) enviados com sucesso. ${indexedChunks} chunk(s) indexado(s).`
      );
      setFiles([]);
      await onUploaded();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Falha no envio.");
    }
  }

  function handleSelectedFiles(selectedFiles: File[]) {
    const supportedFiles = selectedFiles.filter(isSupportedFile);
    const rejectedFiles = selectedFiles.filter((file) => !isSupportedFile(file));

    setFiles(supportedFiles);

    if (rejectedFiles.length > 0) {
      setStatus(
        "Alguns arquivos foram ignorados. Use apenas arquivos TXT, PDF ou DOCX."
      );
      return;
    }

    setStatus("");
  }

  function handleDragOver(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragging(false);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragging(false);

    handleSelectedFiles(Array.from(event.dataTransfer.files));
  }

  const fileLabel =
    files.length === 0
      ? "Arraste arquivos aqui ou clique para selecionar"
      : files.map((file) => file.name).join(", ");

  return (
    <section className="panel">
      <div className="panel-heading">
        <span className="panel-icon">↑</span>
        <div>
          <h2>Enviar documento</h2>
          <p>
            Adicione arquivos para que o assistente possa responder com base no
            conteúdo.
          </p>
        </div>
      </div>

      <label
        className={isDragging ? "file-picker drag-active" : "file-picker"}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <span>{fileLabel}</span>
        <small>Formatos aceitos: TXT, PDF e DOCX</small>

        <input
          type="file"
          accept=".txt,.pdf,.docx"
          multiple
          onChange={(event) =>
            handleSelectedFiles(Array.from(event.target.files ?? []))
          }
        />
      </label>

      <button type="button" onClick={handleUpload} className="primary-action">
        Enviar documento
      </button>

      {status && <p className="status">{status}</p>}
    </section>
  );
}

function isSupportedFile(file: File): boolean {
  const lowerCaseName = file.name.toLowerCase();

  return ALLOWED_EXTENSIONS.some((extension) =>
    lowerCaseName.endsWith(extension)
  );
}
