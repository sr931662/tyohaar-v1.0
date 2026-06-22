import { motion } from 'framer-motion';
import { fadeUp, stagger, inView } from '../../lib/motion';
import styles from './SectionHeading.module.css';

/**
 * SectionHeading — eyebrow + serif title + optional lede.
 * Reveals on scroll with a staggered entrance.
 */
export default function SectionHeading({ eyebrow, title, deva, lede, align = 'left', light }) {
  return (
    <motion.header
      className={`${styles.head} ${align === 'center' ? styles.center : ''} ${light ? styles.light : ''}`}
      variants={stagger(0.12)}
      initial="hidden"
      whileInView="show"
      viewport={inView}
    >
      {eyebrow && (
        <motion.span className={styles.eyebrow} variants={fadeUp}>
          {eyebrow}
        </motion.span>
      )}
      <motion.h2 className={`ty-display ${styles.title}`} variants={fadeUp}>
        {title}
        {deva && <span className={styles.deva}> {deva}</span>}
      </motion.h2>
      {lede && (
        <motion.p className={styles.lede} variants={fadeUp}>
          {lede}
        </motion.p>
      )}
    </motion.header>
  );
}
