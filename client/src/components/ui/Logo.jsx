import logo from '../../assets/logo.png';
import styles from './Logo.module.css';

export default function Logo({ size = 'md', onClick, href = '#top' }) {
  return (
    <a href={href} className={`${styles.logo} ${styles[size]}`} onClick={onClick} aria-label="Tyohaar — home">
      <img src={logo} alt="" className={styles.emblem} aria-hidden="true" />
      <span className={styles.wordmark}>Tyohaar</span>
    </a>
  );
}
