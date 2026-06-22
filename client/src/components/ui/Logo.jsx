import logo from '../../assets/tyohaar-logo.png';
import styles from './Logo.module.css';

/**
 * Tyohaar brand lockup (emblem + wordmark) as an image.
 * @param {'sm'|'md'|'lg'} size  controls the rendered height
 */
export default function Logo({ size = 'md', onClick, href = '#top' }) {
  return (
    <a href={href} className={`${styles.logo} ${styles[size]}`} onClick={onClick} aria-label="Tyohaar — home">
      <img src={logo} alt="Tyohaar" className={styles.img} />
    </a>
  );
}
