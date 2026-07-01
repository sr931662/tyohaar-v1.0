import { motion } from 'framer-motion';
import Button from '../ui/Button.jsx';
import SectionHeading from '../ui/SectionHeading.jsx';
import { packages } from '../../data/packages.js';
import { bloom, fadeUp, stagger, inView } from '../../lib/motion';
import styles from './Packages.module.css';

export default function Packages() {
  return (
    <section id="packages" className={`ty-section ${styles.wrap}`}>
      <div className="ty-container">
        <SectionHeading
          eyebrow="Built for every scale"
          title="Three tiers of celebration"
          lede="From an intimate home gathering to a grand affair — pick the tier that fits your occasion. Pricing is tailored to your date and venue, shared with you in the app."
        />

        <motion.div
          className={styles.grid}
          variants={stagger(0.1)}
          initial="hidden"
          whileInView="show"
          viewport={inView}
        >
          {packages.map((pkg) => {
            const isFeatured = pkg.tag === 'Most popular';
            return (
              <motion.article
                key={pkg.id}
                className={`${styles.card} ${isFeatured ? styles.featured : ''}`}
                variants={bloom}
                style={{ '--tint': `var(--${pkg.tint})` }}
              >
                {/* Top accent */}
                <div className={styles.accent} />

                {/* Badge */}
                {pkg.tag && (
                  <span className={`${styles.badge} ${isFeatured ? styles.badgeFeatured : styles.badgeSoft}`}>
                    {pkg.tag}
                  </span>
                )}

                {/* Name */}
                <div className={styles.nameRow}>
                  <h3 className={styles.name}>{pkg.name}</h3>
                  <span className={styles.sub}>{pkg.sub}</span>
                </div>

                {/* Guest count */}
                <span className={styles.guests}>{pkg.guests}</span>

                {/* Description */}
                <p className={styles.desc}>{pkg.description}</p>

                <div className={styles.divider} />

                {/* Best for */}
                <p className={styles.best}>
                  <span className={styles.bestLabel}>Best for · </span>
                  {pkg.best}
                </p>

                <div className={styles.cta}>
                  <Button
                    href="#download"
                    size="lg"
                    variant={isFeatured ? 'primary' : 'soft'}
                    full
                  >
                    Explore package →
                  </Button>
                </div>
              </motion.article>
            );
          })}
        </motion.div>

        {/* Custom package note */}
        <motion.div
          className={styles.custom}
          variants={fadeUp}
          initial="hidden"
          whileInView="show"
          viewport={inView}
        >
          <p className={styles.customText}>
            Need something tailor-made?{' '}
            <a href="#download" className={styles.customLink}>Talk to us in the app →</a>
          </p>
          <p className={styles.customNote}>
            Exact pricing is confirmed after your date, venue and guest count — no surprises.
          </p>
        </motion.div>
      </div>
    </section>
  );
}
