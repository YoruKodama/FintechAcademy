import { api } from "../api";
import { ErrorBox, Loading, Page } from "../components";
import { useAsync } from "../hooks";

/** Список сценариев: отсюда начинается прохождение. */
export default function Home() {
  const { data, error, loading, reload } = useAsync(() => api.listScenarios(), []);

  return (
    <Page title="Выберите задачу">
      {loading && <Loading />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {data && data.length === 0 && <p>Сценариев пока нет.</p>}
      {data && (
        <ul className="cards">
          {data.map((item) => (
            <li key={item.id}>
              <a className="card" href={`#/scenario/${item.id}`}>
                {item.title}
              </a>
            </li>
          ))}
        </ul>
      )}
    </Page>
  );
}
