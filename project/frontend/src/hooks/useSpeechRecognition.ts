import { useCallback, useEffect, useRef, useState } from "react";
import {
  speechRecognitionConstructor,
  type SpeechRecognitionInstance,
} from "../lib/speech";
import { mergeTranscript, normalizeTranscript } from "../lib/transcript";

interface Options {
  lang?: string;
  continuous?: boolean;
  /** Full final transcript of the current recognition session. */
  onFinal?: (text: string) => void;
  /** Unfinalized tail of the current recognition session. */
  onInterim?: (text: string) => void;
  onEnd?: () => void;
}

function messageForError(code: string): string | null {
  switch (code) {
    case "not-allowed":
    case "service-not-allowed":
      return "Браузер не разрешил доступ к микрофону.";
    case "audio-capture":
      return "Микрофон не найден.";
    case "network":
      return "Распознавание речи недоступно без сети.";
    case "no-speech":
    case "aborted":
      return null;
    default:
      return "Не удалось распознать речь.";
  }
}

export function useSpeechRecognition({
  lang = "ru-RU",
  continuous = false,
  onFinal,
  onInterim,
  onEnd,
}: Options = {}) {
  const supported =
    typeof window !== "undefined" && Boolean(speechRecognitionConstructor());
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const onFinalRef = useRef(onFinal);
  const onInterimRef = useRef(onInterim);
  const onEndRef = useRef(onEnd);
  const generationRef = useRef(0);
  const finalTranscriptRef = useRef("");

  onFinalRef.current = onFinal;
  onInterimRef.current = onInterim;
  onEndRef.current = onEnd;

  useEffect(() => {
    return () => {
      generationRef.current += 1;
      recognitionRef.current?.abort();
      recognitionRef.current = null;
    };
  }, []);

  const start = useCallback(() => {
    if (!supported) {
      setError("Этот браузер не поддерживает распознавание речи.");
      return false;
    }
    const Recognition = speechRecognitionConstructor();
    if (!Recognition) {
      setError("Этот браузер не поддерживает распознавание речи.");
      return false;
    }

    // Invalidate every callback of the previous recognizer. Without this an
    // old instance can still fire onresult/onend and send its text twice.
    generationRef.current += 1;
    const generation = generationRef.current;
    const previous = recognitionRef.current;
    recognitionRef.current = null;
    try {
      previous?.abort();
    } catch {
      // The previous recognizer has already stopped.
    }
    finalTranscriptRef.current = "";

    const recognition = new Recognition();
    recognition.lang = lang;
    recognition.continuous = continuous;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      if (generation !== generationRef.current) {
        return;
      }
      setListening(true);
      setError(null);
    };

    recognition.onresult = (event) => {
      if (generation !== generationRef.current) {
        return;
      }

      let combinedFinal = "";
      let interimText = "";

      // Browsers differ: some send separate final fragments, some send a
      // growing cumulative phrase, and some repeat the whole list on every
      // event. Rebuild the full final transcript from scratch each time.
      // Consumers replace their text with this value instead of appending it,
      // so a repeated fragment can never be duplicated.
      for (let index = 0; index < event.results.length; index += 1) {
        const result = event.results[index];
        const text = result?.[0]?.transcript ?? "";
        if (result.isFinal) {
          combinedFinal = mergeTranscript(combinedFinal, text);
        } else if (index >= event.resultIndex) {
          interimText += text;
        }
      }

      const cleanFinal = normalizeTranscript(combinedFinal);
      if (cleanFinal !== finalTranscriptRef.current) {
        finalTranscriptRef.current = cleanFinal;
        if (cleanFinal) {
          onFinalRef.current?.(cleanFinal);
        }
      }

      const cleanInterim = normalizeTranscript(interimText);
      setInterim(cleanInterim);
      onInterimRef.current?.(cleanInterim);
    };

    recognition.onerror = (event) => {
      if (generation !== generationRef.current) {
        return;
      }
      const message = messageForError(event.error);
      setError(message);
      if (message) {
        setListening(false);
      }
    };

    recognition.onend = () => {
      if (generation !== generationRef.current) {
        return;
      }
      recognitionRef.current = null;
      setListening(false);
      setInterim("");
      onInterimRef.current?.("");
      onEndRef.current?.();
    };

    recognitionRef.current = recognition;
    try {
      recognition.start();
      return true;
    } catch {
      if (generation === generationRef.current) {
        recognitionRef.current = null;
        setError("Не удалось запустить микрофон. Попробуйте ещё раз.");
      }
      return false;
    }
  }, [continuous, lang, supported]);

  const stop = useCallback(() => {
    try {
      recognitionRef.current?.stop();
    } catch {
      // The recognizer has already stopped.
    }
  }, []);

  const abort = useCallback(() => {
    generationRef.current += 1;
    const recognition = recognitionRef.current;
    recognitionRef.current = null;
    try {
      recognition?.abort();
    } catch {
      // The recognizer has already stopped.
    }
    setListening(false);
    setInterim("");
  }, []);

  return { supported, listening, interim, error, start, stop, abort };
}
