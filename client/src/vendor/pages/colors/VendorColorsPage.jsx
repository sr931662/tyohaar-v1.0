import { useQuery } from '@tanstack/react-query';
import { vendorColorsApi } from '../../api';
import { SkeletonTable } from '../../../admin/components/ui/Skeleton';
import EmptyState from '../../../admin/components/ui/EmptyState';

/**
 * The balloon colours customers can currently choose from. Read-only for
 * vendors: Tyohaar manages the palette, and a booking's colours always come
 * from it — so this is the list your team should be able to supply.
 */
export default function VendorColorsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['vendor-balloon-colors'],
    queryFn: vendorColorsApi.list,
  });
  const colors = data ?? [];
  const { data: finishData } = useQuery({ queryKey: ['vendor-balloon-finishes'], queryFn: vendorColorsApi.listFinishes });
  const finishes = finishData ?? [];

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Balloon Colours</h1>
          <p style={{ color: 'var(--text-secondary)' }}>
            Customers pick 1 to 4 of these when they book balloon décor. Make sure you can supply them.
          </p>
        </div>
      </div>

      {isLoading ? <SkeletonTable rows={6} cols={3} /> : isError ? (
        <EmptyState title="Couldn't load the colour palette" message="Please try again." />
      ) : !colors.length ? (
        <EmptyState title="No colours are offered right now" />
      ) : (
        <div className="admin-card" style={{ padding: 18 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 16 }}>
            {colors.map((c) => (
              <div key={c.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
                <span
                  aria-hidden="true"
                  style={{ width: 52, height: 52, borderRadius: '50%', background: c.hex_code, border: '1px solid rgba(0,0,0,0.15)' }}
                />
                <b style={{ fontSize: 13, textAlign: 'center' }}>{c.name}</b>
                <code style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{c.hex_code}</code>
              </div>
            ))}
          </div>
        </div>
      )}

      {finishes.length > 0 && (
        <div className="admin-card" style={{ padding: 18, marginTop: 16 }}>
          <h3 style={{ fontSize: 14, margin: '0 0 10px' }}>Finishes customers can choose</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {finishes.map((f) => <span key={f.id} className="badge badge-info">{f.name}</span>)}
          </div>
        </div>
      )}
    </div>
  );
}
