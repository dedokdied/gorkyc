import { useState } from "react";
import { RobotScene } from "./RobotScene";

type Mode = "login" | "register";

interface Props {
  onLogin: (email: string, password: string) => Promise<void>;
  onRegister: (email: string, password: string, displayName?: string) => Promise<void>;
}

export function AuthScreen({ onLogin, onRegister }: Props) {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function switchMode(nextMode: Mode) {
    setMode(nextMode);
    setError(null);
    setPassword("");
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const normalizedEmail = email.trim();

    if (!normalizedEmail.includes("@") || normalizedEmail.length < 5) {
      setError("Введите корректный email.");
      return;
    }
    if (mode === "register" && password.length < 8) {
      setError("Пароль должен быть не короче 8 символов.");
      return;
    }
    if (!password) {
      setError("Введите пароль.");
      return;
    }

    setBusy(true);
    setError(null);
    try {
      if (mode === "login") {
        await onLogin(normalizedEmail, password);
      } else {
        await onRegister(normalizedEmail, password, displayName);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось выполнить вход.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <header className="auth-head">
        <span className="auth-brand">
          <span className="auth-brand__mark" aria-hidden="true" />
          ЗапишИИ
        </span>
        <span className="auth-head__status">
          <span className="status-dot" aria-hidden="true" />
          online
        </span>
      </header>

      <main className="auth-main">
        <section className="auth-hero">
          <h1>
            Скажи.
            <br />
            <em>Я запомню.</em>
          </h1>
          <p className="auth-hero__lede">Задачи, встречи и напоминания.</p>
          <div className="auth-hero__scene">
            <RobotScene />
          </div>
        </section>

        <section className="auth-panel">
          <div className="auth-card">
            <div className="auth-tabs" role="tablist" aria-label="Вход или регистрация">
              <button
                type="button"
                role="tab"
                aria-selected={mode === "login"}
                className={
                  mode === "login"
                    ? "auth-tabs__item auth-tabs__item--active"
                    : "auth-tabs__item"
                }
                onClick={() => switchMode("login")}
              >
                Вход
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={mode === "register"}
                className={
                  mode === "register"
                    ? "auth-tabs__item auth-tabs__item--active"
                    : "auth-tabs__item"
                }
                onClick={() => switchMode("register")}
              >
                Регистрация
              </button>
            </div>

            <form className="auth-form" onSubmit={(event) => void submit(event)}>
              {mode === "register" && (
                <label>
                  <span>Имя</span>
                  <input
                    name="name"
                    value={displayName}
                    onChange={(event) => setDisplayName(event.target.value)}
                    placeholder="Как к вам обращаться"
                    maxLength={100}
                    autoComplete="name"
                  />
                </label>
              )}
              <label>
                <span>Email</span>
                <input
                  name="email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  autoComplete="email"
                  required
                />
              </label>
              <label>
                <span>Пароль</span>
                <input
                  name="password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder={mode === "register" ? "Минимум 8 символов" : "••••••••"}
                  autoComplete={mode === "register" ? "new-password" : "current-password"}
                  required
                />
              </label>

              {error && (
                <p className="form-error" role="alert">
                  <span aria-hidden="true">!</span> {error}
                </p>
              )}

              <button className="button button--primary button--full" type="submit" disabled={busy}>
                {busy ? "Секунду" : mode === "login" ? "Войти" : "Создать аккаунт"}
                <span aria-hidden="true">→</span>
              </button>
            </form>
          </div>
        </section>
      </main>

      <footer className="auth-foot">
        <span>ЗапишИИ / 2026</span>
        <span>Telegram · Web</span>
      </footer>
    </div>
  );
}
