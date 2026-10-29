import Editor from "@monaco-editor/react";
import { useEffect, useRef, useState } from "react";

import { ApiError, api } from "../api";
import { ErrorBox, Loading, Page } from "../components";
import { useAsync } from "../hooks";

/** Экран 1: условие, редактор кода, ответы на вопросы и отправка решения. */
export default function ScenarioScreen({ scenarioId }: { scenarioId: number }) {
  const scenario = useAsync(() => api.getScenario(scenarioId), [scenarioId]);
  const [attemptId, setAttemptId] = useState<number | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [answers, setAnswers] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const started = useRef<number | null>(null);

  // Прохождение создаётся один раз, когда сценарий загружен.
  useEffect(() => {
    const loaded = scenario.data;
    if (!loaded || started.current === loaded.id) return;
    started.current = loaded.id;
    setCode(loaded.code_template);
    setAnswers(loaded.questions.map(() => ""));
    api
      .startAttempt(loaded.id)
      .then((attempt) => setAttemptId(attempt.id))
      .catch((err: unknown) =>
        setStartError(err instanceof ApiError ? err.message : "Не удалось начать прохождение."),
      );
  }, [scenario.data]);

  async function submit() {
    if (attemptId === null) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await api.submit(attemptId, code, answers);
      window.location.hash = `#/result/${attemptId}`;
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "Не удалось отправить решение.");
      setSubmitting(false);
    }
  }

  if (scenario.loading) return <Loading text="Загружаем задачу…" />;
  if (scenario.error) return <ErrorBox message={scenario.error} onRetry={scenario.reload} />;
  const data = scenario.data;
  if (!data) return null;

  return (
    <Page title={data.title}>
      <section className="panel">
        <h2>Условие</h2>
        <p className="statement">{data.description}</p>
      </section>

      <section className="panel">
        <h2>Ваше решение</h2>
        <Editor
          height="320px"
          language="python"
          theme="vs-dark"
          value={code}
          onChange={(value) => setCode(value ?? "")}
          options={{ minimap: { enabled: false }, fontSize: 14, scrollBeyondLastLine: false }}
          loading={<Loading text="Загружаем редактор…" />}
        />
      </section>

      <section className="panel">
        <h2>Вопросы</h2>
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

      {startError && <ErrorBox message={startError} />}
      {submitError && <ErrorBox message={submitError} />}
      <div className="actions">
        <a className="link" href="#/">
          ← К списку задач
        </a>
        <button
          type="button"
          onClick={submit}
          disabled={submitting || attemptId === null || startError !== null}
        >
          {submitting ? "Проверяем решение…" : "Отправить"}
        </button>
      </div>
    </Page>
  );
}
