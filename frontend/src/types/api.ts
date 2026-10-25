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

/** Заметка «было → лучше» (D3a.2): пишет проверка речи, экран только показывает. */
export interface LanguageNote {
  turn_index: number;
  kind: "error" | "style";
  /** Дословный фрагмент распознанной реплики. */
  said: string;
  better: string;
  /** Причина до пяти слов; может быть пустой. */
  why: string;
  spoken: boolean;
}

/** Строка разговора в History (doc 15, `GET /sessions/talks`). */
export interface TalkListItem {
  id: string;
  started_at: string;
  ended_at: string | null;
  duration_sec: number | null;
  status: string;
  notes_count: number;
}

export interface TalkDetail extends TalkListItem {
  transcript: TranscriptTurn[];
  language_notes: LanguageNote[];
}

/** Ответ «Add to Useful Words»: `exists` — фраза уже в банке, повтор не дублирует. */
export interface AddedWord {
  status: "added" | "exists";
  term_en: string;
  translation_ru: string;
}

/** Ключи kv-настроек (doc 15, `GET/PATCH /settings`). */
export interface UserSettings {
  show_live_transcript: boolean;
  interview_duration_min: number;
  silence_threshold_ms: number;
  speech_length_scale: number;
  /** `MediaDeviceInfo.deviceId` выбранного входа; `null` — системный по умолчанию. */
  mic_device_id: string | null;
}
