// Triggers a browser download for an in-memory Blob. Shared by the admin
// CMS import/export page and the vendor packages import/export UI.
export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// Parses the filename out of a Content-Disposition response header, falling
// back to `fallback` if the header is missing/malformed.
export function filenameFromContentDisposition(headerValue, fallback) {
  return /filename="([^"]+)"/.exec(headerValue ?? '')?.[1] ?? fallback;
}
