import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { bookingsApi, mediaApi } from '../../api';
import { formatDate } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import { SkeletonTable } from '../../components/ui/Skeleton';
import EmptyState from '../../components/ui/EmptyState';
import Modal from '../../components/ui/Modal';

function BookingMediaGrid({ booking }) {
  const { data: images = [], isLoading: loadingImages } = useQuery({
    queryKey: ['booking-media', 'images', booking.booking_id],
    queryFn: () => mediaApi.listImagesForEntity(booking.booking_id, 'booking'),
  });
  const { data: videos = [], isLoading: loadingVideos } = useQuery({
    queryKey: ['booking-media', 'videos', booking.booking_id],
    queryFn: () => mediaApi.listVideosForEntity(booking.booking_id, 'booking'),
  });

  if (loadingImages || loadingVideos) {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 10 }}>
        {[0, 1, 2].map((i) => <div key={i} className="skeleton" style={{ height: 100, borderRadius: 10 }} />)}
      </div>
    );
  }

  if (!images.length && !videos.length) {
    return <p style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>No media uploaded yet.</p>;
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 10 }}>
      {images.map((img) => (
        <div key={img.id} style={{ borderRadius: 10, overflow: 'hidden', border: '1px solid var(--border-subtle)', aspectRatio: '4/3', background: 'var(--bg-base)' }}>
          <img src={img.url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} onError={(e) => { e.target.style.display = 'none'; }} />
        </div>
      ))}
      {videos.map((vid) => (
        <div key={vid.id} style={{ borderRadius: 10, overflow: 'hidden', border: '1px solid var(--border-subtle)', aspectRatio: '4/3', background: '#000' }}>
          <video src={vid.url} controls style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        </div>
      ))}
    </div>
  );
}

function BookingMediaCard({ booking, onOpen }) {
  return (
    <div className="admin-card" style={{ cursor: 'pointer', overflow: 'hidden' }} onClick={() => onOpen(booking)}>
      <div style={{ aspectRatio: '16/9', background: 'var(--bg-base)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {booking.thumbnail_url ? (
          <img src={booking.thumbnail_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        ) : (
          <span style={{ fontSize: 32, color: 'var(--text-tertiary)' }}>🎬</span>
        )}
      </div>
      <div style={{ padding: '14px 16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
          <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-primary)' }}>{booking.event_title}</div>
          <StatusBadge status={booking.booking_status?.toLowerCase()} />
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>{booking.customer_name ?? '—'}</div>
        <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{booking.customer_email ?? '—'}</div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 10, fontSize: 12, color: 'var(--text-tertiary)' }}>
          <span>{formatDate(booking.scheduled_date)}</span>
          <span>📷 {booking.image_count} · 🎞️ {booking.video_count}</span>
        </div>
      </div>
    </div>
  );
}

export default function MultimediaPage() {
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(null);

  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'booking-media', page],
    queryFn: () => bookingsApi.listMedia({ page, page_size: 20 }),
  });

  const items = data?.items ?? [];

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Multimedia</h1>
          <p>Event photos and videos uploaded by vendors after completed bookings</p>
        </div>
      </div>

      {isLoading ? (
        <SkeletonTable rows={6} cols={4} />
      ) : !items.length ? (
        <EmptyState
          title="No event media yet"
          message="Once vendors upload photos or videos for completed bookings, they'll show up here."
        />
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16 }}>
            {items.map((b) => (
              <BookingMediaCard key={b.booking_id} booking={b} onOpen={setSelected} />
            ))}
          </div>

          {data?.pages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 20 }}>
              <button className="btn btn-secondary btn-sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</button>
              <span style={{ alignSelf: 'center', fontSize: 13, color: 'var(--text-tertiary)' }}>Page {page} of {data.pages}</span>
              <button className="btn btn-secondary btn-sm" disabled={page >= data.pages} onClick={() => setPage((p) => p + 1)}>Next</button>
            </div>
          )}
        </>
      )}

      <Modal open={!!selected} onClose={() => setSelected(null)} title={selected?.event_title ?? ''}>
        {selected && (
          <div style={{ padding: '0 4px' }}>
            <div style={{ marginBottom: 14, fontSize: 13, color: 'var(--text-secondary)' }}>
              <div><strong>{selected.customer_name ?? '—'}</strong> · {selected.customer_email ?? '—'}</div>
              <div style={{ color: 'var(--text-tertiary)' }}>{formatDate(selected.scheduled_date)} · Booking #{selected.booking_number}</div>
            </div>
            <BookingMediaGrid booking={selected} />
          </div>
        )}
      </Modal>
    </div>
  );
}
