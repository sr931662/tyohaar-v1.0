import { motion } from 'framer-motion';
import { useTheme } from '../../context/ThemeContext.jsx';
import styles from './ThemeToggle.module.css';

/**
 * ThemeToggle — switch between Warm Light and Festival of Lights.
 * Sun = daylight, Diya = dusk.
 */
export default function ThemeToggle({ className = '' }) {
  const { theme, toggle } = useTheme();
  const isDark = theme === 'dark';

  return (
    <button
      className={`${styles.toggle} ${className}`}
      onClick={toggle}
      role="switch"
      aria-checked={isDark}
      aria-label={isDark ? 'Switch to Warm Light' : 'Switch to Festival of Lights'}
      title={isDark ? 'Warm Light' : 'Festival of Lights'}
    >
      <motion.span
        className={styles.knob}
        layout
        transition={{ type: 'spring', stiffness: 500, damping: 34 }}
        data-on={isDark}
      >
        <span className={styles.icon}>{isDark ? '🪔' : '☀'}</span>
      </motion.span>
    </button>
  );
}
