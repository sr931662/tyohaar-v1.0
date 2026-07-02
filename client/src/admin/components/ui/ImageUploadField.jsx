import { useRef, useState } from 'react';
import { toast } from 'sonner';
import { mediaApi } from '../../api';

/**
 * Image field that supports both pasting a URL and uploading a local file.
 * Uploading replaces the URL text with the returned Cloudinary URL.
 */
export default function ImageUploadField({ value, onChange, usage, placeholder = 'https://...' }) {
  const fileInputRef = useRef(null);
  const [uploading, setUploading] = useState(false);

  const handleFile = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file.');
      return;
    }

    setUploading(true);
    try {
      const image = await mediaApi.uploadImage(file, usage);
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
          className="form-control"
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
            style={{ maxHeight: 80, borderRadius: 8, border: '1px solid var(--border-color, #e5e7eb)' }}
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
          />
        </div>
      )}
    </div>
  );
}
