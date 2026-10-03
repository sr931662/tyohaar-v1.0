import { useRef, useState } from 'react';
import { toast } from 'sonner';
import { vendorMediaApi } from '../api';

/**
 * File field that supports both pasting a URL and uploading a local file
 * (image or document, depending on `accept`). Uploading replaces the URL
 * text with the returned Cloudinary URL.
 *
 * With `multiple`, several files can be picked at once; every uploaded URL is
 * handed to `onUploaded` so a gallery can keep them all instead of only the
 * last one. `onChange` still receives the final URL for single-value callers.
 */
export default function ImageUploadField({
  value,
  onChange,
  onUploaded,
  multiple = false,
  usage,
  placeholder = 'https://...',
  accept = 'image/*',
  label = 'Upload',
}) {
  const fileInputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const showImagePreview = accept.includes('image');

  const handleFile = async (e) => {
    const files = Array.from(e.target.files ?? []);
    e.target.value = ''; // allow re-selecting the same file later
    if (!files.length) return;

    setUploading(true);
    try {
      const urls = [];
      for (const file of files) {
        const uploaded = await vendorMediaApi.uploadImage(file, usage);
        urls.push(uploaded.url);
      }
      if (onUploaded) {
        onUploaded(urls);
      } else {
        onChange(urls[urls.length - 1]);
        toast.success(urls.length > 1 ? `${urls.length} files uploaded.` : 'File uploaded.');
      }
    } catch (err) {
      const msg = err?.response?.data?.detail ?? err?.response?.data?.message ?? 'Upload failed.';
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
          {uploading ? 'Uploading…' : label}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          style={{ display: 'none' }}
          onChange={handleFile}
        />
      </div>
      {value && showImagePreview && (
        <div style={{ marginTop: 8 }}>
          <img
            src={value}
            alt=""
            style={{ maxHeight: 100, borderRadius: 8, border: '1px solid rgba(244,235,220,0.13)' }}
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
          />
        </div>
      )}
      {value && !showImagePreview && (
        <div style={{ marginTop: 8 }}>
          <a href={value} target="_blank" rel="noopener noreferrer" style={{ fontSize: 12 }}>
            View uploaded file
          </a>
        </div>
      )}
    </div>
  );
}
