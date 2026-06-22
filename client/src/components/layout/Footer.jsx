import Logo from '../ui/Logo.jsx';
import Diya from '../ui/Diya.jsx';
import { footerColumns } from '../../data/nav.js';
import styles from './Footer.module.css';

export default function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className={styles.footer}>
      <div className={`ty-container ${styles.inner}`}>
        <div className={styles.brand}>
          <Logo deva size="md" />
          <p className={styles.tagline}>
            The home for life’s celebrations.
            <br />
            <span className={styles.hindi}>आप मनाइए, बाकी हम संभालें।</span>
          </p>
          <div className={styles.stores}>
            <a href="#download" className={styles.store}>
              <span className={styles.storeSub}>Download on the</span>
              <span className={styles.storeName}>App Store</span>
            </a>
            <a href="#download" className={styles.store}>
              <span className={styles.storeSub}>Get it on</span>
              <span className={styles.storeName}>Google Play</span>
            </a>
          </div>
        </div>

        <div className={styles.cols}>
          {footerColumns.map((col) => (
            <div key={col.title} className={styles.col}>
              <h4 className={styles.colTitle}>{col.title}</h4>
              <ul>
                {col.links.map((l) => (
                  <li key={l.label}>
                    <a href={l.href}>{l.label}</a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      <div className={`ty-container ${styles.bottom}`}>
        <span className={styles.copy}>
          © {year} Tyohaar <Diya size={7} pulse={false} /> Made in India, for India.
        </span>
        <div className={styles.legal}>
          <a href="#">Privacy</a>
          <a href="#">Terms</a>
          <a href="#">Cookies</a>
        </div>
      </div>
    </footer>
  );
}
