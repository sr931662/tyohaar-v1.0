import { motion } from 'framer-motion';
import SectionHeading from '../ui/SectionHeading.jsx';
import Flourish from '../ui/Flourish.jsx';
import { steps } from '../../data/steps.js';
import { fadeUp, fadeRight, stagger, inView } from '../../lib/motion';
import panelLeft from '../../assets/ornaments/side-panel-left.svg';
import panelRight from '../../assets/ornaments/side-panel-right.svg';
import styles from './HowItWorks.module.css';

export default function HowItWorks() {
  return (
    <section id="how" className={`ty-section ${styles.wrap}`}>
      {/* Tall decorative side panels framing the section */}
      <img src={panelLeft} alt="" aria-hidden="true" className={styles.panelLeft} />
      <img src={panelRight} alt="" aria-hidden="true" className={styles.panelRight} />

      <div className="ty-container">
        <SectionHeading
          eyebrow="From app to your door"
          title="Five steps to your celebration"
          deva="उत्सव"
          lede="Browse packages, choose your services, and confirm your date and venue — all in the app. Tyohaar then coordinates every partner so everything is ready before your first guest arrives."
        />

        <div className={styles.layout}>
          {/* The vertical timeline of steps */}
          <motion.ol
            className={styles.steps}
            variants={stagger(0.12)}
            initial="hidden"
            whileInView="show"
            viewport={inView}
          >
            {steps.map((s) => (
              <motion.li key={s.n} className={styles.step} variants={fadeRight}>
                <div className={styles.marker}>
                  <span className={styles.num}>{s.n}</span>
                </div>
                <div className={styles.body}>
                  <h3 className={styles.stepTitle}>
                    {s.title}
                    <span className={styles.stepDeva}>{s.deva}</span>
                  </h3>
                  <p className={styles.stepText}>{s.body}</p>
                </div>
              </motion.li>
            ))}
          </motion.ol>

          {/* A calm summary panel */}
          <motion.aside
            className={styles.panel}
            variants={fadeUp}
            initial="hidden"
            whileInView="show"
            viewport={inView}
          >
            <div className={styles.panelGlow} />
            <p className={styles.panelEyebrow}>The promise</p>
            <p className={`ty-display ${styles.panelQuote}`}>
              Pick your package. Set your date and venue. We deliver the complete celebration to your door.
            </p>
            <Flourish className={styles.panelFlourish} width={200} />
            <p className={styles.panelHindi}>आप बस मेजबान बनें।</p>
          </motion.aside>
        </div>
      </div>
    </section>
  );
}
