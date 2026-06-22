/**
 * HangingLights — cascading beaded fairy-light strings that hang from a top edge.
 * Inlines the raw SVG so `fill="currentColor"` inherits color/opacity from CSS.
 * The source SVG has no viewBox (hardcoded 832×1280), so we add one and make it
 * fluid: width:100% with the viewBox driving the height, anchored to the top.
 */
import raw from '../../assets/ornaments/elegant-hanging-fairy-light-strings--cascading-ver (1).svg?raw';

const svg = raw
  .replace('<svg', '<svg viewBox="0 0 832 1280" preserveAspectRatio="xMidYMin meet"')
  .replace(/\swidth="832"/, ' width="100%"')
  .replace(/\sheight="1280"/, '');

export default function HangingLights({ flipped = false, className = '', style = {} }) {
  return (
    <span
      aria-hidden="true"
      className={className}
      style={{ transform: flipped ? 'scaleX(-1)' : undefined, ...style }}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
