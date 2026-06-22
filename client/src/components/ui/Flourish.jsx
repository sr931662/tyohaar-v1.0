/**
 * Flourish — symmetric horizontal divider ornament.
 * A central diamond motif with mirrored floral scrollwork on both sides.
 * Uses currentColor.
 */

const P_SM = 'M 0 0 C -2.5 -3, -3 -8, 0 -11 C 3 -8, 2.5 -3, 0 0';
const P_XS = 'M 0 0 C -1.5 -2, -2 -6, 0 -8 C 2 -6, 1.5 -2, 0 0';

function MiniFlower({ x, y, petal, r, n = 5 }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      {Array.from({ length: n }, (_, i) => (360 / n) * i).map(a => (
        <path key={a} d={petal} transform={`rotate(${a})`} />
      ))}
      <circle r={r} />
    </g>
  );
}

function HalfFlourish() {
  return (
    <g>
      <path d="M 0 0 C 30 -2, 65 -5, 100 -8 Q 135 -11, 165 -13"
            fill="none" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" />
      <path d="M 75 -6 C 80 -12, 84 -18, 87 -23"
            fill="none" stroke="currentColor" strokeWidth="0.9" strokeLinecap="round" />
      <path d="M 165 -13 C 168 -16, 172 -16, 171 -13 C 170 -10, 166 -11, 165 -13"
            fill="none" stroke="currentColor" strokeWidth="0.85" strokeLinecap="round" />
      <MiniFlower x={87}  y={-23} petal={P_SM} r={2.5} n={5} />
      <MiniFlower x={165} y={-13} petal={P_XS} r={1.5} n={5} />
      <g transform="translate(40 -4) rotate(-20)">
        <path d="M 0 0 C 3 -3, 7 -5, 9 -6 C 7 -3, 3 -1, 0 0" />
        <path d="M 0 0 C -3 -3, -7 -5, -9 -6 C -7 -3, -3 -1, 0 0" />
      </g>
      <g transform="translate(120 -11) rotate(-15)">
        <path d="M 0 0 C 2.5 -2.5, 6 -4, 8 -5 C 6 -3, 2.5 -1, 0 0" />
        <path d="M 0 0 C -2.5 -2.5, -6 -4, -8 -5 C -6 -3, -2.5 -1, 0 0" />
      </g>
      <g opacity="0.72">
        <circle cx="22"  cy="-2"  r="1.5" />
        <circle cx="55"  cy="-5"  r="1.3" />
        <circle cx="145" cy="-13" r="1.5" />
      </g>
    </g>
  );
}

export default function Flourish({ width = 380, className = '', style = {} }) {
  return (
    <svg
      viewBox="-185 -36 370 44"
      width={width}
      fill="currentColor"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
      className={className}
      style={style}
    >
      <path d="M 0 -8 L 6 0 L 0 8 L -6 0 Z" />
      <circle cx="0" cy="0" r="2.5" fill="var(--paper, #fff)" />
      <HalfFlourish />
      <g transform="scale(-1 1)"><HalfFlourish /></g>
    </svg>
  );
}
