import { useState } from "react";

import { api } from "../api";
import { ErrorBox, Loading, Page } from "../components";
import { useAsync } from "../hooks";

const STATUS_LABELS = { started: "в процессе", done: "завершено" } as const;

function formatDate(value: string): string {
  return new Date(value).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
}

/** Экран 3: таблица прохождений с баллами и фильтром по сценарию. */
export default function Manager() {
  const [scenarioId, setScenarioId] = useState<number | undefined>(undefined);
  const scenarios = useAsync(() => api.listScenarios(), []);
  const attempts = useAsync(() => api.listAttempts(scenarioId), [scenarioId]);

  return (
    <Page title="Панель руководителя">
      <div className="toolbar">
        <label>
          Сценарий{" "}
          <select
            value={scenarioId ?? ""}
            onChange={(event) =>
              setScenarioId(event.target.value ? Number(event.target.value) : undefined)
            }
          >
            <option value="">Все сценарии</option>
            {scenarios.data?.map((item) => (
              <option key={item.id} value={item.id}>
                {item.title}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="secondary" onClick={attempts.reload}>
          Обновить
        </button>
      </div>

      {attempts.loading && <Loading />}
      {attempts.error && <ErrorBox message={attempts.error} onRetry={attempts.reload} />}
      {attempts.data && attempts.data.length === 0 && <p>Прохождений пока нет.</p>}
      {attempts.data && attempts.data.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>№</th>
              <th>Сценарий</th>
              <th>Начато</th>
              <th>Статус</th>
              <th>Балл</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {attempts.data.map((row) => (
              <tr key={row.id}>
                <td>{row.id}</td>
                <td>{row.scenario_title}</td>
                <td>{formatDate(row.started_at)}</td>
                <td>{STATUS_LABELS[row.status]}</td>
                <td>{row.total ?? "—"}</td>
                <td>
                  {row.status === "done" && <a href={`#/result/${row.id}`}>Открыть</a>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="actions">
        <a className="link" href="#/">
          ← К списку задач
        </a>
      </div>
    </Page>
  );
}
