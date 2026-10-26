import { useEffect, useState } from "react";

type SceneID = "write" | "plan" | "remind";

type Scene = {
  id: SceneID;
  title: string;
  aria: string;
};

const SCENES: Scene[] = [
  {
    id: "write",
    title: "Запись",
    aria: "Робот записывает задачу в блокнот, и над ним загорается идея",
  },
  {
    id: "plan",
    title: "План",
    aria: "Робот раскладывает задачи по дням в календаре и ставит встречу",
  },
  {
    id: "remind",
    title: "Напоминание",
    aria: "Телефон робота получает напоминание, и уведомления разлетаются вокруг",
  },
];

function RobotFigure({ variant }: { variant: SceneID }) {
  return (
    <g className={`robot robot--${variant}`} filter="url(#soft-shadow)">
      <ellipse className="robot-ground" cx="0" cy="122" rx="82" ry="15" />
      <g className="robot-float">
        <line className="antenna-stem" x1="0" y1="-160" x2="0" y2="-184" />
        <circle className="antenna-glow" cx="0" cy="-190" r="19" />
        <circle className="antenna-orb" cx="0" cy="-190" r="7" />

        <rect className="head" x="-68" y="-160" width="136" height="112" rx="38" />
        <rect className="face" x="-51" y="-143" width="102" height="78" rx="25" />
        <ellipse className="head-shine" cx="-26" cy="-135" rx="31" ry="14" />
        <circle className="ear" cx="-68" cy="-104" r="7" />
        <circle className="ear" cx="68" cy="-104" r="7" />

        <g className="eye eye--left">
          <ellipse className="eye-ball" cx="-22" cy="-112" rx="5.4" ry="6.4" />
          <circle className="eye-shine" cx="-20.4" cy="-114.2" r="1.7" />
        </g>
        <g className="eye eye--right">
          <ellipse className="eye-ball" cx="22" cy="-112" rx="5.4" ry="6.4" />
          <circle className="eye-shine" cx="23.6" cy="-114.2" r="1.7" />
        </g>

        <path className="brow" d="M-34 -126 Q-22 -131 -10 -126" />
        <path className="brow" d="M10 -126 Q22 -131 34 -126" />

        <path className="mouth-normal" d="M-15 -83 Q0 -73 15 -83" />
        <ellipse className="mouth-surprised" cx="0" cy="-80" rx="5.6" ry="6.6" />

        <rect className="neck" x="-8" y="-50" width="16" height="20" rx="8" />
        <rect className="body" x="-45" y="-38" width="90" height="94" rx="31" />
        <path className="body-shine" d="M-27 -20 Q0 -31 27 -20" />

        <g className="chest">
          <circle className="chest-ring" cx="0" cy="12" r="16" />
          <circle className="chest-core" cx="0" cy="12" r="6.5" />
          <circle className="chest-glint" cx="-2.4" cy="9.6" r="2" />
        </g>

        <g className="arm-left">
          <path className="limb" d="M-42 -10 Q-73 14 -82 44 Q-85 56 -86 68" />
          <circle className="joint" cx="-42" cy="-10" r="4.2" />
          <circle className="joint" cx="-82" cy="44" r="3.8" />
          <circle className="hand" cx="-87" cy="72" r="7" />
        </g>

        <g className="arm-right">
          {variant === "write" ? (
            <>
              <path className="limb" d="M42 -10 Q78 -2 108 6 Q124 9 132 12" />
              <circle className="joint" cx="42" cy="-10" r="4.2" />
              <circle className="joint" cx="108" cy="6" r="3.8" />
              <circle className="hand" cx="134" cy="14" r="7" />
              <line className="pen" x1="136" y1="16" x2="150" y2="30" />
              <path className="pen-nib" d="M150 30 L154 38 L143 35 Z" />
            </>
          ) : (
            <>
              <path className="limb" d="M42 -10 Q72 2 88 22 Q96 32 99 42" />
              <circle className="joint" cx="42" cy="-10" r="4.2" />
              <circle className="joint" cx="88" cy="22" r="3.8" />
              <circle className="hand" cx="100" cy="46" r="7" />
            </>
          )}
        </g>

        <g className="legs">
          <path className="limb" d="M-23 56 Q-26 84 -27 106" />
          <path className="limb" d="M23 56 Q26 84 27 106" />
          <circle className="joint" cx="-26" cy="84" r="3.6" />
          <circle className="joint" cx="26" cy="84" r="3.6" />
          <path className="foot" d="M-45 108 Q-27 103 -9 108" />
          <path className="foot" d="M9 108 Q27 103 45 108" />
          <path className="foot-shadow" d="M-43 116 Q-26 112 -11 116" />
          <path className="foot-shadow" d="M11 116 Q26 112 43 116" />
        </g>
      </g>
    </g>
  );
}

export function RobotScene() {
  const [index, setIndex] = useState(0);
  const scene = SCENES[index];

  useEffect(() => {
    const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      setIndex(1);
      return;
    }

    const timer = window.setTimeout(() => {
      setIndex((current) => (current + 1) % SCENES.length);
    }, 7200);

    return () => window.clearTimeout(timer);
  }, [index]);

  return (
    <div
      className={`robot-scene robot-scene--${scene.id}`}
      role="group"
      aria-label={`${scene.title}. ${scene.aria}`}
    >
      <svg viewBox="0 0 720 500" aria-hidden="true" focusable="false">
        <defs>
          <linearGradient id="robot-head" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#fffdf8" />
            <stop offset="0.62" stopColor="#f0ece3" />
            <stop offset="1" stopColor="#d5cec0" />
          </linearGradient>
          <linearGradient id="robot-body" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#fbf8f1" />
            <stop offset="0.55" stopColor="#e8e2d6" />
            <stop offset="1" stopColor="#c9c1b1" />
          </linearGradient>
          <linearGradient id="robot-face" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#fffefb" />
            <stop offset="1" stopColor="#f3efe7" />
          </linearGradient>
          <linearGradient id="robot-limb" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#eee9df" />
            <stop offset="1" stopColor="#bdb4a4" />
          </linearGradient>
          <radialGradient id="eye-grad" cx="34%" cy="26%" r="72%">
            <stop offset="0" stopColor="#6f6c66" />
            <stop offset="0.45" stopColor="#262522" />
            <stop offset="1" stopColor="#090909" />
          </radialGradient>
          <radialGradient id="core-grad" cx="35%" cy="30%" r="70%">
            <stop offset="0" stopColor="#fffdf7" />
            <stop offset="0.35" stopColor="#b9b1a2" />
            <stop offset="1" stopColor="#57514a" />
          </radialGradient>
          <linearGradient id="ink-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#2f2d29" />
            <stop offset="1" stopColor="#0e0e0d" />
          </linearGradient>
          <linearGradient id="paper-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#fffdf8" />
            <stop offset="1" stopColor="#e9e4d9" />
          </linearGradient>
          <linearGradient id="desk-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#eae4d8" />
            <stop offset="1" stopColor="#c9c1b2" />
          </linearGradient>
          <linearGradient id="desk-edge" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#b8afa0" />
            <stop offset="1" stopColor="#8d8578" />
          </linearGradient>
          <linearGradient id="screen-grad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#262523" />
            <stop offset="1" stopColor="#0b0b0a" />
          </linearGradient>
          <linearGradient id="device-grad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#f7f3ea" />
            <stop offset="0.5" stopColor="#ddd6c8" />
            <stop offset="1" stopColor="#aaa294" />
          </linearGradient>
          <linearGradient id="card-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#fffefa" />
            <stop offset="1" stopColor="#ece7dd" />
          </linearGradient>
          <radialGradient id="bulb-glow-grad" cx="50%" cy="50%" r="50%">
            <stop offset="0" stopColor="#1c1c1a" stopOpacity="0.18" />
            <stop offset="0.55" stopColor="#1c1c1a" stopOpacity="0.06" />
            <stop offset="1" stopColor="#1c1c1a" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="halo-grad" cx="50%" cy="50%" r="50%">
            <stop offset="0" stopColor="#1c1c1a" stopOpacity="0.075" />
            <stop offset="0.65" stopColor="#1c1c1a" stopOpacity="0.025" />
            <stop offset="1" stopColor="#1c1c1a" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="ground-grad" cx="50%" cy="50%" r="50%">
            <stop offset="0" stopColor="#1c1c1a" stopOpacity="0.22" />
            <stop offset="1" stopColor="#1c1c1a" stopOpacity="0" />
          </radialGradient>
          <filter id="drop-shadow" x="-30%" y="-30%" width="160%" height="180%">
            <feDropShadow dx="0" dy="10" stdDeviation="9" floodColor="#1b1a18" floodOpacity="0.2" />
          </filter>
          <filter id="soft-shadow" x="-25%" y="-25%" width="150%" height="160%">
            <feDropShadow dx="0" dy="4" stdDeviation="4" floodColor="#1b1a18" floodOpacity="0.14" />
          </filter>
          <pattern id="scene-dots" width="26" height="26" patternUnits="userSpaceOnUse">
            <circle className="grid-dot" cx="1.2" cy="1.2" r="1" />
          </pattern>
        </defs>

        <rect className="scene-bg" x="0" y="0" width="720" height="500" fill="url(#scene-dots)" />
        <ellipse className="scene-halo" cx="356" cy="262" rx="300" ry="225" fill="url(#halo-grad)" />

        <g className="ambient">
          <g className="ambient-spark ambient-spark--1" transform="translate(126 158)">
            <line x1="0" y1="-5" x2="0" y2="5" />
            <line x1="-5" y1="0" x2="5" y2="0" />
          </g>
          <g className="ambient-spark ambient-spark--2" transform="translate(612 306)">
            <line x1="0" y1="-4" x2="0" y2="4" />
            <line x1="-4" y1="0" x2="4" y2="0" />
          </g>
          <g className="ambient-spark ambient-spark--3" transform="translate(638 92)">
            <circle cx="0" cy="0" r="2" />
          </g>
        </g>

        {/* scene 1: write */}
        <g className={`scene-stage scene-stage--write ${scene.id === "write" ? "is-active" : ""}`}>
          <ellipse className="stage-ground" cx="356" cy="447" rx="252" ry="30" />
          <g className="desk3d" transform="translate(146 384)" filter="url(#drop-shadow)">
            <rect className="desk-top" x="0" y="0" width="450" height="28" rx="14" />
            <rect className="desk-front" x="10" y="24" width="430" height="17" rx="8" />
            <rect className="desk-leg" x="58" y="38" width="18" height="62" rx="9" />
            <rect className="desk-leg" x="384" y="38" width="18" height="62" rx="9" />
            <rect className="desk-leg-front" x="58" y="52" width="18" height="48" rx="9" />
            <rect className="desk-leg-front" x="384" y="52" width="18" height="48" rx="9" />
          </g>

          <g className="mug3d" transform="translate(196 330)" filter="url(#soft-shadow)">
            <ellipse className="mug-top" cx="22" cy="8" rx="24" ry="8" />
            <path className="mug-body" d="M0 10 H44 V42 Q44 54 34 54 H10 Q0 54 0 42 Z" />
            <path className="mug-handle" d="M44 18 Q64 18 64 31 Q64 44 44 43" />
            <path className="steam steam--1" d="M14 4 Q10 -5 14 -14" />
            <path className="steam steam--2" d="M28 4 Q24 -6 28 -16" />
          </g>

          <g className="notebook3d" transform="translate(424 296) rotate(-6)" filter="url(#drop-shadow)">
            <rect className="nb-back" x="9" y="11" width="170" height="88" rx="10" />
            <rect className="nb-cover" x="0" y="0" width="170" height="88" rx="10" />
            <rect className="nb-page" x="8" y="7" width="154" height="74" rx="6" />
            <line className="nb-spine" x1="25" y1="7" x2="25" y2="81" />
            <line className="note-line note-line--1" x1="37" y1="22" x2="148" y2="22" />
            <line className="note-line note-line--2" x1="37" y1="35" x2="133" y2="35" />
            <line className="note-line note-line--3" x1="37" y1="48" x2="143" y2="48" />
            <line className="note-line note-line--4" x1="37" y1="61" x2="111" y2="61" />
          </g>

          <g transform="translate(300 334)">
            <RobotFigure variant="write" />
          </g>

          <g className="idea3d" transform="translate(300 96)" filter="url(#soft-shadow)">
            <circle className="idea-glow" cx="0" cy="0" r="55" fill="url(#bulb-glow-grad)" />
            <path className="bulb-glass" d="M-14 -4 Q-14 -24 0 -24 Q14 -24 14 -4 Q14 8 6 14 H-6 Q-14 8 -14 -4 Z" />
            <path className="bulb-base" d="M-6 17 V23 H6 V17" />
            <line className="bulb-base" x1="-4" y1="27" x2="4" y2="27" />
            <path className="bulb-filament" d="M-4 5 Q0 -2 4 5" />
            <g className="bulb-rays">
              <line x1="0" y1="-39" x2="0" y2="-47" />
              <line x1="-28" y1="-27" x2="-34" y2="-33" />
              <line x1="28" y1="-27" x2="34" y2="-33" />
              <line x1="-37" y1="0" x2="-46" y2="0" />
              <line x1="37" y1="0" x2="46" y2="0" />
            </g>
          </g>

          <g className="toast toast--saved" transform="translate(492 190)" filter="url(#soft-shadow)">
            <rect className="toast-body" x="0" y="0" width="154" height="58" rx="17" />
            <circle className="toast-icon" cx="29" cy="29" r="12" />
            <path className="toast-check" d="M23 29 L27 34 L36 23" />
            <text className="ui-title" x="49" y="25">Запомнил</text>
            <text className="ui-caption" x="49" y="41">встреча · 15:00</text>
          </g>

          <g className="paper-plane paper-plane--write" transform="translate(400 352)">
            <path className="plane-body" d="M9 0 L-36 14 L-14 20 L-9 42 L5 23 L31 29 Z" />
            <path className="plane-fold" d="M9 0 L-14 20 L5 23" />
            <path className="plane-fold" d="M-14 20 L-9 42" />
            <line className="plane-trail" x1="-50" y1="8" x2="-69" y2="12" />
            <line className="plane-trail" x1="-54" y1="20" x2="-77" y2="25" />
          </g>
        </g>

        {/* scene 2: plan */}
        <g className={`scene-stage scene-stage--plan ${scene.id === "plan" ? "is-active" : ""}`}>
          <ellipse className="stage-ground" cx="370" cy="456" rx="268" ry="31" />
          <g className="platform3d" transform="translate(172 420)" filter="url(#drop-shadow)">
            <rect className="platform-top" x="0" y="0" width="404" height="26" rx="13" />
            <rect className="platform-front" x="12" y="22" width="380" height="16" rx="8" />
          </g>

          <g transform="translate(214 338) scale(0.94)">
            <RobotFigure variant="plan" />
          </g>

          <g className="calendar3d" transform="translate(420 168) rotate(-4)" filter="url(#drop-shadow)">
            <rect className="cal-back cal-back--2" x="18" y="20" width="224" height="200" rx="22" />
            <rect className="cal-back cal-back--1" x="9" y="10" width="224" height="200" rx="22" />
            <rect className="cal-body" x="0" y="0" width="224" height="200" rx="22" />
            <rect className="cal-header" x="0" y="0" width="224" height="46" rx="22" />
            <rect className="cal-header-flat" x="0" y="24" width="224" height="22" />
            <text className="cal-month" x="18" y="29">ОКТЯБРЬ</text>
            <text className="cal-year" x="206" y="29" textAnchor="end">2026</text>

            {[0, 1, 2, 3, 4, 5, 6].map((day) => (
              <text className="cal-day" key={`d-${day}`} x={18 + day * 28} y="65">
                {["П", "В", "С", "Ч", "П", "С", "В"][day]}
              </text>
            ))}

            {Array.from({ length: 21 }, (_, cell) => {
              const col = cell % 7;
              const row = Math.floor(cell / 7);
              const active = cell === 10;
              const filled = [3, 7, 14, 17].includes(cell);
              return (
                <g
                  key={`cell-${cell}`}
                  className={active ? "cal-cell cal-cell--active" : "cal-cell"}
                  style={{ animationDelay: `${120 + cell * 36}ms` }}
                >
                  <rect
                    className={filled ? "cal-tile cal-tile--filled" : "cal-tile"}
                    x={12 + col * 28}
                    y={75 + row * 35}
                    width="24"
                    height="27"
                    rx="8"
                  />
                  <text
                    className={filled || active ? "cal-num cal-num--light" : "cal-num"}
                    x={24 + col * 28}
                    y={93 + row * 35}
                    textAnchor="middle"
                  >
                    {cell + 1}
                  </text>
                  {active && <circle className="cal-ping" cx={24 + col * 28} cy={88 + row * 35} r="18" />}
                </g>
              );
            })}
          </g>

          <g className="clock3d" transform="translate(610 148)" filter="url(#drop-shadow)">
            <circle className="clock-face" cx="0" cy="0" r="42" />
            <circle className="clock-inner" cx="0" cy="0" r="34" />
            <line className="clock-tick" x1="0" y1="-29" x2="0" y2="-24" />
            <line className="clock-tick" x1="0" y1="29" x2="0" y2="24" />
            <line className="clock-tick" x1="-29" y1="0" x2="-24" y2="0" />
            <line className="clock-tick" x1="29" y1="0" x2="24" y2="0" />
            <g className="clock-hands">
              <line className="clock-hand clock-hand--hour" x1="0" y1="0" x2="0" y2="-16" />
              <line className="clock-hand clock-hand--minute" x1="0" y1="0" x2="0" y2="-26" />
            </g>
            <circle className="clock-pin" cx="0" cy="0" r="3.4" />
          </g>

          <g className="meeting-card" transform="translate(362 368)" filter="url(#drop-shadow)">
            <rect className="meeting-body" x="0" y="0" width="214" height="76" rx="20" />
            <rect className="meeting-time" x="14" y="14" width="62" height="48" rx="13" />
            <text className="meeting-time-text" x="45" y="38" textAnchor="middle">15</text>
            <text className="meeting-time-unit" x="45" y="52" textAnchor="middle">:00</text>
            <text className="ui-title" x="90" y="33">Синк с командой</text>
            <text className="ui-caption" x="90" y="51">сегодня · 60 минут</text>
            <circle className="meeting-dot" cx="196" cy="24" r="4" />
          </g>

          <g className="plan-check" transform="translate(652 382)" filter="url(#soft-shadow)">
            <circle className="plan-check-circle" cx="0" cy="0" r="20" />
            <path className="plan-check-mark" d="M-8 0 L-2 7 L9 -7" />
          </g>

          <g className="float-card float-card--plan" transform="translate(550 214)" filter="url(#soft-shadow)">
            <rect className="float-card-body" x="0" y="0" width="112" height="48" rx="14" />
            <line className="float-card-line" x1="16" y1="17" x2="86" y2="17" />
            <line className="float-card-line" x1="16" y1="29" x2="66" y2="29" />
          </g>
        </g>

        {/* scene 3: remind */}
        <g className={`scene-stage scene-stage--remind ${scene.id === "remind" ? "is-active" : ""}`}>
          <ellipse className="stage-ground" cx="364" cy="456" rx="264" ry="31" />
          <g className="platform3d" transform="translate(158 420)" filter="url(#drop-shadow)">
            <rect className="platform-top" x="0" y="0" width="420" height="26" rx="13" />
            <rect className="platform-front" x="12" y="22" width="396" height="16" rx="8" />
          </g>

          <g transform="translate(196 338) scale(0.94)">
            <RobotFigure variant="remind" />
          </g>

          <g className="phone3d" transform="translate(438 132) rotate(6)" filter="url(#drop-shadow)">
            <rect className="phone-body" x="0" y="0" width="196" height="326" rx="38" />
            <rect className="phone-screen" x="9" y="10" width="178" height="306" rx="31" />
            <rect className="phone-notch" x="70" y="18" width="56" height="7" rx="3.5" />
            <rect className="phone-glow" x="20" y="36" width="156" height="252" rx="24" />
            <text className="phone-time" x="98" y="76" textAnchor="middle">09:41</text>
            <text className="phone-date" x="98" y="94" textAnchor="middle">сегодня</text>

            <g className="notif notif--1">
              <rect className="notif-body" x="22" y="116" width="152" height="58" rx="15" />
              <circle className="notif-icon" cx="43" cy="145" r="10" />
              <path className="notif-bell" d="M39 148 Q39 141 43 141 Q47 141 47 148 Z" />
              <line className="notif-bell" x1="38" y1="149" x2="48" y2="149" />
              <text className="notif-title" x="61" y="140">Позвонить Ивану</text>
              <text className="notif-caption" x="61" y="156">через 10 минут</text>
            </g>

            <g className="notif notif--2">
              <rect className="notif-body" x="22" y="184" width="152" height="58" rx="15" />
              <circle className="notif-icon" cx="43" cy="213" r="10" />
              <path className="notif-bell" d="M39 216 Q39 209 43 209 Q47 209 47 216 Z" />
              <line className="notif-bell" x1="38" y1="217" x2="48" y2="217" />
              <text className="notif-title" x="61" y="208">Оплатить подписку</text>
              <text className="notif-caption" x="61" y="224">сегодня · 18:00</text>
            </g>

            <rect className="phone-home" x="72" y="292" width="52" height="5" rx="2.5" />
          </g>

          <g className="bell3d" transform="translate(620 122)" filter="url(#drop-shadow)">
            <circle className="bell-glow" cx="0" cy="0" r="48" />
            <circle className="bell-face" cx="0" cy="0" r="34" />
            <g className="bell-swing">
              <path className="bell-body" d="M-15 10 Q-15 -12 0 -12 Q15 -12 15 10 L19 18 H-19 Z" />
              <line className="bell-clapper" x1="0" y1="20" x2="0" y2="25" />
              <circle className="bell-clapper-dot" cx="0" cy="27" r="2.6" />
            </g>
            <circle className="bell-badge" cx="22" cy="-22" r="11" />
            <text className="bell-badge-text" x="22" y="-18" textAnchor="middle">2</text>
          </g>

          <g className="reminder-cards">
            <g className="reminder-card reminder-card--1" transform="translate(292 116)" filter="url(#soft-shadow)">
              <rect className="reminder-body" x="0" y="0" width="142" height="44" rx="14" />
              <circle className="reminder-dot" cx="18" cy="22" r="4" />
              <line className="reminder-line" x1="31" y1="17" x2="118" y2="17" />
              <line className="reminder-line reminder-line--short" x1="31" y1="29" x2="92" y2="29" />
            </g>
            <g className="reminder-card reminder-card--2" transform="translate(304 176)" filter="url(#soft-shadow)">
              <rect className="reminder-body" x="0" y="0" width="142" height="44" rx="14" />
              <circle className="reminder-dot" cx="18" cy="22" r="4" />
              <line className="reminder-line" x1="31" y1="17" x2="118" y2="17" />
              <line className="reminder-line reminder-line--short" x1="31" y1="29" x2="104" y2="29" />
            </g>
          </g>

          <g className="paper-plane paper-plane--remind" transform="translate(288 300)">
            <path className="plane-body" d="M9 0 L-36 14 L-14 20 L-9 42 L5 23 L31 29 Z" />
            <path className="plane-fold" d="M9 0 L-14 20 L5 23" />
            <path className="plane-fold" d="M-14 20 L-9 42" />
            <line className="plane-trail" x1="-50" y1="8" x2="-69" y2="12" />
            <line className="plane-trail" x1="-54" y1="20" x2="-77" y2="25" />
          </g>

          <g className="float-card float-card--remind" transform="translate(570 366)" filter="url(#soft-shadow)">
            <rect className="float-card-body" x="0" y="0" width="120" height="52" rx="15" />
            <text className="ui-title" x="16" y="23">Не забыть</text>
            <text className="ui-caption" x="16" y="39">через 10 минут</text>
          </g>
        </g>
      </svg>

      <div className="scene-dots" role="group" aria-label="Сцены анимации">
        {SCENES.map((item, itemIndex) => (
          <button
            key={item.id}
            type="button"
            className={itemIndex === index ? "scene-dot scene-dot--active" : "scene-dot"}
            aria-label={`Сцена ${itemIndex + 1}: ${item.title}`}
            aria-pressed={itemIndex === index}
            onClick={() => setIndex(itemIndex)}
          />
        ))}
      </div>
    </div>
  );
}
