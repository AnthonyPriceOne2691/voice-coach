import type { ReactNode } from "react";

interface Props<T> {
  items: T[] | null;
  error?: string | null;
  empty: string;
  children: (items: T[]) => ReactNode;
}

/**
 * Три состояния списка одним местом: загрузка · пусто · данные (+ баннер ошибки).
 *
 * Заведено не ради красоты: History и Words держали эту лесенку копией, и
 * DRY-гейт поймал её как clone-пару (6 строк, 64 токена). Копия опасна не
 * размером, а тем, что расходится молча — «Loading…» на одной странице и
 * «Загрузка…» на другой замечает только пользователь.
 */
export function ListState<T>({ items, error, empty, children }: Props<T>) {
  return (
    <>
      {error && <div className="error-banner">{error}</div>}
      {items === null ? (
        <p className="muted">Loading…</p>
      ) : items.length === 0 ? (
        <p className="muted">{empty}</p>
      ) : (
        children(items)
      )}
    </>
  );
}
