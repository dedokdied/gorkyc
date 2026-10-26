import type { Clarification as ClarificationType } from "../types/api";

interface Props {
  clarification: ClarificationType;
  onPick: (text: string) => void;
}

function examplesFor(clarification: ClarificationType): string[] {
  const missing = new Set(clarification.missing);
  const examples: string[] = [];

  if (missing.has("title")) {
    examples.push("Позвонить маме");
    examples.push("Встреча с Анной");
  }
  if (
    missing.has("due_at") ||
    missing.has("starts_at") ||
    missing.has("time_expression") ||
    missing.has("time")
  ) {
    examples.push("завтра в 15:00");
    examples.push("в пятницу в 10 утра");
  }
  if (missing.has("duration_minutes") || missing.has("duration")) {
    examples.push("на час");
    examples.push("на 30 минут");
  }

  if (examples.length === 0) {
    examples.push("завтра в 15:00", "в пятницу в 10 утра");
  }
  return examples.slice(0, 4);
}

export function Clarification({ clarification, onPick }: Props) {
  const examples = examplesFor(clarification);

  return (
    <section className="clarification" aria-label="Уточнение">
      <p className="clarification__kicker">Уточнение</p>
      <p className="clarification__question">{clarification.question}</p>
      <div className="clarification__examples">
        <span>Можно ответить так:</span>
        {examples.map((example) => (
          <button
            key={example}
            type="button"
            className="clarification__example"
            onClick={() => onPick(example)}
          >
            «{example}»
          </button>
        ))}
      </div>
    </section>
  );
}
