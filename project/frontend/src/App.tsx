import { useCallback, useState } from "react";
import { getDemoUser, setDemoUser } from "./api/client";
import { ChatPage } from "./pages/ChatPage";
import { SearchPage } from "./pages/SearchPage";
import { TimelinePage } from "./pages/TimelinePage";

type Tab = "chat" | "timeline" | "search";

const TABS: Array<{ value: Tab; label: string }> = [
  { value: "chat", label: "Ассистент" },
  { value: "timeline", label: "Таймлайн" },
  { value: "search", label: "Поиск" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("chat");
  const [demoDraft, setDemoDraft] = useState(getDemoUser);
  const [demoUser, setActiveDemoUser] = useState(demoDraft);
  const [refreshKey, setRefreshKey] = useState(0);

  const onEventChanged = useCallback(() => {
    setRefreshKey((value) => value + 1);
  }, []);

  function switchDemoUser(event: React.FormEvent) {
    event.preventDefault();
    const normalized = demoDraft.trim() || "demo";
    setDemoUser(normalized);
    setDemoDraft(normalized);
    setActiveDemoUser(normalized);
    setRefreshKey((value) => value + 1);
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">Telegram MVP + Web</p>
          <h1>Голосовой ассистент</h1>
        </div>
        <form className="demo-switch" onSubmit={switchDemoUser}>
          <label htmlFor="demo-user">Демо-пользователь</label>
          <input
            id="demo-user"
            value={demoDraft}
            onChange={(event) => setDemoDraft(event.target.value)}
            maxLength={100}
          />
          <button className="button button--small button--ghost" type="submit">
            Сменить
          </button>
        </form>
      </header>

      <nav className="nav" aria-label="Разделы">
        {TABS.map((item) => (
          <button
            key={item.value}
            type="button"
            className={`nav__tab ${tab === item.value ? "nav__tab--active" : ""}`}
            onClick={() => setTab(item.value)}
          >
            {item.label}
          </button>
        ))}
        <span className="nav__user">{demoUser}</span>
      </nav>

      <main key={demoUser}>
        {tab === "chat" && <ChatPage onEventChanged={onEventChanged} />}
        {tab === "timeline" && <TimelinePage refreshKey={refreshKey} />}
        {tab === "search" && <SearchPage />}
      </main>
    </div>
  );
}
