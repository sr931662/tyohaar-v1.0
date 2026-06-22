import { motion } from 'framer-motion';
import SectionHeading from '../ui/SectionHeading.jsx';
import { testimonials } from '../../data/testimonials.js';
import { bloom, stagger, inView } from '../../lib/motion';
import styles from './Testimonials.module.css';

export default function Testimonials() {
  return (
    <section id="stories" className={`ty-section ${styles.wrap}`}>
      <div className="ty-container">
        <SectionHeading
          eyebrow="From families like yours"
          title="The moments people remember"
          align="center"
        />

        <motion.div
          className={styles.grid}
          variants={stagger(0.1)}
          initial="hidden"
          whileInView="show"
          viewport={inView}
        >
          {testimonials.map((t, i) => (
            <motion.figure
              key={i}
              className={`${styles.card} ${i === 0 ? styles.feature : ''}`}
              variants={bloom}
              style={{ '--tint': `var(--${t.tint})` }}
            >
              <span className={styles.quoteMark} aria-hidden="true">”</span>
              <blockquote className={styles.quote}>{t.quote}</blockquote>
              <figcaption className={styles.cite}>
                <span className={styles.avatar} aria-hidden="true">{t.name.charAt(0)}</span>
                <span>
                  <span className={styles.name}>{t.name}</span>
                  <span className={styles.role}>{t.role}</span>
                </span>
              </figcaption>
            </motion.figure>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
