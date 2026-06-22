import styles from './Diya.module.css';

/**
 * Diya — the brand's living spark (a glowing dot of light).
 * @param {number} size  diameter in px
 * @param {boolean} pulse  whether it breathes (default true)
 */
export default function Diya({ size = 12, pulse = true, className = '' }) {
  return (
    <span
      className={`${styles.diya} ${pulse ? styles.pulse : ''} ${className}`}
      style={{ '--diya-size': `${size}px` }}
      aria-hidden="true"
    />
  );
}
