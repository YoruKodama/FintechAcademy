// Клиент API. Типы повторяют openapi.yaml, данные берутся только с сервера.

export type Severity = "low" | "medium" | "high";

export interface ScenarioShort {
  id: number;
  title: string;
}

export interface Scenario extends ScenarioShort {
  description: string;
  code_template: string;
  questions: string[];
}

export interface Finding {
  code: string;
  severity: Severity;
  line: number;
  message: string;
}

export interface Criteria {
  correctness: number;
  code_quality: number;
  safety: number;
  explanation: number;
}

export interface Result {
  total: number;
  criteria: Criteria;
  feedback: string;
  findings: Finding[];
}

export interface Attempt {
  id: number;
  scenario_id: number;
  status: "started" | "done";
  started_at: string;
  finished_at: string | null;
  result: Result | null;
}

export interface AttemptSummary {
  id: number;
  scenario_id: number;
  scenario_title: string;
  status: "started" | "done";
  started_at: string;
  total: number | null;
}

/** Ошибка API: сообщение уже на русском, его можно показывать пользователю. */
export class ApiError extends Error {
  code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new ApiError("network", "Не удалось связаться с сервером. Проверьте соединение.");
  }
  if (!response.ok) {
    let body: { error?: { code?: string; message?: string } } = {};
    try {
      body = await response.json();
    } catch {
      // ответ без тела: используем общее сообщение
    }
    throw new ApiError(
      body.error?.code ?? "http_error",
      body.error?.message ?? "Сервер вернул ошибку. Попробуйте ещё раз.",
    );
  }
  return (await response.json()) as T;
}

export const api = {
  listScenarios: () => request<ScenarioShort[]>("/scenarios"),
  getScenario: (id: number) => request<Scenario>(`/scenarios/${id}`),
  startAttempt: (scenarioId: number) =>
    request<Attempt>("/attempts", {
      method: "POST",
      body: JSON.stringify({ scenario_id: scenarioId }),
    }),
  submit: (attemptId: number, code: string, answers: string[]) =>
    request<Attempt>(`/attempts/${attemptId}/submit`, {
      method: "POST",
      body: JSON.stringify({ code, answers }),
    }),
  getAttempt: (id: number) => request<Attempt>(`/attempts/${id}`),
  listAttempts: (scenarioId?: number) =>
    request<AttemptSummary[]>(scenarioId ? `/attempts?scenario_id=${scenarioId}` : "/attempts"),
};
