import { createPortal } from "react-dom";

interface Props {
  open: boolean;
  onGoToProfile: () => void;
  onLater: () => void;
  onNever: () => void;
}

export function TelegramPrompt({
  open,
  onGoToProfile,
  onLater,
  onNever,
}: Props) {
  if (!open) {
    return null;
  }

  return createPortal(
    <div
      className="telegram-prompt"
      role="dialog"
      aria-modal="true"
      aria-labelledby="telegram-prompt-title"
    >
      <div className="telegram-prompt__card">
        <p className="kicker">Уведомления / Telegram</p>
        <h2 id="telegram-prompt-title">Подключите Telegram</h2>
        <p>
          Напоминания о задачах и встречах приходят в Telegram. Подключите бота
          к аккаунту, чтобы не пропустить важное.
        </p>
        <div className="telegram-prompt__actions">
          <button
            className="button button--primary"
            type="button"
            onClick={onGoToProfile}
          >
            Перейти
          </button>
          <button
            className="button button--ghost"
            type="button"
            onClick={onLater}
          >
            Напомнить позже
          </button>
          <button
            className="telegram-prompt__never"
            type="button"
            onClick={onNever}
          >
            Больше не показывать
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
