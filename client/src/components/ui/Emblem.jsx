import { useState } from 'react';
import { Cake, Wine, House, Gem, Baby, Sparkles, Users, Heart } from 'lucide-react';
import styles from './Emblem.module.css';

/**
 * Emblem — celebration symbol, tinted per occasion via `tint` (saffron | rose | leaf | gold).
 * Renders a backend-supplied `iconUrl` image when present; falls back to a
 * production-grade lucide-react icon (keyed by `type`) if the URL is absent
 * or fails to load.
 */
const ICONS = {
  cake: Cake,
  wine: Wine,
  house: House,
  gem: Gem,
  baby: Baby,
  sparkles: Sparkles,
  users: Users,
  heart: Heart,
};

export default function Emblem({ type = 'cake', tint = 'saffron', size = 44, iconUrl = null }) {
  const [imgFailed, setImgFailed] = useState(false);
  const Icon = ICONS[type] || Sparkles;

  return (
    <span
      className={styles.wrap}
      style={{ width: size, height: size, '--em-color': `var(--${tint})` }}
      aria-hidden="true"
    >
      {iconUrl && !imgFailed ? (
        <img
          src={iconUrl}
          alt=""
          loading="lazy"
          width={size}
          height={size}
          style={{ width: size, height: size, objectFit: 'contain' }}
          onError={() => setImgFailed(true)}
        />
      ) : (
        <Icon size={size} strokeWidth={1.6} />
      )}
    </span>
  );
}
