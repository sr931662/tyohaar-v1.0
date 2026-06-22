import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence, useScroll, useMotionValueEvent } from 'framer-motion';
import Logo from '../ui/Logo.jsx';
import Button from '../ui/Button.jsx';
import ThemeToggle from '../ui/ThemeToggle.jsx';
import { navLinks } from '../../data/nav.js';
import styles from './Navbar.module.css';

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const { scrollY } = useScroll();

  useMotionValueEvent(scrollY, 'change', (y) => setScrolled(y > 24));

  // Lock body scroll while the mobile menu is open
  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [open]);

  return (
    <>
    <motion.header
      className={`${styles.nav} ${scrolled ? styles.scrolled : ''}`}
      initial={{ y: -80, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: [0.2, 0.8, 0.2, 1] }}
    >
      <div className={`ty-container ${styles.inner}`}>
        <Logo />

        <nav className={styles.links} aria-label="Primary">
          {navLinks.map((l) => (
            <a key={l.href} href={l.href} className={styles.link}>
              {l.label}
            </a>
          ))}
        </nav>

        <div className={styles.actions}>
          <ThemeToggle className={styles.deskToggle} />
          <Button href="#download" size="md" className={styles.cta}>
            Start a celebration
          </Button>
          <button
            className={styles.burger}
            onClick={() => setOpen((o) => !o)}
            aria-label="Menu"
            aria-expanded={open}
          >
            <span data-open={open} />
            <span data-open={open} />
            <span data-open={open} />
          </button>
        </div>
      </div>
    </motion.header>

    {/* Rendered in a portal on <body> so the menu's position:fixed resolves
        against the viewport — NOT the scrolled header, whose backdrop-filter
        would otherwise become its containing block and collapse the overlay. */}
    {createPortal(
      <AnimatePresence>
        {open && (
          <>
            <motion.div
              className={styles.scrim}
              onClick={() => setOpen(false)}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            />
            <motion.nav
              className={styles.sheet}
              aria-label="Mobile"
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', stiffness: 360, damping: 38 }}
            >
              <div className={styles.sheetTop}>
                <Logo />
                <ThemeToggle />
              </div>
              <ul className={styles.sheetLinks}>
                {navLinks.map((l, i) => (
                  <motion.li
                    key={l.href}
                    initial={{ opacity: 0, x: 24 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.08 + i * 0.06 }}
                  >
                    <a href={l.href} onClick={() => setOpen(false)}>
                      {l.label}
                    </a>
                  </motion.li>
                ))}
              </ul>
              <Button href="#download" size="lg" full onClick={() => setOpen(false)}>
                Start a celebration
              </Button>
            </motion.nav>
          </>
        )}
      </AnimatePresence>,
      document.body
    )}
    </>
  );
}
