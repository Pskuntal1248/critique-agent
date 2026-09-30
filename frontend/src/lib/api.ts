/**
 * Typed API client for the Critique FastAPI backend.
 * All calls are browser-side; import only from 'use client' components.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? '';

// ─── Response types ───────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  provider?: string;
}

export interface TaskCreateRequest {
  task: string;
  human_in_loop?: boolean;
}

export interface TaskResponse {
  task_id: string;
  status: string;
  original_task: string;
  human_in_loop: boolean;
  critic_score: number | null;
  revision_count: number;
  total_tokens: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  estimated_cost_usd: number | null;
  model_name: string | null;
  llm_provider: string | null;
  total_duration_ms: number | null;
  final_report: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskSummary {
  task_id: string;
  status: string;
  original_task: string;
  human_in_loop: boolean;
  critic_score: number | null;
  revision_count: number;
  total_tokens: number;
  estimated_cost_usd: number | null;
  total_duration_ms: number | null;
  created_at: string;
}

export interface MetricsResponse {
  period_hours: number;
  runs_total: number;
  runs_successful: number;
  success_rate_pct: number;
  avg_duration_ms: number | null;
  p95_duration_ms: number | null;
  avg_tokens_per_run: number | null;
  avg_revisions: number | null;
  agent_avg_latency_ms: Record<string, number>;
}

export interface AgentEventResponse {
  id: number;
  event_type: string;
  agent_name: string | null;
  data: Record<string, unknown>;
  created_at: string;
}

export interface AgentStepResponse {
  id: number;
  agent_name: string;
  step_number: number;
  status: string;
  output_summary: string | null;
  tokens_used: number;
  duration_ms: number | null;
  error: string | null;
  created_at: string;
}

export interface ApproveRequest {
  decision: 'approve' | 'reject' | 'feedback';
  feedback?: string;
}

export interface CancelResponse {
  task_id: string;
  status: string;
}

// ─── Internal helpers ─────────────────────────────────────────────────────────

function buildHeaders(extra?: Record<string, string>): Record<string, string> {
  const h: Record<string, string> = { 'Content-Type': 'application/json' };
  if (API_KEY) h['X-API-Key'] = API_KEY;
  return { ...h, ...(extra ?? {}) };
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...buildHeaders(),
      ...((init?.headers as Record<string, string>) ?? {}),
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new ApiError(res.status, text);
  }

  return res.json() as Promise<T>;
}

// ─── Public API ───────────────────────────────────────────────────────────────

export const api = {
  health: (): Promise<HealthResponse> => apiFetch<HealthResponse>('/health'),

  metrics: (hours = 24): Promise<MetricsResponse> =>
    apiFetch<MetricsResponse>(`/metrics?hours=${hours}`),

  createTask: (body: TaskCreateRequest): Promise<TaskResponse> =>
    apiFetch<TaskResponse>('/tasks', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  listTasks: (limit = 8): Promise<TaskSummary[]> =>
    apiFetch<TaskSummary[]>(`/tasks?limit=${limit}`),

  getTask: (taskId: string): Promise<TaskResponse> =>
    apiFetch<TaskResponse>(`/tasks/${taskId}`),

  approveTask: (taskId: string, body: ApproveRequest): Promise<unknown> =>
    apiFetch(`/tasks/${taskId}/approve`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  cancelTask: (taskId: string): Promise<CancelResponse> =>
    apiFetch<CancelResponse>(`/tasks/${taskId}/cancel`, { method: 'POST' }),

  getEvents: (taskId: string): Promise<AgentEventResponse[]> =>
    apiFetch<AgentEventResponse[]>(`/tasks/${taskId}/events`),

  getSteps: (taskId: string): Promise<AgentStepResponse[]> =>
    apiFetch<AgentStepResponse[]>(`/tasks/${taskId}/steps`),

  reportJson: (taskId: string): Promise<TaskResponse> =>
    apiFetch<TaskResponse>(`/tasks/${taskId}/report.json`),

  /** Download the Markdown report as a file attachment. */
  downloadReportMd: async (taskId: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/tasks/${taskId}/report.md`, {
      headers: buildHeaders(),
    });
    if (!res.ok) throw new ApiError(res.status, await res.text());
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `critique-${taskId.slice(0, 8)}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },

  /** Download the JSON report as a file attachment. */
  downloadReportJson: async (taskId: string): Promise<void> => {
    const data = await apiFetch<TaskResponse>(`/tasks/${taskId}/report.json`);
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `critique-${taskId.slice(0, 8)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
};

// ─── SSE streaming ────────────────────────────────────────────────────────────

export interface StreamEvent {
  type: string;
  data: Record<string, unknown>;
}

export type StreamHandler = (event: StreamEvent) => void;

const STREAM_EVENT_TYPES = [
  'agent_start',
  'agent_complete',
  'awaiting_approval',
  'task_complete',
  'task_failed',
  'task_cancelled',
] as const;

const FINAL_STREAM_EVENTS = new Set<string>([
  'task_complete',
  'task_failed',
  'task_cancelled',
]);

/**
 * Open an SSE connection to GET /tasks/{id}/stream.
 *
 * Returns a cleanup function — call it on component unmount.
 *
 * The browser's `EventSource` API cannot send custom headers, so when
 * `NEXT_PUBLIC_API_KEY` is set the key is appended as a `?api_key=` query
 * parameter.  The backend's `/stream` endpoint accepts both the header and
 * the query param for exactly this reason.
 */
export function streamTask(
  taskId: string,
  onEvent: StreamHandler,
  onDone: () => void,
): () => void {
  const base = `${API_BASE}/tasks/${taskId}/stream`;
  const url = API_KEY ? `${base}?api_key=${encodeURIComponent(API_KEY)}` : base;
  const es = new EventSource(url);

  const makeHandler =
    (type: string) =>
    (e: MessageEvent<string>) => {
      let parsed: Record<string, unknown> = {};
      try {
        parsed = JSON.parse(e.data) as Record<string, unknown>;
      } catch {
        // non-JSON data — ignore
      }
      onEvent({ type, data: parsed });
      if (FINAL_STREAM_EVENTS.has(type)) {
        es.close();
        onDone();
      }
    };

  for (const eventType of STREAM_EVENT_TYPES) {
    es.addEventListener(eventType, makeHandler(eventType));
  }

  es.onerror = () => {
    es.close();
    onDone();
  };

  return () => es.close();
}
