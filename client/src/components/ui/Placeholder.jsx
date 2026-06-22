import styles from './Placeholder.module.css';

/**
 * Placeholder — arch-topped, tinted image stand-in with a monospace label.
 * Swap these for real photography (the single biggest visual upgrade).
 * @param {string} label  monospace caption (e.g. "venue · golden hour")
 * @param {string} tint   saffron | rose | leaf | gold
 * @param {boolean} arch  round the top into a doorway (default true)
 * @param {string} ratio  CSS aspect-ratio (e.g. "4 / 5")
 * @param {React.ReactNode} emblem  custom centerpiece that replaces the default orb
 */
export default function Placeholder({
  label = '',
  tint = 'saffron',
  arch = true,
  ratio = '4 / 5',
  className = '',
  emblem,
  children,
}) {
  const style = {
    '--ph-color': `var(--${tint})`,
    aspectRatio: ratio,
    borderRadius: arch ? '999px 999px var(--r-lg) var(--r-lg)' : 'var(--r-lg)',
  };
  return (
    <div className={`${styles.ph} ${className}`} style={style}>
      {emblem ? <div className={styles.emblem}>{emblem}</div> : <div className={styles.orb} />}
      {children}
      {label && <span className={styles.label}>{label}</span>}
    </div>
  );
}
