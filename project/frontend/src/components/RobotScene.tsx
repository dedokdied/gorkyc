import { useEffect, useState } from "react";

type Phase = "write" | "surprise" | "idea" | "remember" | "throw";

const TIMELINE: Array<[Phase, number]> = [
  ["write", 3200],
  ["surprise", 1600],
  ["idea", 1800],
  ["remember", 1800],
  ["throw", 1800],
];

export function RobotScene() {
  const [phase, setPhase] = useState<Phase>("write");

  useEffect(() => {
    const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      setPhase("remember");
      return;
    }

    let index = 0;
    let timer = 0;

    const tick = () => {
      const [nextPhase, duration] = TIMELINE[index];
      setPhase(nextPhase);
      index = (index + 1) % TIMELINE.length;
      timer = window.setTimeout(tick, duration);
    };

    tick();
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <div
      className={`robot-scene robot-scene--${phase}`}
      role="img"
      aria-label="Робот записывает мысль в блокнот, находит идею и отправляет письмо"
    >
      <svg viewBox="0 0 560 380" aria-hidden="true" focusable="false">
        {/* desk */}
        <g className="desk">
          <line x1="64" y1="300" x2="486" y2="300" />
          <line x1="98" y1="300" x2="98" y2="360" />
          <line x1="452" y1="300" x2="452" y2="360" />
        </g>

        {/* robot */}
        <g className="robot">
          <line x1="253" y1="120" x2="253" y2="101" />
          <circle cx="253" cy="95" r="5" />

          <rect x="205" y="120" width="96" height="84" rx="22" />
          <circle className="eye" cx="234" cy="160" r="3.5" />
          <circle className="eye" cx="272" cy="160" r="3.5" />

          <path className="mouth-normal" d="M240 183 Q253 190 266 183" />
          <circle className="mouth-surprised" cx="253" cy="184" r="5.5" />

          <line x1="253" y1="204" x2="253" y2="214" />
          <rect x="222" y="208" width="62" height="80" rx="14" />
          <circle className="chest" cx="253" cy="240" r="3" />

          <path className="arm-left" d="M222 224 C206 234 198 250 194 269" />
          <circle className="hand-left" cx="194" cy="274" r="6" />

          <path className="leg" d="M238 288 V340" />
          <path className="leg" d="M268 288 V340" />
          <path className="foot" d="M228 340 H244" />
          <path className="foot" d="M262 340 H278" />
        </g>

        {/* notebook */}
        <g className="notebook" transform="translate(300 246) rotate(-6)">
          <rect x="0" y="0" width="100" height="54" />
          <line x1="50" y1="4" x2="50" y2="50" />
          <line className="note-line note-line--1" x1="10" y1="16" x2="42" y2="16" />
          <line className="note-line note-line--2" x1="10" y1="26" x2="42" y2="26" />
          <line className="note-line note-line--3" x1="10" y1="36" x2="42" y2="36" />
          <line className="note-line note-line--4" x1="58" y1="16" x2="90" y2="16" />
          <line className="note-line note-line--5" x1="58" y1="26" x2="90" y2="26" />
        </g>

        {/* writing arm, above the notebook */}
        <g className="arm-right">
          <path d="M284 224 C300 234 310 248 320 259" />
          <circle className="hand-right" cx="322" cy="261" r="6" />
        </g>

        {/* idea */}
        <g className="bulb">
          <circle cx="253" cy="52" r="14" />
          <path d="M246 66 V71 H260 V66" />
          <path d="M248 77 H258" />
          <line x1="253" y1="24" x2="253" y2="14" />
          <line x1="275" y1="34" x2="283" y2="26" />
          <line x1="287" y1="52" x2="297" y2="52" />
          <line x1="231" y1="34" x2="223" y2="26" />
          <line x1="219" y1="52" x2="209" y2="52" />
        </g>

        {/* surprise mark */}
        <g className="bang">
          <line x1="334" y1="120" x2="334" y2="143" />
          <circle cx="334" cy="151" r="3" />
        </g>

        {/* remembering */}
        <g className="thought">
          <circle cx="316" cy="116" r="5" />
          <circle cx="330" cy="106" r="3" />
          <ellipse cx="366" cy="86" rx="40" ry="25" />
          <circle className="thought-dot" cx="350" cy="86" r="3" />
          <circle className="thought-dot" cx="366" cy="86" r="3" />
          <circle className="thought-dot" cx="382" cy="86" r="3" />
        </g>

        {/* flying letter */}
        <g transform="translate(322 256)">
          <g className="letter">
            <rect x="-14" y="-10" width="28" height="20" />
            <path d="M-14 -10 L0 2 L14 -10" />
            <line x1="-26" y1="0" x2="-19" y2="0" />
            <line x1="-30" y1="6" x2="-22" y2="6" />
          </g>
        </g>
      </svg>
    </div>
  );
}
