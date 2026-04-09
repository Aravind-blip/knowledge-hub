export type SourceCitation = {
  chunk_id: string;
  document_id: string;
  file_name: string;
  snippet: string;
  page_number: number | null;
  relevance_score: number;
};

export type ChatMessage = {
  id: string;
  role: "user" | "system";
  content: string;
  citations: SourceCitation[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type DocumentRecord = {
  id: string;
  file_name: string;
  original_name: string;
  status: string;
  content_type: string;
  file_size: number;
  created_at: string;
  metadata: Record<string, unknown>;
};

export type DocumentListResponse = {
  items: DocumentRecord[];
};

export type AskResponse = {
  session_id: string;
  answer: string;
  citations: SourceCitation[];
  retrieval_count: number;
  insufficient_information: boolean;
  confidence_note: string | null;
  answer_message: ChatMessage;
  question_message: ChatMessage;
};

export type RetrieveResponse = {
  question: string;
  citations: SourceCitation[];
  retrieval_count: number;
  insufficient_information: boolean;
  confidence_note: string | null;
};

export type SessionResponse = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
};

export type SessionSummary = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type SessionListResponse = {
  items: SessionSummary[];
};
