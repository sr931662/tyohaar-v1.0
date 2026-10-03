import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { vendorPackagesApi } from '../../api';
import ImageUploadField from '../../components/ImageUploadField';

// Additional images beyond the single cover image — customers swipe through
// cover-first, then these, on the package detail page.
//
// Used both inside the package form (so a vendor adds every photo in one
// place) and on its own in the Photos modal. Every control is type="button"
// and the delete confirmation is inline rather than a nested dialog, because
// this renders inside the package <form> and must never submit it.
export default function PackageGalleryEditor({ pkgId, compact = false }) {
  const qc = useQueryClient();
  const [uploadUrl, setUploadUrl] = useState('');
  const [confirmingId, setConfirmingId] = useState(null);

  const { data: gallery = [], isLoading } = useQuery({
    queryKey: ['pkg-gallery', pkgId],
    queryFn: () => vendorPackagesApi.listGallery(pkgId),
  });

  const invalidate = () => qc.invalidateQueries(['pkg-gallery', pkgId]);

  const addMutation = useMutation({
    mutationFn: (fileUrl) => vendorPackagesApi.addGalleryItem(pkgId, { file_url: fileUrl }),
    onSuccess: () => { invalidate(); setUploadUrl(''); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to add image.'),
  });

  const deleteMutation = useMutation({
    mutationFn: (galleryId) => vendorPackagesApi.deleteGalleryItem(pkgId, galleryId),
    onSuccess: () => { toast.success('Image removed.'); invalidate(); setConfirmingId(null); },
    onError: () => toast.error('Failed to remove image.'),
  });

  // Files picked through the upload button are added to the gallery straight
  // away — making the vendor press "+ Add" once per photo is the reason this
  // felt like a single-image field.
  const handleUploaded = async (urls) => {
    for (const url of urls) {
      try {
        await addMutation.mutateAsync(url);
      } catch {
        return; // mutation's onError already surfaced it
      }
    }
    toast.success(urls.length > 1 ? `${urls.length} photos added.` : 'Photo added.');
  };

  const tile = compact ? 120 : 140;

  return (
    <div>
      {isLoading ? (
        <div style={{ display: 'grid', gridTemplateColumns: `repeat(auto-fill, minmax(${tile}px, 1fr))`, gap: 10, marginBottom: 14 }}>
          {[0, 1, 2].map((i) => <div key={i} className="skeleton" style={{ height: 100, borderRadius: 10 }} />)}
        </div>
      ) : gallery.length > 0 ? (
        <div style={{ display: 'grid', gridTemplateColumns: `repeat(auto-fill, minmax(${tile}px, 1fr))`, gap: 10, marginBottom: 14 }}>
          {gallery.map((item) => (
            <div key={item.id} style={{ position: 'relative', borderRadius: 10, overflow: 'hidden', border: '1px solid var(--border-subtle)', aspectRatio: '4/3', background: 'var(--bg-base)' }}>
              <img src={item.file_url} alt={item.caption ?? ''} style={{ width: '100%', height: '100%', objectFit: 'cover' }} onError={(e) => { e.currentTarget.style.display = 'none'; }} />
              {confirmingId === item.id ? (
                <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.62)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8, padding: 8, textAlign: 'center' }}>
                  <span style={{ fontSize: 12, color: '#fff' }}>Remove this photo?</span>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button
                      type="button"
                      className="btn btn-sm"
                      style={{ background: '#ef4444', border: 'none', color: '#fff' }}
                      disabled={deleteMutation.isPending}
                      onClick={() => deleteMutation.mutate(item.id)}
                    >
                      {deleteMutation.isPending ? 'Removing…' : 'Remove'}
                    </button>
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => setConfirmingId(null)}>Cancel</button>
                  </div>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setConfirmingId(item.id)}
                  title="Remove photo"
                  style={{ position: 'absolute', top: 5, right: 5, width: 22, height: 22, borderRadius: '50%', border: 'none', background: 'rgba(239,68,68,0.85)', color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12 }}
                >×</button>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p style={{ color: 'var(--text-tertiary)', fontSize: 13, marginBottom: 12 }}>
          No additional photos yet. Add as many as you like below — customers swipe through them.
        </p>
      )}

      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          <ImageUploadField
            value={uploadUrl}
            onChange={setUploadUrl}
            onUploaded={handleUploaded}
            multiple
            usage="package_image"
            placeholder="Image URL (https://...)"
            label="Upload photos"
          />
        </div>
        <button
          type="button"
          className="btn btn-primary"
          disabled={!uploadUrl || addMutation.isPending}
          onClick={() => addMutation.mutate(uploadUrl, {
            onSuccess: () => toast.success('Photo added.'),
          })}
        >
          {addMutation.isPending ? 'Adding…' : '+ Add'}
        </button>
      </div>
    </div>
  );
}
