import styles from './AppMockup.module.css';

export default function AppMockup() {
  return (
    <div className={styles.phone} aria-hidden="true">
      {/* Dynamic island / notch */}
      <div className={styles.island} />

      <div className={styles.screen}>
        {/* App header */}
        <div className={styles.header}>
          <span className={styles.appName}>Tyohaar</span>
          <span className={styles.avatar}>R</span>
        </div>

        {/* Active occasion */}
        <div className={styles.occasionRow}>
          <span className={styles.occasionChip}>
            <span className={styles.dot} />
            Birthday · 40 guests
          </span>
          <span className={styles.changeLink}>Change</span>
        </div>

        {/* Package selection label */}
        <p className={styles.label}>Choose a package</p>

        {/* Featured package */}
        <div className={`${styles.pkg} ${styles.pkgFeatured}`}>
          <div className={styles.pkgHead}>
            <span className={styles.pkgName}>Celebration Pack</span>
            <span className={styles.pkgBadge}>Popular</span>
          </div>
          <span className={styles.pkgPrice}>from ₹75,000</span>
          <div className={styles.pkgTags}>
            <span>Décor</span>
            <span>Catering</span>
            <span>Photo</span>
            <span>+6 more</span>
          </div>
        </div>

        {/* Secondary package */}
        <div className={styles.pkg}>
          <div className={styles.pkgHead}>
            <span className={styles.pkgName}>Essentials Pack</span>
          </div>
          <span className={styles.pkgPrice}>from ₹35,000</span>
          <div className={styles.pkgTags}>
            <span>Décor</span>
            <span>Catering</span>
            <span>+3 more</span>
          </div>
        </div>

        {/* Venue */}
        <div className={styles.venue}>
          <span className={styles.venuePin}>⊙</span>
          <span className={styles.venueText}>Your home · New Delhi</span>
        </div>

        {/* CTA */}
        <div className={styles.cta}>
          Customize &amp; Book
          <span className={styles.ctaArrow}>→</span>
        </div>
      </div>
    </div>
  );
}
