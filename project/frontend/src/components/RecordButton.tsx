import { useState } from "react";
import { useRecorder } from "../hooks/useRecorder";

interface Props {
  disabled: boolean;
  onRecorded: (audio: Blob) => Promise<void>;
}

export function RecordButton({ disabled, onRecorded }: Props) {
  const { recording, error, start, stop } = useRecorder();
  const [sending, setSending] = useState(false);

  async function toggle() {
    if (recording) {
      const audio = await stop();
      if (audio) {
        setSending(true);
        try {
          await onRecorded(audio);
        } finally {
          setSending(false);
        }
      }
      return;
    }
    await start();
  }

  return (
    <div className="recorder">
      <button
        type="button"
        className={`button ${recording ? "button--danger" : "button--ghost"}`}
        disabled={disabled || sending}
        onClick={() => void toggle()}
      >
        {sending ? "Отправка..." : recording ? "■ Остановить" : "● Голос"}
      </button>
      {recording && <span className="recorder__hint">Идёт запись</span>}
      {error && <span className="form-error">{error}</span>}
    </div>
  );
}
