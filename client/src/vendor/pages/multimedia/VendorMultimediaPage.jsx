import { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { vendorBookingsApi, vendorMediaApi } from '../../api';
import Modal from '../../../admin/components/ui/Modal';

function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function MediaTile({ item, isVideo, bookingId, qc }) {
  const [editing, setEditing] = useState(false);
  const [caption, setCaption] = useState(isVideo ? (item.title ?? '') : (item.alt_text ?? ''));
  const [confirmDelete, setConfirmDelete] = useState(false);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['vendor', 'booking-media-gallery', isVideo ? 'videos' : 'images', bookingId] });
    qc.invalidateQueries({ queryKey: ['vendor', 'booking-media'] });
  };

  const updateMutation = useMutation({
    mutationFn: (body) => (isVideo ? vendorMediaApi.updateVideo(item.id, body) : vendorMediaApi.updateImage(item.id, body)),
    onSuccess: () => {
      toast.success('Caption updated.');
      setEditing(false);
      invalidate();
    },
    onError: () => toast.error('Failed to update caption.'),
  });

  const deleteMutation = useMutation({
    mutationFn: () => (isVideo ? vendorMediaApi.deleteVideo(item.id) : vendorMediaApi.deleteImage(item.id)),
    onSuccess: () => {
      toast.success(isVideo ? 'Video removed.' : 'Photo removed.');
      invalidate();
    },
    onError: () => toast.error('Failed to remove media.'),
  });

  const handleSaveCaption = () => {
    const body = isVideo ? { title: caption.trim() || undefined } : { alt_text: caption.trim() || undefined };
    updateMutation.mutate(body);
  };

  return (
    <div style={{ borderRadius: 10, overflow: 'hidden', border: '1px solid var(--border-subtle)', background: isVideo ? '#000' : 'var(--bg-base)' }}>
      <div style={{ position: 'relative', aspectRatio: '4/3' }}>
        {isVideo ? (
          <video src={item.url} controls style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        ) : (
          <img src={item.url} alt={item.alt_text ?? ''} style={{ width: '100%', height: '100%', objectFit: 'cover' }} onError={(e) => { e.target.style.display = 'none'; }} />
        )}
        <div style={{ position: 'absolute', top: 4, right: 4, display: 'flex', gap: 4 }}>
          <button
            type="button"
            onClick={() => setEditing((v) => !v)}
            title="Edit caption"
            style={{ width: 24, height: 24, borderRadius: '50%', border: 'none', background: 'rgba(0,0,0,0.6)', color: '#fff', cursor: 'pointer', fontSize: 12 }}
          >✏️</button>
          {confirmDelete ? (
            <button
              type="button"
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
              title="Confirm delete"
              style={{ height: 24, borderRadius: 12, border: 'none', background: '#ef4444', color: '#fff', cursor: 'pointer', fontSize: 11, padding: '0 8px' }}
            >{deleteMutation.isPending ? '…' : 'Confirm'}</button>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              onBlur={() => setConfirmDelete(false)}
              title="Delete"
              style={{ width: 24, height: 24, borderRadius: '50%', border: 'none', background: 'rgba(0,0,0,0.6)', color: '#fff', cursor: 'pointer', fontSize: 12 }}
            >🗑</button>
          )}
        </div>
      </div>
      {editing ? (
        <div style={{ display: 'flex', gap: 4, padding: 6, background: 'var(--bg-subtle)' }}>
          <input
            className="admin-input"
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            placeholder="Caption"
            style={{ flex: 1, fontSize: 12, padding: '4px 6px' }}
          />
          <button className="btn btn-primary btn-sm" disabled={updateMutation.isPending} onClick={handleSaveCaption}>
            {updateMutation.isPending ? '…' : 'Save'}
          </button>
        </div>
      ) : (caption && (
        <div style={{ padding: '4px 8px', fontSize: 11, color: 'var(--text-tertiary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {caption}
        </div>
      ))}
    </div>
  );
}

function BookingMediaGallery({ booking }) {
  const qc = useQueryClient();
  const { data: images = [], isLoading: loadingImages } = useQuery({
    queryKey: ['vendor', 'booking-media-gallery', 'images', booking.booking_id],
    queryFn: () => vendorMediaApi.listImagesForEntity(booking.booking_id, 'booking'),
  });
  const { data: videos = [], isLoading: loadingVideos } = useQuery({
    queryKey: ['vendor', 'booking-media-gallery', 'videos', booking.booking_id],
    queryFn: () => vendorMediaApi.listVideosForEntity(booking.booking_id, 'booking'),
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
        <MediaTile key={img.id} item={img} isVideo={false} bookingId={booking.booking_id} qc={qc} />
      ))}
      {videos.map((vid) => (
        <MediaTile key={vid.id} item={vid} isVideo bookingId={booking.booking_id} qc={qc} />
      ))}
    </div>
  );
}

function BookingMediaCard({ booking, onOpenGallery }) {
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
      qc.invalidateQueries({ queryKey: ['vendor', 'booking-media-gallery', 'images', booking.booking_id] });
    },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to upload photo.'),
    onSettled: () => setUploadingPhoto(false),
  });

  const uploadVideoMutation = useMutation({
    mutationFn: (file) => vendorBookingsApi.uploadEventVideo(booking.booking_id, file),
    onSuccess: () => {
      toast.success('Event video uploaded.');
      qc.invalidateQueries({ queryKey: ['vendor', 'booking-media'] });
      qc.invalidateQueries({ queryKey: ['vendor', 'booking-media-gallery', 'videos', booking.booking_id] });
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
    <div
      className="admin-card"
      style={{ padding: '16px 18px', cursor: 'pointer' }}
      onClick={() => onOpenGallery(booking)}
    >
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

      <div style={{ marginTop: 14, display: 'flex', gap: 10, flexWrap: 'wrap' }} onClick={(e) => e.stopPropagation()}>
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
  const [selected, setSelected] = useState(null);

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
            <BookingMediaCard key={b.booking_id} booking={b} onOpenGallery={setSelected} />
          ))}
        </div>
      )}

      <Modal open={!!selected} onClose={() => setSelected(null)} title={selected?.event_title ?? ''}>
        {selected && (
          <div style={{ padding: '0 4px' }}>
            <div style={{ marginBottom: 14, fontSize: 13, color: 'var(--text-secondary)' }}>
              <div><strong>{selected.customer_name ?? '—'}</strong> · {selected.customer_email ?? '—'}</div>
              <div style={{ color: 'var(--text-tertiary)' }}>{formatDate(selected.scheduled_date)} · Booking #{selected.booking_number}</div>
            </div>
            <BookingMediaGallery booking={selected} />
          </div>
        )}
      </Modal>
    </div>
  );
}
