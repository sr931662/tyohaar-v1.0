import { motion } from 'framer-motion';
import SectionHeading from '../ui/SectionHeading.jsx';
import Emblem from '../ui/Emblem.jsx';
import HangingLights from '../ui/HangingLights.jsx';
import { occasions } from '../../data/occasions.js';
import { bloom, stagger, inView } from '../../lib/motion';
import styles from './Occasions.module.css';

export default function Occasions() {
  return (
    <section id="occasions" className={`ty-section ${styles.section}`}>
      {/* Cascading fairy-light strings hanging from the top edges, with a soft glow behind */}
      <div className={`${styles.lights} ${styles.lightsL}`} aria-hidden="true">
        <span className={styles.glow} />
        <HangingLights />
      </div>
      <div className={`${styles.lights} ${styles.lightsR}`} aria-hidden="true">
        <span className={styles.glow} />
        <HangingLights />
      </div>

      <div className="ty-container">
        <SectionHeading
          eyebrow="Every milestone, held with care"
          title="One home for every occasion"
          lede="Whatever you’re celebrating, Tyohaar already knows the shape of it — the rituals, the rhythm, the people who matter."
        />

        <motion.ul
          className={styles.grid}
          variants={stagger(0.07)}
          initial="hidden"
          whileInView="show"
          viewport={inView}
        >
          {occasions.map((o) => (
            <motion.li
              key={o.id}
              className={styles.card}
              variants={bloom}
              whileHover={{ y: -6 }}
              transition={{ duration: 0.3 }}
              style={{ '--tint': `var(--${o.tint})` }}
            >
              <div className={styles.emblem}>
                <Emblem type={o.emblem} tint={o.tint} size={44} />
              </div>
              <h3 className={styles.name}>{o.en}</h3>
              <p className={styles.sub}>{o.sub}</p>
              <p className={styles.blurb}>{o.blurb}</p>
              <span className={styles.arrow} aria-hidden="true">→</span>
            </motion.li>
          ))}
        </motion.ul>
      </div>
    </section>
  );
}
