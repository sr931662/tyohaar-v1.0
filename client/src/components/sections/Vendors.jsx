import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import SectionHeading from '../ui/SectionHeading.jsx';
import Placeholder from '../ui/Placeholder.jsx';
import { vendors, vendorCategories } from '../../data/vendors.js';
import { bloom, inView } from '../../lib/motion';
import styles from './Vendors.module.css';

const priceLabel = (p) => '₹'.repeat(p) + '·'.repeat(3 - p);

export default function Vendors() {
  const [cat, setCat] = useState('All');
  const list = cat === 'All' ? vendors : vendors.filter((v) => v.cat === cat);

  return (
    <section id="partners" className="ty-section">
      <div className="ty-container">
        <SectionHeading
          eyebrow="Hand-picked, never crowd-sourced"
          title="Partners families trust"
          lede="Every caterer, decorator and photographer is vetted, rated and held to one standard: they show up exactly as promised."
        />

        {/* category filter */}
        <div className={styles.filters} role="tablist" aria-label="Partner categories">
          {vendorCategories.map((c) => (
            <button
              key={c}
              role="tab"
              aria-selected={cat === c}
              className={`${styles.chip} ${cat === c ? styles.chipOn : ''}`}
              onClick={() => setCat(c)}
            >
              {c}
            </button>
          ))}
        </div>

        <motion.ul layout className={styles.grid}>
          <AnimatePresence mode="popLayout">
            {list.map((v) => (
              <motion.li
                layout
                key={v.id}
                className={styles.card}
                variants={bloom}
                initial="hidden"
                whileInView="show"
                viewport={inView}
                exit={{ opacity: 0, scale: 0.92 }}
                whileHover={{ y: -6 }}
              >
                <div className={styles.media}>
                  <Placeholder label={v.cat.toLowerCase()} tint={v.tint} ratio="16 / 11" />
                  <span className={styles.rating}>★ {v.rating.toFixed(1)}</span>
                </div>
                <div className={styles.info}>
                  <span className={styles.cat}>{v.cat}</span>
                  <h3 className={styles.name}>{v.name}</h3>
                  <p className={styles.note}>{v.note}</p>
                  <div className={styles.meta}>
                    <span className={styles.price}>{priceLabel(v.price)}</span>
                    <span className={styles.from}>from {v.from}</span>
                  </div>
                </div>
              </motion.li>
            ))}
          </AnimatePresence>
        </motion.ul>
      </div>
    </section>
  );
}
