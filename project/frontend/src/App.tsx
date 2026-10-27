import { useCallback, useState } from "react";
import { AuthScreen } from "./components/AuthScreen";
import { ModePicker } from "./components/ModePicker";
import { ReminderBanner } from "./components/ReminderBanner";
import { useAuth } from "./hooks/useAuth";
import { useReminders } from "./hooks/useReminders";
import { ChatPage } from "./pages/ChatPage";
import { ProfilePage } from "./pages/ProfilePage";
import { SearchPage } from "./pages/SearchPage";
import { TimelinePage } from "./pages/TimelinePage";
import {
  getStoredMode,
  setStoredMode,
  type AssistantMode,
} from "./store/mode";
import type { AuthUser } from "./types/auth";

type Tab = "chat" | "timeline" | "search" | "profile";

const TABS: Array<{ value: Tab; label: string; index: string }> = [
  { value: "chat", label: "Ассистент", index: "01" },
  { value: "timeline", label: "Таймлайн", index: "02" },
  { value: "search", label: "Поиск", index: "03" },
  { value: "profile", label: "Профиль", index: "04" },
];

function BootScreen() {
  return (
    <div className="boot-screen">
      <p className="kicker">GORKY / WEB</p>
      <p className="boot-screen__text">Поднимаем связь…</p>
      <span className="boot-screen__line" aria-hidden="true" />
    </div>
  );
}

function Workspace({
  user,
  onLogout,
  onLinkTelegram,
  onUpdateProfile,
}: {
  user: AuthUser;
  onLogout: () => void;
  onLinkTelegram: (code: string) => Promise<AuthUser>;
  onUpdateProfile: (payload: {
    display_name?: string;
    timezone?: string;
  }) => Promise<AuthUser>;
}) {
  const [tab, setTab] = useState<Tab>("chat");
  const [refreshKey, setRefreshKey] = useState(0);
  const [mode, setMode] = useState<AssistantMode>(() => getStoredMode() ?? "text");
  const [pickerOpen, setPickerOpen] = useState(true);
  const { reminders, dismiss } = useReminders();

  const onEventChanged = useCallback(() => {
    setRefreshKey((value) => value + 1);
  }, []);

  const changeMode = useCallback((next: AssistantMode) => {
    setMode(next);
    setStoredMode(next);
  }, []);

  const selectInitialMode = useCallback((next: AssistantMode) => {
    setMode(next);
    setStoredMode(next);
    setPickerOpen(false);
  }, []);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand__mark">■</span>
          <span className="brand__name">ГОРЬКИЙ</span>
          <span className="brand__slash">/</span>
          <span className="brand__role">ассистент</span>
        </div>

        <nav className="main-nav" aria-label="Разделы">
          {TABS.map((item) => (
            <button
              key={item.value}
              type="button"
              className={`main-nav__tab ${tab === item.value ? "main-nav__tab--active" : ""}`}
              onClick={() => setTab(item.value)}
            >
              <span className="main-nav__index">{item.index}</span>
              {item.label}
            </button>
          ))}
        </nav>

        <div className="topbar__account">
          <span className="topbar__user" title={user.email ?? undefined}>
            <span className="status-dot" />
            {user.display_name}
          </span>
          <button className="button button--small button--ghost" type="button" onClick={onLogout}>
            Выйти
          </button>
        </div>
      </header>

      <main className="app-main" key={user.id}>
        <ReminderBanner reminders={reminders} onDismiss={(id) => void dismiss(id)} />
        {tab === "chat" && (
          <ChatPage
            onEventChanged={onEventChanged}
            timezone={user.timezone}
            mode={mode}
            onModeChange={changeMode}
          />
        )}
        {tab === "timeline" && <TimelinePage refreshKey={refreshKey} />}
        {tab === "search" && <SearchPage />}
        {tab === "profile" && (
          <ProfilePage
            user={user}
            onLink={onLinkTelegram}
            onUpdate={onUpdateProfile}
          />
        )}
      </main>

      <footer className="app-footer">
        <span>GORKY CODE / 2026</span>
        <span>Telegram + Web / один backend</span>
        <span>{user.email ?? "web account"}</span>
      </footer>

      {pickerOpen && (
        <ModePicker defaultMode={mode} onSelect={selectInitialMode} />
      )}
    </div>
  );
}

export default function App() {
  const {
    user,
    booting,
    signIn,
    signUp,
    signOut,
    linkTelegram,
    updateProfile,
  } = useAuth();

  if (booting) {
    return <BootScreen />;
  }

  if (!user) {
    return <AuthScreen onLogin={signIn} onRegister={signUp} />;
  }

  return (
    <Workspace
      user={user}
      onLogout={signOut}
      onLinkTelegram={linkTelegram}
      onUpdateProfile={updateProfile}
    />
  );
}
