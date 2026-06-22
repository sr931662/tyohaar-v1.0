/**
 * HeroOrnament — premium celebration paisley flourish.
 * Inlines the raw SVG so `fill="currentColor"` inherits color/opacity from CSS.
 * The artwork natively radiates toward the bottom-left (south-west); use the
 * `flipped` / `flippedV` props to re-aim it into the correct corner.
 */
import raw from '../../assets/ornaments/premium-celebration-themed-ornamental-svg--elegant.svg?raw';

// The source SVG ships with no viewBox and hardcoded 1024×1024 dimensions, so it
// renders at full intrinsic size and ignores CSS sizing. Add a square viewBox and
// make it fluid (width:100%, height driven by the viewBox ratio) so it scales to
// whatever box the corner gives it.
const svg = raw
  .replace('<svg', '<svg viewBox="0 0 1024 1024" preserveAspectRatio="xMidYMid meet"')
  .replace(/\swidth="1024"/, ' width="100%"')
  .replace(/\sheight="1024"/, '');

export default function HeroOrnament({ flipped = false, flippedV = false, className = '', style = {} }) {
  const t = [flipped && 'scaleX(-1)', flippedV && 'scaleY(-1)'].filter(Boolean).join(' ');
  return (
    <span
      aria-hidden="true"
      className={className}
      style={{ transform: t || undefined, ...style }}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
