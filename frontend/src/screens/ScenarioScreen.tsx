import Editor from "@monaco-editor/react";
import { useEffect, useRef, useState } from "react";

import { ApiError, api } from "../api";
import { ErrorBox, Loading, Page } from "../components";
import { useAsync } from "../hooks";

/** Экран 1: условие, редактор кода, ответы на вопросы и отправка решения. */
export default function ScenarioScreen({ scenarioId }: { scenarioId: number }) {
  const scenario = useAsync(() => api.getScenario(scenarioId), [scenarioId]);
  const [code, setCode] = useState("");
  const [answers, setAnswers] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const initialized = useRef<number | null>(null);

  // Шаблон кода и пустые ответы подставляются один раз, когда сценарий загружен.
  useEffect(() => {
    const loaded = scenario.data;
    if (!loaded || initialized.current === loaded.id) return;
    initialized.current = loaded.id;
    setCode(loaded.code_template);
    setAnswers(loaded.questions.map(() => ""));
  }, [scenario.data]);

  // Прохождение создаётся только при отправке: открытая страница не засоряет панель руководителя.
  async function submit() {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const attempt = await api.startAttempt(scenarioId);
      await api.submit(attempt.id, code, answers);
      window.location.hash = `#/result/${attempt.id}`;
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "Не удалось отправить решение.");
      setSubmitting(false);
    }
  }

  if (scenario.loading) return <Loading text="Загружаем задачу…" />;
  if (scenario.error) return <ErrorBox message={scenario.error} onRetry={scenario.reload} />;
  const data = scenario.data;
  if (!data) return null;

  const filled = answers.filter((answer) => answer.trim()).length;

  return (
    <Page title={data.title} subtitle="Напишите решение, ответьте на вопросы и отправьте на проверку.">
      <div className="task-layout">
        <aside>
          <section className="panel">
            <h2>Условие</h2>
            <p className="statement">{data.description}</p>
            <p className="tip">
              Проверка идёт по 8 правилам (деньги в float, голый except, eval и другие), затем разбор пишет модель.
            </p>
          </section>
        </aside>

        <div>
          <section className="panel">
            <h2>Ваше решение</h2>
            <div className="editor-frame">
              <Editor
                height="340px"
                language="python"
                theme="vs-dark"
                value={code}
                onChange={(value) => setCode(value ?? "")}
                options={{ minimap: { enabled: false }, fontSize: 14, scrollBeyondLastLine: false }}
                loading={<Loading text="Загружаем редактор…" />}
              />
            </div>
          </section>

          <section className="panel">
            <h2>
              Вопросы
              <span className="answers-progress">
                отвечено {filled} из {data.questions.length}
              </span>
            </h2>
            {data.questions.map((question, index) => (
              <label key={question} className="field">
                <span>
                  {index + 1}. {question}
                </span>
                <textarea
                  rows={3}
                  value={answers[index] ?? ""}
                  onChange={(event) =>
                    setAnswers((current) =>
                      current.map((value, i) => (i === index ? event.target.value : value)),
                    )
                  }
                />
              </label>
            ))}
          </section>

          {submitError && <ErrorBox message={submitError} />}
          <div className="actions">
            <a className="link" href="#/">
              ← К списку задач
            </a>
            <button type="button" onClick={submit} disabled={submitting}>
              {submitting ? "Проверяем решение…" : "Отправить"}
            </button>
          </div>
        </div>
      </div>
    </Page>
  );
}
