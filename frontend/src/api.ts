import type { BatchJob, FaqDraft, GenerationItem, GenerationItemDraft, LlmUsageSummary, ProgressState, UploadedImage, UploadRecord, User, WebhookUploadItem } from './types';

const jsonHeaders = { 'Content-Type': 'application/json' };

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method || 'GET').toUpperCase();
  const headers = new Headers(options.headers);
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const token = getCookie('csrftoken');
    if (token) headers.set('X-CSRFToken', token);
  }
  const response = await fetch(url, { credentials: 'include', ...options, headers });
  if (!response.ok) {
    const data = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(data.detail || JSON.stringify(data));
  }
  return response.json() as Promise<T>;
}

function getCookie(name: string): string {
  const match = document.cookie.match(new RegExp(`(^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[2]) : '';
}

export const api = {
  me: () => request<User>('/api/auth/me/'),
  login: (username: string, password: string) =>
    request<User>('/api/auth/login/', {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify({ username, password }),
    }),
  logout: () =>
    request<{ ok: boolean }>('/api/auth/logout/', {
      method: 'POST',
      headers: jsonHeaders,
    }),
  createBatch: (title: string) =>
    request<BatchJob>('/api/batches/', {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify({ title }),
    }),
  listBatches: () => request<BatchJob[]>('/api/batches/'),
  uploadImages: (batchId: number, files: File[]) => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    return request<UploadedImage[]>(`/api/batches/${batchId}/images/`, {
      method: 'POST',
      body: formData,
    });
  },
  updateImageDescription: (imageId: number, description: string) =>
    request<UploadedImage>(`/api/images/${imageId}/`, {
      method: 'PATCH',
      headers: jsonHeaders,
      body: JSON.stringify({ description }),
    }),
  saveGenerationItems: (batchId: number, items: GenerationItemDraft[]) =>
    request<GenerationItem[]>(`/api/batches/${batchId}/generation-items/`, {
      method: 'PUT',
      headers: jsonHeaders,
      body: JSON.stringify({
        items: items.map(({ id: _id, ...item }) => item),
      }),
    }),
  startGenerate: (batchId: number) =>
    request<{ ok: boolean }>(`/api/batches/${batchId}/generate/`, {
      method: 'POST',
      headers: jsonHeaders,
    }),
  getProgress: (batchId: number) => request<ProgressState>(`/api/batches/${batchId}/progress/`),
  getDrafts: (batchId: number) => request<FaqDraft[]>(`/api/batches/${batchId}/drafts/`),
  updateDraft: (draft: FaqDraft) =>
    request<FaqDraft>(`/api/drafts/${draft.id}/`, {
      method: 'PATCH',
      headers: jsonHeaders,
      body: JSON.stringify({
        question: draft.question,
        similar_questions: draft.similar_questions,
        answer_text: draft.answer_text,
      }),
    }),
  uploadWebhook: (batchId: number, webhookUrl: string, uploadItems?: WebhookUploadItem[]) =>
    request<{ ok: boolean }>(`/api/batches/${batchId}/upload-webhook/`, {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify({ webhook_url: webhookUrl, ...(uploadItems?.length ? { upload_items: uploadItems } : {}) }),
    }),
  listUploadRecords: () => request<UploadRecord[]>('/api/upload-records/'),
  getLlmUsage: () => request<LlmUsageSummary>('/api/llm-usage/me/'),
};

