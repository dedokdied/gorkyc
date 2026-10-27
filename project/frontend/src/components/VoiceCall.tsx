import { useCallback, useEffect, useRef, useState } from "react";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";
import { useSpeechSynthesis } from "../hooks/useSpeechSynthesis";
import { mergeTranscript, normalizeTranscript } from "../lib/transcript";
import type { ChatResponse } from "../types/api";

type Phase = "connecting" | "listening" | "thinking" | "speaking" | "error";

interface Props {
  open: boolean;
  greeting?: string | null;
  onTurn: (text: string) => Promise<ChatResponse | null>;
  onClose: () => void;
}

const BARS = Array.from({ length: 34 }, (_, index) => ({
  height: 16 + Math.round(58 * Math.abs(Math.sin(index * 1.73 + 0.4))),
  delay: (index % 8) * 65,
  duration: 720 + (index % 6) * 110,
}));

function statusFor(phase: Phase): string {
  switch (phase) {
    case "connecting":
      return "Соединяю…";
    case "listening":
      return "Слушаю вас";
    case "thinking":
      return "Думаю…";
    case "speaking":
      return "Горький говорит";
    default:
      return "Связь прервалась";
  }
}

function formatTime(total: number): string {
  const minutes = Math.floor(total / 60)
    .toString()
    .padStart(2, "0");
  const seconds = (total % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}

export function VoiceCall({ open, greeting, onTurn, onClose }: Props) {
  const [phase, setPhase] = useState<Phase>("connecting");
  const [seconds, setSeconds] = useState(0);
  const phaseRef = useRef<Phase>("connecting");
  const activeRef = useRef(false);
  const busyRef = useRef(false);
  const onTurnRef = useRef(onTurn);
  const greetingRef = useRef(greeting);
  const startListeningRef = useRef<() => boolean>(() => false);
  const stopListeningRef = useRef<() => void>(() => {});
  const pendingTextRef = useRef("");
  const sessionBaseRef = useRef("");
  const sessionFinalRef = useRef("");
  const interimTextRef = useRef("");
  const silenceTimerRef = useRef(0);

  const SILENCE_MS = 2000;

  onTurnRef.current = onTurn;
  greetingRef.current = greeting;

  const { speak, cancel } = useSpeechSynthesis();

  const setCallPhase = useCallback((next: Phase) => {
    phaseRef.current = next;
    setPhase(next);
  }, []);

  const botSay = useCallback(
    async (text: string) => {
      if (!activeRef.current) {
        return;
      }
      setCallPhase("speaking");
      await speak(text);
      if (!activeRef.current) {
        return;
      }
      setCallPhase("listening");
      startListeningRef.current();
    },
    [setCallPhase, speak],
  );

  const clearSilenceTimer = useCallback(() => {
    if (silenceTimerRef.current) {
      window.clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = 0;
    }
  }, []);

  // Full text of the current turn: everything from previous recognition
  // sessions plus the final and interim parts of the current one.
  const currentTurnText = useCallback(() => {
    const withFinal = mergeTranscript(
      sessionBaseRef.current,
      sessionFinalRef.current,
    );
    return mergeTranscript(withFinal, interimTextRef.current);
  }, []);

  const commitTurn = useCallback(async () => {
    if (!activeRef.current || busyRef.current) {
      return;
    }
    const text = currentTurnText();
    if (!text) {
      return;
    }

    pendingTextRef.current = "";
    sessionBaseRef.current = "";
    sessionFinalRef.current = "";
    interimTextRef.current = "";
    clearSilenceTimer();
    busyRef.current = true;
    stopListeningRef.current();
    setCallPhase("thinking");
    try {
      const response = await onTurnRef.current(text);
      if (!activeRef.current) {
        return;
      }
      await botSay(response?.reply || "Не удалось связаться. Попробуйте ещё раз.");
    } catch {
      if (activeRef.current) {
        await botSay("Не удалось связаться. Попробуйте ещё раз.");
      }
    } finally {
      busyRef.current = false;
    }
  }, [botSay, clearSilenceTimer, currentTurnText, setCallPhase]);

  const scheduleAnswer = useCallback(
    (delay = SILENCE_MS) => {
      if (!activeRef.current || busyRef.current) {
        return;
      }
      if (!currentTurnText()) {
        return;
      }
      clearSilenceTimer();
      silenceTimerRef.current = window.setTimeout(() => {
        void commitTurn();
      }, delay);
    },
    [clearSilenceTimer, commitTurn, currentTurnText],
  );

  const handleFinal = useCallback(
    (text: string) => {
      if (!activeRef.current || busyRef.current) {
        return;
      }
      const full = normalizeTranscript(text);
      if (!full) {
        return;
      }
      // The hook sends the whole final phrase, not a delta. Replace the
      // current session part instead of appending it again.
      sessionFinalRef.current = full;
      pendingTextRef.current = mergeTranscript(sessionBaseRef.current, full);
      interimTextRef.current = "";
      scheduleAnswer();
    },
    [scheduleAnswer],
  );

  const handleInterim = useCallback(
    (text: string) => {
      if (!activeRef.current || busyRef.current) {
        return;
      }
      interimTextRef.current = normalizeTranscript(text);
      if (currentTurnText()) {
        scheduleAnswer();
      }
    },
    [currentTurnText, scheduleAnswer],
  );

  const restartIfNeeded = useCallback(() => {
    if (!activeRef.current || busyRef.current) {
      return;
    }
    const combined = currentTurnText();
    if (combined) {
      pendingTextRef.current = combined;
      if (!silenceTimerRef.current) {
        scheduleAnswer();
      }
    }
    if (phaseRef.current !== "listening") {
      return;
    }
    window.setTimeout(() => {
      if (
        activeRef.current &&
        !busyRef.current &&
        phaseRef.current === "listening"
      ) {
        startListeningRef.current();
      }
    }, 380);
  }, [currentTurnText, scheduleAnswer]);

  const {
    supported: recognitionSupported,
    listening,
    error: recognitionError,
    start,
    stop,
    abort,
  } = useSpeechRecognition({
    lang: "ru-RU",
    continuous: true,
    onFinal: handleFinal,
    onInterim: handleInterim,
    onEnd: restartIfNeeded,
  });

  const beginListening = useCallback(() => {
    if (!activeRef.current) {
      return false;
    }
    // Everything collected before this recognition session becomes the base
    // for the next one, so a browser-side restart cannot erase the phrase.
    sessionBaseRef.current = pendingTextRef.current;
    sessionFinalRef.current = "";
    interimTextRef.current = "";
    return start();
  }, [start]);

  startListeningRef.current = beginListening;
  stopListeningRef.current = stop;

  useEffect(() => {
    if (!open) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    activeRef.current = true;
    busyRef.current = false;
    pendingTextRef.current = "";
    sessionBaseRef.current = "";
    sessionFinalRef.current = "";
    interimTextRef.current = "";
    clearSilenceTimer();
    setSeconds(0);
    setCallPhase("connecting");

    const timer = window.setInterval(() => {
      setSeconds((value) => value + 1);
    }, 1000);

    const greetingTimer = window.setTimeout(() => {
      void botSay(greetingRef.current || "Слушаю. Чем помочь?");
    }, 520);

    return () => {
      activeRef.current = false;
      busyRef.current = false;
      pendingTextRef.current = "";
      sessionBaseRef.current = "";
      sessionFinalRef.current = "";
      interimTextRef.current = "";
      clearSilenceTimer();
      window.clearInterval(timer);
      window.clearTimeout(greetingTimer);
      document.body.style.overflow = previousOverflow;
      abort();
      cancel();
    };
  }, [abort, botSay, cancel, clearSilenceTimer, open, setCallPhase]);

  useEffect(() => {
    if (!recognitionError) {
      return;
    }
    setCallPhase("error");
  }, [recognitionError, setCallPhase]);

  if (!open) {
    return null;
  }

  const hint = recognitionSupported
    ? "Говорите обычными словами. Когда закончите — сделайте паузу."
    : "Этот браузер не умеет распознавать речь. Можно перейти в текстовый режим.";

  return (
    <div className="call" role="dialog" aria-modal="true" aria-label="Голосовой звонок ассистенту">
      <div className="call__grain" aria-hidden="true" />
      <header className="call__head">
        <span className="call__brand">
          <span className="call__brand-mark" aria-hidden="true" />
          ГОРЬКИЙ / НА ЛИНИИ
        </span>
        <span className="call__secure">
          <span className="status-dot" aria-hidden="true" />
          {listening ? "микрофон включён" : "голосовой канал"}
        </span>
      </header>

      <main className="call__stage">
        <div className={`call__orb call__orb--${phase}`} aria-hidden="true">
          <span className="call__orb-ring call__orb-ring--one" />
          <span className="call__orb-ring call__orb-ring--two" />
          <span className="call__orb-core" />
        </div>

        <p className="call__name">Горький</p>
        <p className="call__status" aria-live="polite">
          {statusFor(phase)}
        </p>

        <div className={`call-wave call-wave--${phase}`} aria-hidden="true">
          {BARS.map((bar, index) => (
            <span
              key={index}
              className="call-wave__bar"
              style={{
                height: `${bar.height}%`,
                animationDelay: `${bar.delay}ms`,
                animationDuration: `${bar.duration}ms`,
              }}
            />
          ))}
        </div>

        <p className="call__timer">{formatTime(seconds)}</p>

        {recognitionError && (
          <p className="call__error" role="alert">
            {recognitionError}
          </p>
        )}
        {!recognitionSupported && (
          <p className="call__error" role="alert">
            Web Speech API недоступен в этом браузере.
          </p>
        )}
      </main>

      <footer className="call__foot">
        <p className="call__hint">{hint}</p>
        <div className="call__controls">
          <button type="button" className="call__end" onClick={onClose}>
            <span className="call__end-icon" aria-hidden="true" />
            Завершить
          </button>
        </div>
      </footer>
    </div>
  );
}
