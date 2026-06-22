import { motion } from 'framer-motion';
import SectionHeading from '../ui/SectionHeading.jsx';
import ServiceIcon from '../ui/ServiceIcon.jsx';
import { services } from '../../data/services.js';
import { bloom, stagger, inView } from '../../lib/motion';
import styles from './PackageServices.module.css';

export default function PackageServices() {
  return (
    <section id="services" className="ty-section">
      <div className="ty-container">
        <SectionHeading
          eyebrow="What's inside every package"
          title="13 services. One booking."
          lede="Mix and match from a full menu of professional services. Add what you need, remove what you don't — your total updates live."
        />

        <motion.ul
          className={styles.grid}
          variants={stagger(0.05)}
          initial="hidden"
          whileInView="show"
          viewport={inView}
          role="list"
        >
          {services.map((s) => (
            <motion.li
              key={s.name}
              className={styles.tile}
              variants={bloom}
              style={{ '--tint': `var(--${s.tint})` }}
            >
              <span className={styles.icon}>
                <ServiceIcon name={s.name} size={22} strokeWidth={1.8} />
              </span>
              <span className={styles.name}>{s.name}</span>
              <span className={styles.desc}>{s.desc}</span>
            </motion.li>
          ))}
        </motion.ul>

        <motion.p
          className={styles.note}
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={inView}
          transition={{ duration: 0.6, delay: 0.3 }}
        >
          Every service is professionally fulfilled and fulfilled at your venue.
          Services not included in your package can be added individually at transparent prices.
        </motion.p>
      </div>
    </section>
  );
}
