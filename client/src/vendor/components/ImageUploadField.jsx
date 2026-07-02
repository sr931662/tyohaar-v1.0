import { useRef, useState } from 'react';
import { toast } from 'sonner';
import { vendorMediaApi } from '../api';

/**
 * Cover-image field that supports both pasting a URL and uploading a local
 * file. Uploading replaces the URL text with the returned Cloudinary URL.
 */
export default function ImageUploadField({ value, onChange, usage, placeholder = 'https://...' }) {
  const fileInputRef = useRef(null);
  const [uploading, setUploading] = useState(false);

  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = ''; // allow re-selecting the same file later
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file.');
      return;
    }

    setUploading(true);
    try {
      const image = await vendorMediaApi.uploadImage(file, usage);
      onChange(image.url);
      toast.success('Image uploaded.');
    } catch (err) {
      const msg = err?.response?.data?.detail ?? err?.response?.data?.message ?? 'Image upload failed.';
      toast.error(msg);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          className="admin-input"
          type="url"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          style={{ flex: 1 }}
          disabled={uploading}
        />
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? 'Uploading…' : 'Upload'}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          style={{ display: 'none' }}
          onChange={handleFile}
        />
      </div>
      {value && (
        <div style={{ marginTop: 8 }}>
          <img
            src={value}
            alt=""
            style={{ maxHeight: 100, borderRadius: 8, border: '1px solid rgba(244,235,220,0.13)' }}
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
          />
        </div>
      )}
    </div>
  );
}
