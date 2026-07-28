import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import Navbar from '../../components/layout/Navbar.jsx';
import Footer from '../../components/layout/Footer.jsx';
import { fadeUp } from '../../lib/motion';
import styles from './LegalDocumentPage.module.css';

function formatDate(value) {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
}

/**
 * Shared shell for the three admin-published legal documents (Terms,
 * Privacy Policy, Cancellation & Refund Policy). Fetches the currently
 * published version from the public `/common/...` endpoints the admin
 * Settings → Legal tab writes to, so this always mirrors what's live —
 * there's no separate copy to keep in sync.
 */
export default function LegalDocumentPage({ eyebrow, title, queryKey, queryFn }) {
  const { data, isLoading, isError } = useQuery({ queryKey, queryFn });

  const effectiveDate = formatDate(data?.effective_date ?? data?.created_at);

  return (
    <>
      <Navbar />
      <main id="top" className={styles.page}>
        <section className={`ty-section ${styles.hero}`}>
          <div className={`ty-container ${styles.heroInner}`}>
            <motion.span className={styles.eyebrow} initial="hidden" animate="show" variants={fadeUp}>
              {eyebrow}
            </motion.span>
            <motion.h1
              className={`ty-display ${styles.title}`}
              initial="hidden"
              animate="show"
              variants={fadeUp}
              transition={{ delay: 0.08 }}
            >
              {data?.title || title}
            </motion.h1>
            {data && (
              <motion.p
                className={styles.meta}
                initial="hidden"
                animate="show"
                variants={fadeUp}
                transition={{ delay: 0.14 }}
              >
                Version {data.version}
                {effectiveDate && <> &middot; Effective {effectiveDate}</>}
              </motion.p>
            )}
          </div>
        </section>

        <section className={`ty-section ${styles.body}`}>
          <div className="ty-container">
            {isLoading && (
              <div className={styles.state}>
                <span className={styles.spinner} aria-hidden="true" />
              </div>
            )}

            {!isLoading && isError && (
              <div className={styles.state}>
                <p>We couldn't load this document right now. Please try again shortly.</p>
              </div>
            )}

            {!isLoading && !isError && !data && (
              <div className={styles.state}>
                <p>{title} hasn't been published yet.</p>
              </div>
            )}

            {!isLoading && !isError && data && (
              <div className={styles.prose} dangerouslySetInnerHTML={{ __html: data.content ?? '' }} />
            )}
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
