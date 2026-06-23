import type {
  ChatHistoryResponse,
  ChatResponse,
  ClearChatHistoryResponse,
  DocumentItem,
  SourceChunk,
  UploadResponse
} from "../types/api";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";


export type HealthResponse = {
  status: string;
  app: string;
  environment: string;
  redis: string;
  llm?: {
    provider: string;
    model: string;
  };
};

type StreamEvent = {
  event: string;
  data: unknown;
};

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Requisição falhou com status ${response.status}`;

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


export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`);
  return parseResponse<HealthResponse>(response);
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

export async function getChatHistory(
  sessionId: string
): Promise<ChatHistoryResponse> {
  const response = await fetch(
    `${API_BASE_URL}/chat/sessions/${sessionId}/history`
  );

  return parseResponse<ChatHistoryResponse>(response);
}

export async function clearChatHistory(
  sessionId: string
): Promise<ClearChatHistoryResponse> {
  const response = await fetch(
    `${API_BASE_URL}/chat/sessions/${sessionId}/history`,
    {
      method: "DELETE"
    }
  );

  return parseResponse<ClearChatHistoryResponse>(response);
}

export async function streamChatMessage(
  params: {
    question: string;
    sessionId: string;
    topK: number;
  },
  onEvent: (event: StreamEvent) => void
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream"
    },
    body: JSON.stringify({
      question: params.question,
      session_id: params.sessionId,
      top_k: params.topK
    })
  });

  if (!response.ok) {
    throw new Error(`Requisição falhou com status ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Resposta em streaming indisponível.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();

    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });

    let eventBoundary = buffer.indexOf("\n\n");

    while (eventBoundary !== -1) {
      const rawEvent = buffer.slice(0, eventBoundary);
      buffer = buffer.slice(eventBoundary + 2);

      const parsedEvent = parseSseEvent(rawEvent);

      if (parsedEvent) {
        onEvent(parsedEvent);
      }

      eventBoundary = buffer.indexOf("\n\n");
    }
  }

  if (buffer.trim()) {
    const parsedEvent = parseSseEvent(buffer);

    if (parsedEvent) {
      onEvent(parsedEvent);
    }
  }
}

function parseSseEvent(rawEvent: string): StreamEvent | null {
  const lines = rawEvent.split("\n");

  let event = "message";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.replace("event:", "").trim();
    }

    if (line.startsWith("data:")) {
      dataLines.push(line.replace("data:", "").trim());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  const rawData = dataLines.join("\n");

  return {
    event,
    data: JSON.parse(rawData)
  };
}
