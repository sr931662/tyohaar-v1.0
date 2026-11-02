// Balloon colours on a booking, shared by the admin and vendor booking pages.
// With a proportion mix (balloon_color_ratios, one % per colour) it shows each
// share and a bar of the whole mix; without one, just the swatches (even mix).
export default function BalloonMix({ colors = [], ratios }) {
  const shares = Array.isArray(ratios) && ratios.length === colors.length && colors.length > 1 ? ratios : null;
  const swatch = (c) => ({ width: 16, height: 16, borderRadius: '50%', background: c, border: '1px solid rgba(0,0,0,0.15)', display: 'inline-block', flexShrink: 0 });
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        {colors.map((c, i) => (
          <span key={i} title={c} style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
            <span style={swatch(c)} />
            {shares && <span style={{ fontSize: 12.5, fontWeight: 600 }}>{shares[i]}%</span>}
          </span>
        ))}
      </div>
      {shares && (
        <div
          role="img"
          aria-label={`Balloon mix: ${colors.map((c, i) => `${c} ${shares[i]}%`).join(', ')}`}
          style={{ display: 'flex', height: 10, borderRadius: 999, overflow: 'hidden', border: '1px solid rgba(0,0,0,0.12)', maxWidth: 260 }}
        >
          {colors.map((c, i) => <span key={i} style={{ flex: shares[i], background: c }} />)}
        </div>
      )}
    </div>
  );
}
