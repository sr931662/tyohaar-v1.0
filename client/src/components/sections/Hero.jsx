import { motion } from 'framer-motion';
import Button from '../ui/Button.jsx';
import Diya from '../ui/Diya.jsx';
import HeroOrnament from '../ui/HeroOrnament.jsx';
import { useTheme } from '../../context/ThemeContext.jsx';
import { fadeUp, stagger, EASE } from '../../lib/motion';
import darkScreenshot from '../../assets/screenshots/dark mode SS tyohaar.jpeg';
import lightScreenshot from '../../assets/screenshots/light mode SS tyohaar.jpeg';
import styles from './Hero.module.css';

const floatFast = {
  animate: { y: [0, 8, 0], transition: { duration: 5.5, repeat: Infinity, ease: 'easeInOut', delay: 0.8 } },
};
const floatSlow = {
  animate: { y: [0, -10, 0], transition: { duration: 7, repeat: Infinity, ease: 'easeInOut' } },
};

export default function Hero() {
  const { theme } = useTheme();
  return (
    <section className={styles.hero}>
      <div className={styles.arches} aria-hidden="true">
        <span className={styles.arch} />
        <span className={`${styles.arch} ${styles.archTall}`} />
        <span className={styles.arch} />
      </div>
      <div className={styles.glow} aria-hidden="true" />

      {/* Premium paisley flourishes — top corners, aimed toward the interior.
          Artwork natively faces SW: top-left mirrors to face SE, top-right stays native (SW). */}
      <HeroOrnament className={styles.ornTL} flipped />
      <HeroOrnament className={styles.ornTR} />

      <div className={`ty-container ${styles.inner}`}>
        {/* Left: copy */}
        <motion.div
          className={styles.copy}
          variants={stagger(0.12, 0.1)}
          initial="hidden"
          animate="show"
        >
          <motion.span className={styles.badge} variants={fadeUp}>
            <Diya size={9} /> Celebration packages · delivered to your venue
          </motion.span>

          <motion.h1 className={`ty-display ${styles.title}`} variants={fadeUp}>
            The home for
            <br />
            life's <em className={styles.em}>celebrations</em>.
          </motion.h1>

          <motion.p className={styles.deva} variants={fadeUp}>
            त्योहार
          </motion.p>

          <motion.p className={styles.lede} variants={fadeUp}>
            Choose from curated celebration packages for birthdays, anniversaries, weddings and
            more. Pick your services, confirm your date and venue — home, villa or farmhouse — and
            we deliver the entire celebration to you.
          </motion.p>

          <motion.div className={styles.actions} variants={fadeUp}>
            <Button href="#download" size="lg">Browse packages</Button>
            <Button href="#how" variant="ghost" size="lg">See how it works</Button>
          </motion.div>

          <motion.div className={styles.proof} variants={fadeUp}>
            <div className={styles.stat}>
              <strong>12,000+</strong>
              <span>celebrations delivered</span>
            </div>
            <div className={styles.divider} />
            <div className={styles.stat}>
              <strong>800+</strong>
              <span>verified service partners</span>
            </div>
            <div className={styles.divider} />
            <div className={styles.stat}>
              <strong>4.9 ★</strong>
              <span>average host rating</span>
            </div>
          </motion.div>
        </motion.div>

        {/* Right: live interactive app demo + floating badges */}
        <motion.div
          className={styles.visual}
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.9, ease: EASE, delay: 0.25 }}
        >
          <div className={styles.phoneWrap}>
            <div className={styles.phoneZoom}>
              <img
                src={theme === 'dark' ? darkScreenshot : lightScreenshot}
                alt="Tyohaar app"
                className={styles.screenshot}
              />
            </div>
          </div>

          {/* Toast: booking confirmed */}
          <motion.div className={`${styles.toast} ${styles.toastBooked}`} variants={floatFast} animate="animate">
            <span className={styles.toastDot} />
            <span>Package confirmed</span>
            <span className={styles.toastCheck}>✓</span>
          </motion.div>

          {/* Toast: rating */}
          <motion.div className={`${styles.toast} ${styles.toastRating}`} variants={floatSlow} animate="animate">
            <span className={styles.toastStars}>★ 4.9</span>
            <span className={styles.toastLabel}>host rating</span>
          </motion.div>

        </motion.div>
      </div>

      <a href="#occasions" className={styles.scrollCue} aria-label="Scroll down">
        <span>Scroll</span>
        <span className={styles.arrow}>↓</span>
      </a>
    </section>
  );
}
