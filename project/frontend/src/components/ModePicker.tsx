import type { AssistantMode } from "../store/mode";

interface Props {
  defaultMode: AssistantMode;
  onSelect: (mode: AssistantMode) => void;
}

const OPTIONS: Array<{
  value: AssistantMode;
  index: string;
  title: string;
  caption: string;
  description: string;
}> = [
  {
    value: "text",
    index: "01",
    title: "Текстовый режим",
    caption: "писать сообщения",
    description:
      "Обычный чат. Можно печатать или надиктовать сообщение микрофоном — текст появится в строке ввода.",
  },
  {
    value: "voice",
    index: "02",
    title: "Голосовой режим",
    caption: "позвонить ассистенту",
    description:
      "Звонок без текста и клавиатуры. Вы говорите — ЗапишИИ слушает и отвечает голосом.",
  },
];

export function ModePicker({ defaultMode, onSelect }: Props) {
  return (
    <div className="mode-picker" role="dialog" aria-modal="true" aria-labelledby="mode-title">
      <div className="mode-picker__card">
        <header className="mode-picker__head">
          <p className="kicker">ЗАПИШИИ / РЕЖИМ СВЯЗИ</p>
          <h2 id="mode-title">
            Как вам удобнее
            <br />
            <em>говорить?</em>
          </h2>
          <p>
            Режим можно сменить в любой момент — прямо в чате или во время звонка.
          </p>
        </header>

        <div className="mode-picker__options">
          {OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              className={
                option.value === defaultMode
                  ? "mode-option mode-option--suggested"
                  : "mode-option"
              }
              onClick={() => onSelect(option.value)}
            >
              <span className="mode-option__index">{option.index}</span>
              <span className="mode-option__title">{option.title}</span>
              <span className="mode-option__caption">{option.caption}</span>
              <span className="mode-option__description">{option.description}</span>
              <span className="mode-option__arrow" aria-hidden="true">
                →
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
