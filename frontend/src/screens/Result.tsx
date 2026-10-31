import type { Criteria, Severity } from "../api";
import { api } from "../api";
import { ErrorBox, Loading, Page, toneForCriterion, toneForTotal } from "../components";
import { useAsync } from "../hooks";

const CRITERIA_LABELS: Record<keyof Criteria, string> = {
  correctness: "Правильность",
  code_quality: "Качество кода",
  safety: "Безопасность",
  explanation: "Ясность объяснения",
};

const SEVERITY_LABELS: Record<Severity, string> = {
  low: "низкая",
  medium: "средняя",
  high: "высокая",
};

const VERDICTS = { ok: "Хороший результат", warn: "Есть что улучшить", bad: "Нужно доработать" };

const RING_RADIUS = 76;
const RING_LENGTH = 2 * Math.PI * RING_RADIUS;

/** Экран 2: общий балл, четыре критерия, разбор и замечания с номерами строк. */
export default function Result({ attemptId }: { attemptId: number }) {
  const { data, error, loading, reload } = useAsync(() => api.getAttempt(attemptId), [attemptId]);

  if (loading) return <Loading text="Загружаем результат…" />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!data) return null;
  if (!data.result) {
    return (
      <Page title="Результат">
        <p>Решение ещё не отправлено.</p>
        <a className="link" href={`#/scenario/${data.scenario_id}`}>
          Вернуться к задаче
        </a>
      </Page>
    );
  }

  const { total, criteria, feedback, findings } = data.result;
  const tone = toneForTotal(total);
  const color = `var(--${tone})`;

  return (
    <Page title="Результат" subtitle="Автоматический разбор вашего решения.">
      <section className="panel score">
        <div className="total" aria-label={`Общий балл ${total} из 100`}>
          <svg className="ring" viewBox="0 0 180 180" aria-hidden="true">
            <circle className="track" cx="90" cy="90" r={RING_RADIUS} />
            <circle
              className="value"
              cx="90"
              cy="90"
              r={RING_RADIUS}
              style={{ stroke: color }}
              strokeDasharray={`${(total / 100) * RING_LENGTH} ${RING_LENGTH}`}
            />
          </svg>
          <div className="center">
            <span className="number">{total}</span>
            <span className="of">из 100</span>
          </div>
        </div>
        <div>
          <span className={`verdict tone-${tone}`}>{VERDICTS[tone]}</span>
          <ul className="criteria">
            {(Object.keys(CRITERIA_LABELS) as (keyof Criteria)[]).map((key) => (
              <li key={key}>
                <div className="criterion-head">
                  <span>{CRITERIA_LABELS[key]}</span>
                  <strong>{criteria[key]} / 25</strong>
                </div>
                <div className="bar">
                  <div
                    className={`fill tone-${toneForCriterion(criteria[key])}`}
                    style={{ width: `${(criteria[key] / 25) * 100}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="panel">
        <h2>Разбор</h2>
        <p className="statement">{feedback}</p>
      </section>

      <section className="panel">
        <h2>Замечания к коду</h2>
        {findings.length === 0 ? (
          <p className="empty">Замечаний нет.</p>
        ) : (
          <ul className="findings">
            {findings.map((item, index) => (
              <li key={`${item.code}-${item.line}-${index}`} className={`sev-${item.severity}`}>
                <span className="line">строка {item.line}</span>
                <span className="badge">{SEVERITY_LABELS[item.severity]}</span>
                <span>{item.message}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="actions">
        <a className="link" href="#/">
          ← К списку задач
        </a>
        <a className="link" href="#/manager">
          Панель руководителя
        </a>
      </div>
    </Page>
  );
}
