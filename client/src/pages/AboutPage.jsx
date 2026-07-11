import { motion } from 'framer-motion';
import Navbar from '../components/layout/Navbar.jsx';
import Footer from '../components/layout/Footer.jsx';
import SectionHeading from '../components/ui/SectionHeading.jsx';
import { fadeUp, bloom, stagger, inView } from '../lib/motion';
import styles from './AboutPage.module.css';

const founders = [
  {
    name: 'Karn Goyal',
    title: 'Co-Founder',
    photo: null,
    bio: 'Bio coming soon.',
  },
  {
    name: 'Arjun Goyal',
    title: 'Co-Founder',
    photo: null,
    bio: 'Bio coming soon.',
  },
];

const values = [
  {
    title: 'Tradition, made effortless',
    body: 'Every ritual and custom is honoured — we just remove the logistics that get in the way of celebrating it.',
  },
  {
    title: 'Vetted, not just listed',
    body: 'Every vendor on Tyohaar is verified for quality and reliability before they ever reach a customer.',
  },
  {
    title: 'Built for Indian families',
    body: 'From guest lists to multi-day functions, the product is designed around how celebrations actually happen here.',
  },
];

export default function AboutPage() {
  return (
    <>
      <Navbar />
      <main id="top" className={styles.page}>
        <section className={`ty-section ${styles.hero}`}>
          <div className={`ty-container ${styles.heroInner}`}>
            <motion.span
              className={styles.eyebrow}
              initial="hidden"
              animate="show"
              variants={fadeUp}
            >
              About Tyohaar
            </motion.span>
            <motion.h1
              className={`ty-display ${styles.title}`}
              initial="hidden"
              animate="show"
              variants={fadeUp}
              transition={{ delay: 0.08 }}
            >
              Every celebration deserves to be about the people, not the planning.
            </motion.h1>
            <motion.p
              className={styles.lede}
              initial="hidden"
              animate="show"
              variants={fadeUp}
              transition={{ delay: 0.16 }}
            >
              Tyohaar connects families with vetted vendors and curated packages for every
              milestone — from Haldi to housewarmings — so you can be present for the moment
              instead of managing it.
            </motion.p>
          </div>
        </section>

        <section className={`ty-section ${styles.story}`}>
          <div className="ty-container">
            <SectionHeading
              eyebrow="Our story"
              title="Why we built Tyohaar"
              align="left"
            />
            <motion.div
              className={styles.storyBody}
              variants={stagger(0.12)}
              initial="hidden"
              whileInView="show"
              viewport={inView}
            >
              <motion.p variants={fadeUp}>
                Planning a celebration in India means juggling dozens of vendors, last-minute
                changes, and a guest list that grows by the day — usually all at once, and
                usually for an event that only happens once. We started Tyohaar to bring that
                sprawl into one place: a single app to discover trusted vendors, book curated
                packages, and manage guests and logistics for any occasion.
              </motion.p>
              <motion.p variants={fadeUp}>
                Our mission is to preserve tradition while embracing the convenience of the
                modern world, making family gatherings more meaningful and effortless — whether
                that's a Diwali get-together, a wedding function, or a baby shower.
              </motion.p>
            </motion.div>
          </div>
        </section>

        <section className={`ty-section ${styles.values}`}>
          <div className="ty-container">
            <SectionHeading eyebrow="What we believe" title="How we work" align="left" />
            <motion.div
              className={styles.valuesGrid}
              variants={stagger(0.1)}
              initial="hidden"
              whileInView="show"
              viewport={inView}
            >
              {values.map((v) => (
                <motion.div key={v.title} className={styles.valueCard} variants={bloom}>
                  <h3 className={styles.valueTitle}>{v.title}</h3>
                  <p className={styles.valueBody}>{v.body}</p>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        <section className={`ty-section ${styles.team}`}>
          <div className="ty-container">
            <SectionHeading
              eyebrow="Leadership"
              title="Meet the co-founders"
              align="center"
            />
            <motion.div
              className={styles.teamGrid}
              variants={stagger(0.12)}
              initial="hidden"
              whileInView="show"
              viewport={inView}
            >
              {founders.map((f) => (
                <motion.div key={f.name} className={styles.founderCard} variants={bloom}>
                  <div className={styles.founderPhoto}>
                    {f.photo ? (
                      <img src={f.photo} alt={f.name} />
                    ) : (
                      <span className={styles.founderPlaceholder} aria-hidden="true">
                        {f.name.charAt(0)}
                      </span>
                    )}
                  </div>
                  <h3 className={styles.founderName}>{f.name}</h3>
                  <span className={styles.founderTitle}>{f.title}</span>
                  <p className={styles.founderBio}>{f.bio}</p>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
