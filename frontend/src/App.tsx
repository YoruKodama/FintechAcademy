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

  return (
    <>
      <header className="topbar">
        <a href="#/" className="brand">
          AI-тренажёр собеседований
        </a>
        <nav>
          <a href="#/">Задачи</a>
          <a href="#/manager">Панель руководителя</a>
        </nav>
      </header>
      {content}
    </>
  );
}
