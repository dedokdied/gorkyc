import { useCallback, useEffect, useRef, useState } from "react";
import { pickRussianVoice, speechSynthesisSupported } from "../lib/speech";

export function useSpeechSynthesis() {
  const supported = typeof window !== "undefined" && speechSynthesisSupported();
  const [speaking, setSpeaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const voiceRef = useRef<SpeechSynthesisVoice | null>(null);
  const finishRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!supported) {
      return;
    }

    const selectVoice = () => {
      voiceRef.current = pickRussianVoice(window.speechSynthesis.getVoices());
    };

    selectVoice();
    window.speechSynthesis.addEventListener("voiceschanged", selectVoice);
    return () => {
      window.speechSynthesis.removeEventListener("voiceschanged", selectVoice);
      window.speechSynthesis.cancel();
      finishRef.current?.();
      finishRef.current = null;
    };
  }, [supported]);

  const cancel = useCallback(() => {
    if (!supported) {
      return;
    }
    window.speechSynthesis.cancel();
    setSpeaking(false);
    finishRef.current?.();
    finishRef.current = null;
  }, [supported]);

  const speak = useCallback(
    (text: string): Promise<void> => {
      const clean = text.trim();
      if (!supported || !clean) {
        return Promise.resolve();
      }

      window.speechSynthesis.cancel();
      finishRef.current?.();

      return new Promise<void>((resolve) => {
        let settled = false;
        let started = false;
        let startGuard = 0;
        const finish = () => {
          if (settled) {
            return;
          }
          settled = true;
          window.clearTimeout(startGuard);
          finishRef.current = null;
          setSpeaking(false);
          resolve();
        };

        const utterance = new SpeechSynthesisUtterance(clean);
        utterance.lang = "ru-RU";
        utterance.rate = 0.98;
        utterance.pitch = 1;
        utterance.volume = 1;
        if (voiceRef.current) {
          utterance.voice = voiceRef.current;
        }
        utterance.onstart = () => {
          started = true;
          window.clearTimeout(startGuard);
          setSpeaking(true);
          setError(null);
        };
        utterance.onend = finish;
        utterance.onerror = (event) => {
          if (event.error !== "interrupted" && event.error !== "canceled") {
            setError("Браузер не смог озвучить ответ.");
          }
          finish();
        };

        startGuard = window.setTimeout(() => {
          if (!started) {
            setError("Браузер не смог запустить озвучку.");
            finish();
          }
        }, 2600);

        finishRef.current = finish;
        setSpeaking(true);
        window.speechSynthesis.speak(utterance);
      });
    },
    [supported],
  );

  return { supported, speaking, error, speak, cancel };
}
