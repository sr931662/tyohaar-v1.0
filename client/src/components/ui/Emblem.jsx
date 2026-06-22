import { Cake, Wine, House, Gem, Baby, Sparkles, Users, Heart } from 'lucide-react';
import styles from './Emblem.module.css';

/**
 * Emblem — celebration symbol rendered with a production-grade lucide-react icon,
 * tinted per occasion via `tint` (saffron | rose | leaf | gold).
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

export default function Emblem({ type = 'cake', tint = 'saffron', size = 44 }) {
  const Icon = ICONS[type] || Cake;
  return (
    <span
      className={styles.wrap}
      style={{ width: size, height: size, '--em-color': `var(--${tint})` }}
      aria-hidden="true"
    >
      <Icon size={size} strokeWidth={1.6} />
    </span>
  );
}
