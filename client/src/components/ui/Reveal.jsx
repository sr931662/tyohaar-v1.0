import { motion } from 'framer-motion';
import { fadeUp, inView } from '../../lib/motion';

/**
 * Reveal — lightweight scroll-reveal wrapper around framer-motion.
 * Defaults to a fade-up; pass any variants object to change it.
 *
 * <Reveal as="li" variants={bloom} delay={0.1}>…</Reveal>
 */
export default function Reveal({
  children,
  as = 'div',
  variants = fadeUp,
  delay = 0,
  className = '',
  ...rest
}) {
  const MotionTag = motion[as] || motion.div;
  return (
    <MotionTag
      className={className}
      variants={variants}
      initial="hidden"
      whileInView="show"
      viewport={inView}
      transition={delay ? { delay } : undefined}
      {...rest}
    >
      {children}
    </MotionTag>
  );
}
