export type User = {
  id: number;
  username: string;
  name: string;
  avatar_url: string;
  external_user_id: string;
  is_staff: boolean;
};

export type BatchJob = {
  id: number;
  title: string;
  status: string;
  total_count: number;
  processed_count: number;
  failed_count: number;
  current_step: string;
  error_message: string;
  image_count: number;
  created_at: string;
  updated_at: string;
};

export type UploadedImage = {
  id: number;
  batch: number;
  image_url: string;
  original_name: string;
  description: string;
  sort_order: number;
};

export type FaqDraft = {
  id: number;
  batch: number;
  image: UploadedImage | null;
  generation_item: number | null;
  generation_title: string;
  generation_image_urls: string[];
  question: string;
  similar_questions: string[];
  answer_text: string;
  status: string;
  error_message: string;
  is_edited: boolean;
};

export type ProgressState = {
  id: number;
  status: string;
  total_count: number;
  processed_count: number;
  failed_count: number;
  current_step: string;
  error_message: string;
  percent: number;
};

export type WebhookUploadItem = {
  draft_ids: number[];
  question: string;
  similar_questions: string[];
  answer_text: string;
};

export type GenerationItemDraft = {
  id: string;
  image_ids: number[];
  title: string;
  description: string;
  sort_order: number;
  is_combined: boolean;
};

export type GenerationItem = {
  id: number;
  batch: number;
  images: UploadedImage[];
  image_ids: number[];
  title: string;
  description: string;
  sort_order: number;
  is_combined: boolean;
  created_at: string;
  updated_at: string;
};

export type UploadRecord = {
  id: number;
  batch: number;
  draft: number | null;
  question: string;
  similar_questions: string[];
  answer_text: string;
  image_cdn_urls: string[];
  wechat_image_items: Record<string, unknown>[];
  wechat_record_id: string;
  wechat_record_values: Record<string, unknown>;
  source_draft_ids: number[];
  response_summary: Record<string, unknown>;
  ok: boolean;
  created_at: string;
};

export type LlmUsageItem = {
  id: number;
  batch: number;
  batch_title: string;
  draft: number | null;
  draft_question: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  ok: boolean;
  error_message: string;
  created_at: string;
};

export type LlmUsageSummary = {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  items: LlmUsageItem[];
};

