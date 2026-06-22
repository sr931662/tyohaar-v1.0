import { motion } from 'framer-motion';
import styles from './Button.module.css';

/**
 * Button — renders as <a> when `href` is given, else <button>.
 * variants: primary | ghost | soft
 * sizes: md | lg
 */
export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  href,
  onClick,
  type = 'button',
  full = false,
  icon = null,
  className = '',
  ...rest
}) {
  const cls = `${styles.btn} ${styles[variant]} ${styles[size]} ${full ? styles.full : ''} ${className}`;
  const motionProps = {
    whileHover: { y: -2 },
    whileTap: { scale: 0.97 },
    transition: { duration: 0.2, ease: [0.2, 0.8, 0.2, 1] },
  };

  if (href) {
    return (
      <motion.a href={href} className={cls} onClick={onClick} {...motionProps} {...rest}>
        {children}
        {icon && <span className={styles.icon}>{icon}</span>}
      </motion.a>
    );
  }

  return (
    <motion.button type={type} className={cls} onClick={onClick} {...motionProps} {...rest}>
      {children}
      {icon && <span className={styles.icon}>{icon}</span>}
    </motion.button>
  );
}
