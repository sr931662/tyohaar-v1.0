// TY.jsx — all window.TY primitives as a proper ES module.
// Consumed only by Screens.jsx. Keep raw inline styles; this is app-demo code.
import React from 'react';
import { occasions as OCCASIONS_DATA } from '../data/occasions.js';
import EmblemComponent from '../components/ui/Emblem.jsx';

/* ─── data ─── */
export const OCCASIONS = OCCASIONS_DATA;

export const VIBES = [
  'Intimate', 'Traditional', 'Grand', 'Elegant',
  'Colorful', 'Relaxed', 'Festive', 'Modern',
];

export const VENDORS = [
  { id: 'v5', cat: 'Venue',       name: 'The Courtyard',  note: 'Heritage open-air',      rating: 4.7, price: 3, from: '₹2.2L',          est: 220000, tint: 'leaf'    },
  { id: 'v1', cat: 'Catering',    name: 'Saffron Table',  note: 'Live thali counters',    rating: 4.9, price: 3, from: '₹1,250 / plate',  est: 90000,  tint: 'saffron' },
  { id: 'v2', cat: 'Décor',       name: 'Marigold & Co.', note: 'Floral & light design',  rating: 4.8, price: 2, from: '₹85,000',         est: 85000,  tint: 'gold'    },
  { id: 'v3', cat: 'Photography', name: 'Frame Stories',  note: 'Candid + cinematic',     rating: 4.9, price: 3, from: '₹1.4L',           est: 140000, tint: 'rose'    },
  { id: 'v4', cat: 'Music',       name: 'Dhol & Disco',   note: 'Live dhol + DJ',         rating: 4.7, price: 2, from: '₹65,000',         est: 65000,  tint: 'leaf'    },
  { id: 'v6', cat: 'Mehendi',     name: 'Henna by Roohi', note: 'Bridal & guest art',     rating: 5.0, price: 1, from: '₹18,000',         est: 18000,  tint: 'rose'    },
];

export const PLAN_TEMPLATE = [
  {
    phase: '4 weeks out',
    items: [
      { t: 'Confirm guest list & headcount',    who: 'Host',           done: true  },
      { t: 'Book venue and confirm capacity',   who: 'Tyohaar',        done: true  },
      { t: 'Send digital invitations',          who: 'Tyohaar',        done: false },
    ],
  },
  {
    phase: '2 weeks out',
    items: [
      { t: 'Finalise catering menu with chef',  who: 'Tyohaar',        done: false },
      { t: 'Confirm décor theme and colours',   who: 'Host + Tyohaar', done: false },
      { t: 'Chase pending RSVPs',               who: 'Host',           done: false },
    ],
  },
  {
    phase: 'Day before',
    items: [
      { t: 'Décor setup and delivery',          who: 'Tyohaar',        done: false },
      { t: 'Catering team briefing',            who: 'Tyohaar',        done: false },
    ],
  },
  {
    phase: 'Celebration day',
    items: [
      { t: 'Welcome guests',                    who: 'Host',           done: false },
      { t: 'Photography session begins',        who: 'Tyohaar',        done: false },
      { t: 'Dinner, music & celebration',       who: 'Everyone',       done: false },
    ],
  },
];

export const SEED_GUESTS = [
  { n: 'The Kapoors',     c: 4, rsvp: 'yes'     },
  { n: 'Meera & Raj',    c: 2, rsvp: 'yes'     },
  { n: 'Sharma Family',  c: 5, rsvp: 'yes'     },
  { n: 'Nandan & Priya', c: 3, rsvp: 'maybe'   },
  { n: 'Auntie Sheila',  c: 1, rsvp: 'yes'     },
  { n: 'The Mehtas',     c: 4, rsvp: 'pending'  },
  { n: 'Rohan & Aisha',  c: 2, rsvp: 'pending'  },
];

/* ─── color map ─── */
export const TINTS = {
  saffron: ['var(--saffron)', '#E68A2E'],
  rose:    ['var(--rose)',    '#C8456B'],
  leaf:    ['var(--leaf)',    '#5E8C5A'],
  gold:    ['var(--gold)',    '#C99A3B'],
};

/* ─── utils ─── */
export const priceStr = (n) => '₹'.repeat(n) + '·'.repeat(3 - n);
export const stars    = (r) => r.toFixed(1);

/* ─── Icon ─── */
export function Icon({ name, size = 20, sw = 1.7 }) {
  const s = 'currentColor';
  const paths = {
    home:    <path d="M3 12L12 4l9 8v9h-6v-5H9v5H3v-9z" stroke={s} strokeWidth={sw} fill="none" strokeLinejoin="round" strokeLinecap="round"/>,
    plan:    <><rect x="5" y="3" width="14" height="18" rx="2" stroke={s} strokeWidth={sw} fill="none"/><path d="M9 7h6M9 11h6M9 15h4" stroke={s} strokeWidth={sw} strokeLinecap="round"/></>,
    vendors: <><path d="M3 9h18l-1.5 9H4.5L3 9z" stroke={s} strokeWidth={sw} fill="none" strokeLinejoin="round"/><path d="M8 9V6a4 4 0 018 0v3" stroke={s} strokeWidth={sw} fill="none" strokeLinecap="round"/></>,
    heart:   <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z" stroke={s} strokeWidth={sw} fill="none" strokeLinejoin="round" strokeLinecap="round"/>,
    bell:    <><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9z" stroke={s} strokeWidth={sw} fill="none" strokeLinejoin="round"/><path d="M13.73 21a2 2 0 01-3.46 0" stroke={s} strokeWidth={sw} strokeLinecap="round"/></>,
    chevR:   <path d="M9 18l6-6-6-6" stroke={s} strokeWidth={sw} fill="none" strokeLinecap="round" strokeLinejoin="round"/>,
    chevL:   <path d="M15 18l-6-6 6-6" stroke={s} strokeWidth={sw} fill="none" strokeLinecap="round" strokeLinejoin="round"/>,
    close:   <path d="M18 6L6 18M6 6l12 12" stroke={s} strokeWidth={sw} fill="none" strokeLinecap="round"/>,
    plus:    <path d="M12 5v14M5 12h14" stroke={s} strokeWidth={sw} fill="none" strokeLinecap="round"/>,
    cal:     <><rect x="3" y="4" width="18" height="18" rx="2" stroke={s} strokeWidth={sw} fill="none"/><path d="M16 2v4M8 2v4M3 10h18" stroke={s} strokeWidth={sw} strokeLinecap="round"/></>,
    pin:     <><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z" stroke={s} strokeWidth={sw} fill="none" strokeLinejoin="round"/><circle cx="12" cy="10" r="3" stroke={s} strokeWidth={sw} fill="none"/></>,
    spark:   <><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" stroke={s} strokeWidth={sw} strokeLinecap="round"/><path d="M12 8l1.5 3.5L17 12l-3.5 1.5L12 17l-1.5-3.5L7 12l3.5-1.5L12 8z" stroke={s} strokeWidth={sw} fill="none" strokeLinejoin="round"/></>,
    star:    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" stroke={s} strokeWidth={sw} fill="none" strokeLinejoin="round"/>,
    check:   <path d="M20 6L9 17l-5-5" stroke={s} strokeWidth={sw} fill="none" strokeLinecap="round" strokeLinejoin="round"/>,
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" style={{ display: 'block', flexShrink: 0 }}>
      {paths[name] || null}
    </svg>
  );
}

/* ─── Photo (image placeholder with tint gradient) ─── */
export function Photo({ label = '', tint = 'saffron', h = 200, arch = true }) {
  return (
    <div style={{
      width: '100%', height: h, overflow: 'hidden', position: 'relative',
      borderRadius: arch ? '999px 999px var(--r-lg) var(--r-lg)' : 'var(--r-lg)',
      background: `linear-gradient(150deg, color-mix(in srgb, var(--${tint}) 26%, var(--surface)) 0%, color-mix(in srgb, var(--${tint}) 9%, var(--surface)) 100%)`,
    }}>
      <div style={{
        position: 'absolute', top: '36%', left: '50%', width: '34%', aspectRatio: '1',
        transform: 'translate(-50%, -50%)', borderRadius: '50%',
        background: `color-mix(in srgb, var(--${tint}) 30%, transparent)`,
      }} />
      {label && (
        <span style={{
          position: 'absolute', left: 10, bottom: 10,
          fontFamily: 'ui-monospace, "SF Mono", Menlo, monospace',
          fontSize: 10, letterSpacing: '0.04em', color: 'var(--ink-2)',
          background: 'color-mix(in srgb, var(--surface) 72%, transparent)',
          backdropFilter: 'blur(4px)', padding: '3px 8px', borderRadius: 6,
        }}>{label}</span>
      )}
    </div>
  );
}

/* ─── Emblem — re-export the existing component ─── */
export const Emblem = EmblemComponent;

/* ─── Ring (circular progress) ─── */
export function Ring({ pct = 0, size = 44, sw = 4, children }) {
  const r = (size - sw) / 2;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  return (
    <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}
        style={{ display: 'block', transform: 'rotate(-90deg)' }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--line)" strokeWidth={sw} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--saffron)" strokeWidth={sw}
          strokeDasharray={`${dash} ${circ}`} strokeLinecap="round" />
      </svg>
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: 'var(--font-sans)', fontSize: size * 0.28, fontWeight: 700, color: 'var(--ink)',
      }}>{children}</div>
    </div>
  );
}

/* ─── Avatar ─── */
const AV_COLORS = ['var(--saffron)', 'var(--rose)', 'var(--leaf)', 'var(--gold)'];
export function Avatar({ name = '', i = 0, size = 40 }) {
  const bg = AV_COLORS[i % AV_COLORS.length];
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%', flexShrink: 0,
      background: `color-mix(in srgb, ${bg} 22%, var(--surface))`,
      border: '2px solid var(--surface)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: size * 0.38, fontWeight: 800, color: bg,
    }}>
      {name.charAt(0).toUpperCase()}
    </div>
  );
}

/* ─── Btn ─── */
export function Btn({ children, onClick, full = false, kind = 'primary', style: extra = {} }) {
  const v = {
    primary: { background: 'var(--saffron)', color: 'var(--on-primary)', border: 'none', boxShadow: '0 6px 18px color-mix(in srgb, var(--saffron) 38%, transparent)' },
    soft:    { background: 'var(--surface)',  color: 'var(--ink)', border: '1px solid var(--line)', boxShadow: 'var(--shadow-sm)' },
    ghost:   { background: 'transparent',     color: 'var(--ink)', border: '1.5px solid var(--line)' },
  };
  return (
    <button onClick={onClick} style={{
      appearance: 'none', cursor: 'pointer',
      fontFamily: 'var(--font-sans)', fontWeight: 700, fontSize: 16, lineHeight: 1,
      padding: '15px 22px', borderRadius: 16,
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
      width: full ? '100%' : 'auto',
      ...v[kind], ...extra,
    }}>{children}</button>
  );
}

/* ─── Chip ─── */
export function Chip({ children, active = false, onClick }) {
  return (
    <button onClick={onClick} style={{
      appearance: 'none', cursor: 'pointer',
      fontFamily: 'var(--font-sans)', fontWeight: 700, fontSize: 13,
      padding: '8px 16px', borderRadius: 999, whiteSpace: 'nowrap',
      background: active ? 'var(--saffron)' : 'var(--surface)',
      color:      active ? 'var(--on-primary)' : 'var(--ink-2)',
      border:     active ? 'none' : '1px solid var(--line)',
    }}>{children}</button>
  );
}
