import { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { vendorBookingsApi } from '../../api';

function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function BookingMediaCard({ booking }) {
  const qc = useQueryClient();
  const photoInputRef = useRef(null);
  const videoInputRef = useRef(null);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [uploadingVideo, setUploadingVideo] = useState(false);

  const uploadPhotoMutation = useMutation({
    mutationFn: (file) => vendorBookingsApi.uploadEventPhoto(booking.booking_id, file),
    onSuccess: () => {
      toast.success('Event photo uploaded.');
      qc.invalidateQueries({ queryKey: ['vendor', 'booking-media'] });
    },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to upload photo.'),
    onSettled: () => setUploadingPhoto(false),
  });

  const uploadVideoMutation = useMutation({
    mutationFn: (file) => vendorBookingsApi.uploadEventVideo(booking.booking_id, file),
    onSuccess: () => {
      toast.success('Event video uploaded.');
      qc.invalidateQueries({ queryKey: ['vendor', 'booking-media'] });
    },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to upload video.'),
    onSettled: () => setUploadingVideo(false),
  });

  const handlePhotoChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingPhoto(true);
    uploadPhotoMutation.mutate(file);
    e.target.value = '';
  };

  const handleVideoChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingVideo(true);
    uploadVideoMutation.mutate(file);
    e.target.value = '';
  };

  return (
    <div className="admin-card" style={{ padding: '16px 18px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--text-primary)' }}>{booking.event_title}</div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>{booking.customer_name ?? '—'}</div>
          <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{booking.customer_email ?? '—'}</div>
        </div>
        <span className={`badge badge-${booking.booking_status === 'completed' ? 'success' : 'neutral'}`}>
          <span className="badge-dot" />
          {booking.booking_status?.replace(/_/g, ' ')}
        </span>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 12, fontSize: 12, color: 'var(--text-tertiary)' }}>
        <span>{formatDate(booking.scheduled_date)} · Booking #{booking.booking_number}</span>
        <span>📷 {booking.image_count} · 🎞️ {booking.video_count}</span>
      </div>

      <div style={{ marginTop: 14, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        {booking.can_upload ? (
          <>
            <input ref={photoInputRef} type="file" accept="image/*" hidden onChange={handlePhotoChange} />
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={uploadingPhoto}
              onClick={() => photoInputRef.current?.click()}
            >
              {uploadingPhoto ? 'Uploading…' : '📷 Upload Photo'}
            </button>

            <input ref={videoInputRef} type="file" accept="video/*" hidden onChange={handleVideoChange} />
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={uploadingVideo}
              onClick={() => videoInputRef.current?.click()}
            >
              {uploadingVideo ? 'Uploading…' : '🎞️ Upload Video'}
            </button>
          </>
        ) : (
          <p style={{ margin: 0, fontSize: 12, color: 'var(--text-tertiary)' }}>
            Media upload unlocks once this booking is confirmed.
          </p>
        )}
      </div>
    </div>
  );
}

export default function VendorMultimediaPage() {
  const { data: bookings = [], isLoading } = useQuery({
    queryKey: ['vendor', 'booking-media'],
    queryFn: () => vendorBookingsApi.listMedia(),
  });

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Multimedia</h1>
          <p>Upload event photos and videos for the bookings you've been assigned to.</p>
        </div>
      </div>

      {isLoading ? (
        <div style={{ display: 'grid', gap: 12 }}>
          {[0, 1, 2].map((i) => <div key={i} className="skeleton skeleton-card" style={{ height: 140 }} />)}
        </div>
      ) : !bookings.length ? (
        <div className="admin-empty">
          <div className="admin-empty-title">No assigned bookings yet</div>
          <p style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>Once you're assigned to a booking, it'll show up here for media uploads.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: 14 }}>
          {bookings.map((b) => (
            <BookingMediaCard key={b.booking_id} booking={b} />
          ))}
        </div>
      )}
    </div>
  );
}
