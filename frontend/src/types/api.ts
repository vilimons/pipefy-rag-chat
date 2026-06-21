export type DocumentItem = {
  file_id: string;
  name: string;
  uploaded_at: string;
  chunks: number;
};

export type UploadResponse = {
  file_id: string;
  filename: string;
  chunks_indexed: number;
  status: string;
};

export type SourceChunk = {
  chunk: string;
  source: string;
  score: number;
  chunk_index: number | null;
  file_id: string | null;
};

export type ChatResponse = {
  answer: string;
  sources: SourceChunk[];
  session_id: string;
};
