import Diya from '../ui/Diya.jsx';
import { useOccasions } from '../../hooks/useOccasions.js';
import styles from './Marquee.module.css';

export default function Marquee() {
  const { occasions } = useOccasions();
  // Build a doubled track for a seamless loop.
  const items = [...occasions, ...occasions];

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
