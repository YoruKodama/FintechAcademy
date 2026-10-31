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

export function Page({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <main className="page">
      <h1>{title}</h1>
      {subtitle && <p className="subtitle">{subtitle}</p>}
      {children}
    </main>
  );
}

/** Цветовая градация по общему баллу 0-100. */
export function toneForTotal(total: number): "ok" | "warn" | "bad" {
  if (total >= 75) return "ok";
  if (total >= 50) return "warn";
  return "bad";
}

/** Цветовая градация по баллу критерия 0-25. */
export function toneForCriterion(score: number): "ok" | "warn" | "bad" {
  return toneForTotal((score / 25) * 100);
}
