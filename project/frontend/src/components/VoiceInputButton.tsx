import { useEffect, useRef } from "react";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";
import { joinTranscript } from "../lib/transcript";

interface Props {
  disabled: boolean;
  value: string;
  onChange: (text: string) => void;
}

export function VoiceInputButton({ disabled, value, onChange }: Props) {
  const baseTextRef = useRef("");
  const { supported, listening, interim, error, start, stop } =
    useSpeechRecognition({
      lang: "ru-RU",
      continuous: false,
      // The hook reports the whole phrase for this dictation session, so the
      // field is replaced rather than appended. Repeated fragments from the
      // browser cannot pile up as "создай создай событие".
      onFinal: (text) => onChange(joinTranscript(baseTextRef.current, text)),
    });

  useEffect(() => {
    if (disabled && listening) {
      stop();
    }
  }, [disabled, listening, stop]);

  function toggle() {
    if (listening) {
      stop();
      return;
    }
    baseTextRef.current = value;
    start();
  }

  if (!supported) {
    return (
      <span
        className="mic-button mic-button--unsupported"
        title="Браузер не поддерживает Web Speech API"
      >
        ● Голос
      </span>
    );
  }

  return (
    <div className={`mic ${listening ? "mic--listening" : ""}`}>
      <button
        type="button"
        className={`button ${listening ? "button--danger" : "button--ghost"} mic-button`}
        disabled={disabled}
        aria-pressed={listening}
        aria-label={listening ? "Остановить голосовой ввод" : "Надиктовать сообщение"}
        onClick={toggle}
      >
        <span className="mic-button__dot" aria-hidden="true" />
        {listening ? "Стоп" : "Голос"}
      </button>
      {listening && (
        <span className="mic__hint" aria-live="polite">
          {interim || "Слушаю…"}
        </span>
      )}
      {error && <span className="form-error mic__error">{error}</span>}
    </div>
  );
}
