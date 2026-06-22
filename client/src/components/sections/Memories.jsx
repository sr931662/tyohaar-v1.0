import { motion } from 'framer-motion';
import { Check } from 'lucide-react';
import SectionHeading from '../ui/SectionHeading.jsx';
import Placeholder from '../ui/Placeholder.jsx';
import Button from '../ui/Button.jsx';
import giftBox from '../../assets/ornaments/birthday-gift-box.svg';
import diwaliAnaar from '../../assets/ornaments/diwali-anaar.svg';
import holiPlate from '../../assets/ornaments/holi-plate-gold.svg';
import { fadeLeft, fadeUp, stagger, bloom, inView } from '../../lib/motion';
import styles from './Memories.module.css';

export default function Memories() {
  return (
    <section id="memories" className={`ty-section ${styles.wrap}`}>
      <div className={`ty-container ${styles.layout}`}>
        {/* collage */}
        <motion.div
          className={styles.collage}
          variants={stagger(0.1)}
          initial="hidden"
          whileInView="show"
          viewport={inView}
        >
          <motion.div className={styles.m1} variants={bloom}>
            <Placeholder
              label="diwali · 2025"
              tint="saffron"
              ratio="3 / 4"
              emblem={<img src={diwaliAnaar} alt="" />}
            />
          </motion.div>
          <motion.div className={styles.m2} variants={bloom}>
            <Placeholder
              label="dadi’s 70th"
              tint="rose"
              ratio="1 / 1"
              emblem={<img src={giftBox} alt="" />}
            />
          </motion.div>
          <motion.div className={styles.m3} variants={bloom}>
            <Placeholder
              label="holi at home"
              tint="leaf"
              ratio="4 / 3"
              emblem={<img src={holiPlate} alt="" />}
            />
          </motion.div>
        </motion.div>

        {/* copy */}
        <motion.div
          className={styles.copy}
          variants={stagger(0.12)}
          initial="hidden"
          whileInView="show"
          viewport={inView}
        >
          <motion.span className={styles.eyebrow} variants={fadeLeft}>
            After the lamps dim
          </motion.span>
          <motion.h2 className={`ty-display ${styles.title}`} variants={fadeLeft}>
            A celebration shouldn’t end when the guests leave.
          </motion.h2>
          <motion.p className={styles.text} variants={fadeUp}>
            Tyohaar keeps every moment — the photos, the guest notes, the menu, the people who
            came — woven into a living memory you’ll return to for years. Each celebration becomes
            a page in your family’s story.
          </motion.p>
          <motion.ul className={styles.list} variants={stagger(0.08)}>
            {[
              'A shared album every guest can add to',
              'The full story: vendors, menu, timeline, speeches',
              'Gentle reminders when the anniversary returns',
            ].map((t) => (
              <motion.li key={t} variants={fadeUp}>
                <span className={styles.tick} aria-hidden="true">
                  <Check size={14} strokeWidth={2.5} />
                </span>
                {t}
              </motion.li>
            ))}
          </motion.ul>
          <motion.div variants={fadeUp}>
            <Button href="#download" variant="soft">Explore Memories</Button>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
