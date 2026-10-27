import { useState } from "react";
import type { AuthUser } from "../types/auth";

const TIMEZONES = [
  "Europe/Moscow",
  "Europe/London",
  "Europe/Berlin",
  "Asia/Almaty",
  "Asia/Tbilisi",
  "Asia/Dubai",
  "America/New_York",
  "UTC",
];

interface Props {
  user: AuthUser;
  onLink: (code: string) => Promise<AuthUser>;
  onUpdate: (payload: {
    display_name?: string;
    timezone?: string;
  }) => Promise<AuthUser>;
}

export function ProfilePage({ user, onLink, onUpdate }: Props) {
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [displayName, setDisplayName] = useState(user.display_name);
  const [timezone, setTimezone] = useState(user.timezone);
  const [profileBusy, setProfileBusy] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileSaved, setProfileSaved] = useState(false);

  async function saveProfile(event: React.FormEvent) {
    event.preventDefault();
    if (!displayName.trim() || profileBusy) {
      setProfileError("Имя не может быть пустым.");
      return;
    }
    setProfileBusy(true);
    setProfileError(null);
    setProfileSaved(false);
    try {
      await onUpdate({ display_name: displayName.trim(), timezone });
      setProfileSaved(true);
    } catch (cause) {
      setProfileError(
        cause instanceof Error ? cause.message : "Не удалось сохранить профиль.",
      );
    } finally {
      setProfileBusy(false);
    }
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!/^\d{5}$/.test(code) || busy) {
      setError("Введите код из 5 цифр.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await onLink(code);
      setCode("");
      setSuccess(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось подключить Telegram.");
    } finally {
      setBusy(false);
    }
  }

  const created = new Date(user.created_at).toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });

  return (
    <section className="page page--profile">
      <header className="page-head">
        <div>
          <p className="kicker">Аккаунт / 04</p>
          <h1>Профиль</h1>
          <p className="hint">Настройки аккаунта и подключение уведомлений.</p>
        </div>
      </header>

      <div className="profile-grid">
        <article className="profile-card">
          <p className="profile-card__label">Сайт</p>
          <dl className="profile-facts">
            <div>
              <dt>Имя</dt>
              <dd>{user.display_name}</dd>
            </div>
            <div>
              <dt>Email</dt>
              <dd>{user.email ?? "—"}</dd>
            </div>
            <div>
              <dt>С нами с</dt>
              <dd>{created}</dd>
            </div>
          </dl>
        </article>

        <article className="profile-card">
          <p className="profile-card__label">Настройки</p>
          <form className="profile-settings" onSubmit={(event) => void saveProfile(event)}>
            <label>
              Имя
              <input
                value={displayName}
                onChange={(event) => {
                  setDisplayName(event.target.value);
                  setProfileError(null);
                  setProfileSaved(false);
                }}
                maxLength={100}
                required
              />
            </label>
            <label>
              Часовой пояс
              <select
                value={timezone}
                onChange={(event) => {
                  setTimezone(event.target.value);
                  setProfileSaved(false);
                }}
              >
                {TIMEZONES.map((zone) => (
                  <option key={zone} value={zone}>
                    {zone}
                  </option>
                ))}
              </select>
            </label>
            <p className="hint">
              В этой таймзоне ассистент понимает «завтра» и «в 10:00» в чате.
            </p>
            {profileSaved && <p className="profile-success">Сохранено.</p>}
            {profileError && <p className="form-error">{profileError}</p>}
            <button className="button button--primary" type="submit" disabled={profileBusy}>
              {profileBusy ? "Сохраняю" : "Сохранить"}
            </button>
          </form>
        </article>

        <article
          className="profile-card profile-card--telegram"
          id="telegram-card"
        >
          <p className="profile-card__label">Telegram · уведомления</p>

          {user.telegram_linked ? (
            <>
              <p className="profile-status">
                <span className="status-dot" aria-hidden="true" />
                Уведомления включены
                {user.telegram_username ? ` · @${user.telegram_username}` : ""}
              </p>
              <p className="hint">
                Напоминания о задачах и встречах приходят в Telegram. События
                на сайте и в боте — один общий список.
              </p>
            </>
          ) : (
            <>
              <p className="profile-notice">
                <strong>Уведомления приходят в Telegram.</strong> Подключите
                бота к аккаунту, иначе напоминания не будут приходить в
                Telegram.
              </p>
              <p className="hint">
                Откройте бота в Telegram и отправьте <code>/link</code>. Он пришлёт
                код из 5 цифр — введите его здесь.
              </p>
              <form className="profile-link" onSubmit={(event) => void submit(event)}>
                <input
                  value={code}
                  onChange={(event) => {
                    setCode(event.target.value.replace(/\D/g, "").slice(0, 5));
                    setError(null);
                  }}
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  placeholder="00000"
                  maxLength={5}
                  aria-label="Код из Telegram"
                />
                <button
                  className="button button--primary"
                  type="submit"
                  disabled={busy || code.length !== 5}
                >
                  {busy ? "Проверяю" : "Подключить"}
                </button>
              </form>
              {success && <p className="profile-success">Telegram подключён.</p>}
              {error && <p className="form-error">{error}</p>}
            </>
          )}
        </article>
      </div>
    </section>
  );
}
