import { motion } from 'framer-motion';
import Button from '../ui/Button.jsx';
import Diya from '../ui/Diya.jsx';
import balloons from '../../assets/ornaments/balloons-corner.svg';
import filigree from '../../assets/ornaments/filigree-medallion.svg';
import giftBox from '../../assets/ornaments/gift-corner.svg';
import { fadeUp, stagger, inView } from '../../lib/motion';
import styles from './CTA.module.css';

export default function CTA() {
  return (
    <section id="download" className={`ty-section ${styles.wrap}`}>
      <div className="ty-container">
        <motion.div
          className={styles.band}
          variants={stagger(0.1)}
          initial="hidden"
          whileInView="show"
          viewport={inView}
        >
          {/* luminous arches inside the band */}
          <div className={styles.arches} aria-hidden="true">
            <span /><span /><span />
          </div>

          {/* corner celebration art — balloons (left, mirrored) & gift box (right) */}
          <img src={balloons} alt="" aria-hidden="true" className={styles.balloons} />
          <img src={giftBox} alt="" aria-hidden="true" className={styles.gift} />

          <motion.span className={styles.eyebrow} variants={fadeUp}>
            <Diya size={8} /> Your next celebration starts here
          </motion.span>
          <motion.h2 className={`ty-display ${styles.title}`} variants={fadeUp}>
            Let’s make a memory.
          </motion.h2>
          <motion.p className={styles.deva} variants={fadeUp}>त्योहार</motion.p>
          <motion.p className={styles.text} variants={fadeUp}>
            Download Tyohaar and plan your first celebration in minutes — free to start, with you
            every step of the way.
          </motion.p>

          <motion.div className={styles.actions} variants={fadeUp}>
            <Button href="#" size="lg" className={styles.appBtn}>
               App Store
            </Button>
            <Button href="#" size="lg" variant="ghost" className={styles.ghostOnDark}>
              ▶ Google Play
            </Button>
          </motion.div>

          <motion.p className={styles.fine} variants={fadeUp}>
            Free to download · No card required · Available across India
          </motion.p>

          {/* Symmetric filigree divider above fine print */}
          <img src={filigree} alt="" aria-hidden="true" className={styles.filigree} />
        </motion.div>
      </div>
    </section>
  );
}
