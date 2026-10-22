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
      <input
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Найти задачу, встречу или заметку"
        aria-label="Поисковый запрос"
      />
      <button className="button" type="submit" disabled={busy || !query.trim()}>
        {busy ? "Поиск..." : "Найти"}
      </button>
    </form>
  );
}
