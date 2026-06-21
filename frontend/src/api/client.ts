import type { ChatResponse, DocumentItem, UploadResponse } from "../types/api";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const payload = await response.json();
      message = payload.detail ?? message;
    } catch {
      // Keep default message.
    }

    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export async function listDocuments(): Promise<DocumentItem[]> {
  const response = await fetch(`${API_BASE_URL}/documents`);
  return parseResponse<DocumentItem[]>(response);
}

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: "POST",
    body: formData
  });

  return parseResponse<UploadResponse>(response);
}

export async function deleteDocument(fileId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/documents/${fileId}`, {
    method: "DELETE"
  });

  await parseResponse(response);
}

export async function sendChatMessage(params: {
  question: string;
  sessionId: string;
  topK: number;
}): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      question: params.question,
      session_id: params.sessionId,
      top_k: params.topK
    })
  });

  return parseResponse<ChatResponse>(response);
}
