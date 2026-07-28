import { motion } from 'framer-motion';
import { Mail, Phone } from 'lucide-react';
import Navbar from '../components/layout/Navbar.jsx';
import Footer from '../components/layout/Footer.jsx';
import SectionHeading from '../components/ui/SectionHeading.jsx';
import Button from '../components/ui/Button.jsx';
import { fadeUp, bloom, stagger, inView } from '../lib/motion';
import styles from './ContactPage.module.css';

const CONTACT_EMAIL = 'goyalkarn@gmail.com';
const CONTACT_PHONE = '+91 8860384909';
const CONTACT_PHONE_TEL = '+918860384909';

const channels = [
  {
    icon: Mail,
    label: 'Email',
    value: CONTACT_EMAIL,
    href: `mailto:${CONTACT_EMAIL}`,
  },
  {
    icon: Phone,
    label: 'Phone',
    value: CONTACT_PHONE,
    href: `tel:${CONTACT_PHONE_TEL}`,
  },
];

export default function ContactPage() {
  return (
    <>
      <Navbar />
      <main id="top" className={styles.page}>
        <section className={`ty-section ${styles.hero}`}>
          <div className={`ty-container ${styles.heroInner}`}>
            <motion.span className={styles.eyebrow} initial="hidden" animate="show" variants={fadeUp}>
              Contact us
            </motion.span>
            <motion.h1
              className={`ty-display ${styles.title}`}
              initial="hidden"
              animate="show"
              variants={fadeUp}
              transition={{ delay: 0.08 }}
            >
              We'd love to hear from you.
            </motion.h1>
            <motion.p
              className={styles.lede}
              initial="hidden"
              animate="show"
              variants={fadeUp}
              transition={{ delay: 0.16 }}
            >
              Questions about a booking, a partnership, or anything else — reach out and we'll
              get back to you.
            </motion.p>
          </div>
        </section>

        <section className={`ty-section ${styles.body}`}>
          <div className="ty-container">
            <SectionHeading eyebrow="Get in touch" title="Ways to reach us" align="left" />
            <motion.div
              className={styles.channels}
              variants={stagger(0.1)}
              initial="hidden"
              whileInView="show"
              viewport={inView}
            >
              {channels.map(({ icon: Icon, label, value, href }) => (
                <motion.a key={label} href={href} className={styles.channelCard} variants={bloom}>
                  <span className={styles.channelIcon}>
                    <Icon size={20} strokeWidth={2} />
                  </span>
                  <span className={styles.channelText}>
                    <span className={styles.channelLabel}>{label}</span>
                    <span className={styles.channelValue}>{value}</span>
                  </span>
                </motion.a>
              ))}
            </motion.div>

            <div className={styles.cta}>
              <Button href={`mailto:${CONTACT_EMAIL}`} size="lg">
                Email us
              </Button>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
