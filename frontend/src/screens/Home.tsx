import { api } from "../api";
import { ErrorBox, Loading } from "../components";
import { useAsync } from "../hooks";

const STEPS = [
  { title: "Выберите задачу", text: "Банковская задача на Python: комиссии, карты, выписки." },
  { title: "Напишите решение", text: "Редактор с подсветкой кода и два-три вопроса по теме." },
  { title: "Получите разбор", text: "Замечания по строкам, оценка по четырём критериям и баллы." },
];

/** Главная: описание и список сценариев, отсюда начинается прохождение. */
export default function Home() {
  const { data, error, loading, reload } = useAsync(() => api.listScenarios(), []);

  return (
    <main className="page">
      <section className="hero">
        <h1>Тренажёр технического собеседования</h1>
        <p>
          Решайте задачи из банковской практики и сразу получайте разбор от модели, которая работает локально. Персональные
          данные до неё не доходят.
        </p>
      </section>

      <ol className="steps">
        {STEPS.map((step, index) => (
          <li key={step.title}>
            <span className="n">{index + 1}</span>
            <div>
              <b>{step.title}</b>
              <span className="text">{step.text}</span>
            </div>
          </li>
        ))}
      </ol>

      <h2 className="section-title">Выберите задачу</h2>
      {loading && <Loading />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {data && data.length === 0 && <p className="empty">Сценариев пока нет.</p>}
      {data && (
        <ul className="cards">
          {data.map((item, index) => (
            <li key={item.id}>
              <a className="task-card" href={`#/scenario/${item.id}`}>
                <span className="num">{index + 1}</span>
                <span className="title">{item.title}</span>
                <span className="meta">
                  <span>Python · разбор по 8 правилам</span>
                  <span className="go">Начать →</span>
                </span>
              </a>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
