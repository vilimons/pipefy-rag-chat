import { FormEvent, useState } from "react";

import { sendChatMessage } from "../api/client";
import type { SourceChunk } from "../types/api";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  sources?: SourceChunk[];
};

export function ChatPanel() {
  const [sessionId] = useState(() => crypto.randomUUID());
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();

    const trimmedQuestion = question.trim();

    if (!trimmedQuestion) {
      return;
    }

    setError("");
    setIsLoading(true);
    setQuestion("");

    setMessages((currentMessages) => [
      ...currentMessages,
      {
        role: "user",
        content: trimmedQuestion
      }
    ]);

    try {
      const response = await sendChatMessage({
        question: trimmedQuestion,
        sessionId,
        topK: 3
      });

      setMessages((currentMessages) => [
        ...currentMessages,
        {
          role: "assistant",
          content: response.answer,
          sources: response.sources
        }
      ]);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Failed to send message."
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="card chat-card">
      <h2>RAG Chat</h2>
      <p className="session">Session: {sessionId}</p>

      <div className="messages">
        {messages.length === 0 ? (
          <p>Ask something about the indexed documents.</p>
        ) : (
          messages.map((message, index) => (
            <article key={`${message.role}-${index}`} className={message.role}>
              <strong>{message.role === "user" ? "You" : "Assistant"}</strong>
              <p>{message.content}</p>

              {message.sources && message.sources.length > 0 && (
                <details>
                  <summary>Sources</summary>
                  <ul>
                    {message.sources.map((source) => (
                      <li key={`${source.file_id}-${source.chunk_index}`}>
                        <strong>{source.source}</strong> · score {source.score}
                        <p>{source.chunk}</p>
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </article>
          ))
        )}
      </div>

      <form onSubmit={handleSubmit} className="chat-form">
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask a question about your documents..."
        />
        <button type="submit" disabled={isLoading}>
          {isLoading ? "Thinking..." : "Send"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}
    </section>
  );
}
