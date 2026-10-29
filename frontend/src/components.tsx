import type { ReactNode } from "react";

export function Loading({ text = "Загрузка…" }: { text?: string }) {
  return (
    <div className="state" role="status">
      <span className="spinner" aria-hidden="true" />
      {text}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state error" role="alert">
      <p>{message}</p>
      {onRetry && (
        <button type="button" className="secondary" onClick={onRetry}>
          Повторить
        </button>
      )}
    </div>
  );
}

export function Page({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="page">
      <h1>{title}</h1>
      {children}
    </main>
  );
}
