import { Page } from "./components";
import { useRoute } from "./hooks";
import Home from "./screens/Home";
import Manager from "./screens/Manager";
import Result from "./screens/Result";
import ScenarioScreen from "./screens/ScenarioScreen";

function parseId(value: string | undefined): number | null {
  const id = Number(value);
  return Number.isInteger(id) && id > 0 ? id : null;
}

export default function App() {
  const [section, param] = useRoute();

  let content;
  if (!section) content = <Home />;
  else if (section === "manager") content = <Manager />;
  else if (section === "scenario" && parseId(param) !== null)
    content = <ScenarioScreen key={param} scenarioId={parseId(param)!} />;
  else if (section === "result" && parseId(param) !== null)
    content = <Result key={param} attemptId={parseId(param)!} />;
  else
    content = (
      <Page title="Страница не найдена">
        <a className="link" href="#/">
          На главную
        </a>
      </Page>
    );

  const tasksActive = !section || section === "scenario" || section === "result";
  return (
    <>
      <header className="topbar">
        <a href="#/" className="brand">
          <span className="logo" aria-hidden="true">
            AI
          </span>
          Тренажёр собеседований
        </a>
        <nav>
          <a href="#/" className={tasksActive ? "active" : ""}>
            Задачи
          </a>
          <a href="#/manager" className={section === "manager" ? "active" : ""}>
            Панель руководителя
          </a>
        </nav>
      </header>
      {content}
    </>
  );
}
