import Diya from '../ui/Diya.jsx';
import { occasions } from '../../data/occasions.js';
import styles from './Marquee.module.css';

// Build a doubled track for a seamless loop.
const items = [...occasions, ...occasions];

export default function Marquee() {
  return (
    <div className={styles.band} aria-hidden="true">
      <div className={styles.track}>
        {items.map((o, i) => (
          <span className={styles.item} key={i}>
            <span className={styles.en}>{o.en}</span>
            <span className={styles.deva}>{o.sub}</span>
            <Diya size={7} pulse={false} className={styles.dot} />
          </span>
        ))}
      </div>
    </div>
  );
}
