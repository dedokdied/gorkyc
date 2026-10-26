import { useState } from "react";

interface Props {
  busy: boolean;
  onSearch: (query: string) => void;
}

export function SearchBar({ busy, onSearch }: Props) {
  const [query, setQuery] = useState("");

  return (
    <form
      className="search-bar"
      onSubmit={(event) => {
        event.preventDefault();
        if (query.trim()) {
          onSearch(query.trim());
        }
      }}
    >
      <span className="search-bar__icon" aria-hidden="true">
        ⌕
      </span>
      <input
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Найти задачу, встречу или заметку"
        aria-label="Поисковый запрос"
      />
      <button className="button button--primary" type="submit" disabled={busy || !query.trim()}>
        {busy ? "Ищу…" : "Найти"}
      </button>
    </form>
  );
}
