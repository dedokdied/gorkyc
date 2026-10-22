import { useState } from "react";
import { EventCard } from "../components/EventCard";
import { SearchBar } from "../components/SearchBar";
import { searchEvents } from "../api/search";
import type { SearchHit } from "../types/api";

export function SearchPage() {
  const [results, setResults] = useState<SearchHit[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(query: string) {
    setBusy(true);
    setError(null);
    try {
      setResults((await searchEvents(query)).items);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Поиск не удался");
      setResults([]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page">
      <header className="page__header">
        <div>
          <h1>Поиск</h1>
          <p className="hint">По названию и описанию событий</p>
        </div>
      </header>

      <SearchBar busy={busy} onSearch={(query) => void handleSearch(query)} />
      {error && <p className="form-error">{error}</p>}

      {results === null && (
        <p className="empty-state">Введите запрос, чтобы найти старые записи.</p>
      )}
      {results?.length === 0 && <p className="empty-state">Ничего не найдено.</p>}

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
