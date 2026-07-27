// REST payload shapes — mirror docs/15-api-websocket-spec.md

export interface InterviewListItem {
  id: string;
  started_at: string;
  ended_at: string | null;
  interview_mode: string;
  duration_sec: number | null;
  status: string;
  has_review: boolean;
  review_session_id: string | null;
  has_debrief: boolean;
  summary_kind: "minimal" | "full" | null;
}

export interface TranscriptTurn {
  role: "agent" | "user";
  text: string;
  timestamp_ms: number;
  turn_index: number;
  state?: string | null;
  question_id?: string | null;
}

export interface Debrief {
  overall_summary?: string;
  scores?: Record<string, number>;
  strengths?: { text: string; reference?: string }[];
  improvements?: {
    category?: string;
    problem: string;
    evidence?: string;
    impact?: string;
    fix: string;
  }[];
  weak_answers?: {
    question: string;
    user_answer_summary?: string;
    suggested_rephrase: string;
    issue?: string;
  }[];
  vocabulary?: VocabularyItem[];
  consistency_flags?: string[];
  next_session_focus?: string[];
}

export interface InterviewDetail extends InterviewListItem {
  transcript: TranscriptTurn[];
  metadata: Record<string, unknown>;
  debrief: Debrief | null;
}

export interface ReviewDetail {
  id: string;
  source_interview_id: string;
  transcript: TranscriptTurn[];
  status: string;
}

export interface VocabularyItem {
  id?: string;
  term_en: string;
  translation_ru: string;
  example_en: string;
  category?: string;
  status?: string;
  times_seen?: number;
  added_at?: string;
}
