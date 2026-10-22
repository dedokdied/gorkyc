import { useState } from "react";
import type { Clarification as ClarificationType } from "../types/api";

interface Props {
  clarification: ClarificationType;
  disabled: boolean;
  onAnswer: (text: string) => void;
}

export function Clarification({ clarification, disabled, onAnswer }: Props) {
  const [value, setValue] = useState("");

  function submit(text: string) {
    if (!text.trim() || disabled) {
      return;
    }
    onAnswer(text.trim());
    setValue("");
  }

  return (
    <section className="clarification" aria-label="Уточнение">
      <p>{clarification.question}</p>
      {clarification.options.length > 0 && (
        <div className="clarification__options">
          {clarification.options.map((option) => (
            <button
              key={option}
              type="button"
              className="button button--ghost"
              disabled={disabled}
              onClick={() => submit(option)}
            >
              {option}
            </button>
          ))}
        </div>
      )}
      <form
        className="clarification__form"
        onSubmit={(event) => {
          event.preventDefault();
          submit(value);
        }}
      >
        <input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Ваш ответ"
          disabled={disabled}
        />
        <button className="button" type="submit" disabled={disabled}>
          Ответить
        </button>
      </form>
    </section>
  );
}
