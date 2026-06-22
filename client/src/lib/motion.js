// Shared framer-motion variants & helpers.
// Keep entrances short (0.5–0.8s) and purposeful — celebration is a moment, not a loop.

export const EASE = [0.2, 0.8, 0.2, 1];
export const EASE_SOFT = [0.34, 1.2, 0.4, 1];

// Reveal upward (the default "bloom-in")
export const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.7, ease: EASE },
  },
};

export const fadeIn = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.8, ease: EASE } },
};

// Gentle scale "bloom" — used for cards / emblems
export const bloom = {
  hidden: { opacity: 0, scale: 0.94, y: 18 },
  show: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { duration: 0.6, ease: EASE_SOFT },
  },
};

export const fadeRight = {
  hidden: { opacity: 0, x: -36 },
  show: { opacity: 1, x: 0, transition: { duration: 0.7, ease: EASE } },
};

export const fadeLeft = {
  hidden: { opacity: 0, x: 36 },
  show: { opacity: 1, x: 0, transition: { duration: 0.7, ease: EASE } },
};

// Parent container that staggers its children
export const stagger = (staggerChildren = 0.09, delayChildren = 0) => ({
  hidden: {},
  show: {
    transition: { staggerChildren, delayChildren },
  },
});

// Shared viewport config for whileInView
export const inView = { once: true, amount: 0.2, margin: '0px 0px -80px 0px' };

// Tactile hover/tap presets for interactive cards & buttons
export const liftHover = {
  rest: { y: 0 },
  hover: { y: -6, transition: { duration: 0.3, ease: EASE } },
  tap: { scale: 0.98 },
};
