import { Link } from 'react-router-dom';
import logo from '../../assets/logo.png';
import styles from './Logo.module.css';

export default function Logo({ size = 'md', onClick, to = '/' }) {
  return (
    <Link
      to={to}
      className={`${styles.logo} ${styles[size]}`}
      onClick={onClick}
      aria-label="Tyohaar home"
    >
      <img src={logo} alt="" className={styles.emblem} aria-hidden="true" />
      <span className={styles.wordmark}>Tyohaar</span>
    </Link>
  );
}
