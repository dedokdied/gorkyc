import { useState } from "react";
import { EventCard } from "../components/EventCard";
import { SearchBar } from "../components/SearchBar";
import { searchEvents } from "../api/search";
import type { SearchHit } from "../types/api";

const EXAMPLES = ["договор", "встреча с командой", "позвонить"];

export function SearchPage() {
  const [results, setResults] = useState<SearchHit[] | null>(null);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(value: string) {
    setQuery(value);
    setBusy(true);
    setError(null);
    try {
      setResults((await searchEvents(value)).items);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Поиск не удался");
      setResults([]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page">
      <header className="page-head">
        <div>
          <p className="kicker">Архив / 03</p>
          <h1>Поиск</h1>
          <p className="hint">Вспомните всё, что уже было — по названию и описанию.</p>
        </div>
        <span className="count-label">
          {results === null ? "—" : String(results.length).padStart(2, "0")}
          <small>найдено</small>
        </span>
      </header>

      <div className="search-panel">
        <SearchBar busy={busy} onSearch={(value) => void handleSearch(value)} />
        <div className="search-examples">
          <span>Попробуйте:</span>
          {EXAMPLES.map((example) => (
            <button
              key={example}
              type="button"
              className="text-link"
              onClick={() => void handleSearch(example)}
            >
              {example}
            </button>
          ))}
        </div>
        {error && <p className="form-error">{error}</p>}
      </div>

      {results === null && (
        <div className="empty-state">
          <p className="empty-state__index">00 / 00</p>
          <h2>Найдите старую запись.</h2>
          <p>Поиск работает по названиям и описаниям событий.</p>
        </div>
      )}
      {results?.length === 0 && (
        <div className="empty-state">
          <p className="empty-state__index">00 / 00</p>
          <h2>Ничего не найдено.</h2>
          <p>Попробуйте сформулировать запрос иначе{query ? `: «${query}»` : "."}</p>
        </div>
      )}

      <div className="event-list">
        {results?.map((hit) => (
          <EventCard
            key={hit.event.id}
            event={hit.event}
            snippet={hit.snippet}
            score={hit.score}
          />
        ))}
      </div>
    </section>
  );
}
