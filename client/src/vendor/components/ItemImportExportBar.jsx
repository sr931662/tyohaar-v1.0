import { useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { vendorItemIoApi } from '../api';
import { downloadBlob } from '../../lib/downloadBlob';

/**
 * Compact bulk import/export toolbar shared by CommonItemsModal (vendor-wide,
 * no packageId) and PackageItemsModal (scoped to one packageId), and reused
 * unchanged for services via the `entityApi` prop (defaults to items' API).
 * Import is upsert-by-name on the backend — re-uploading a corrected file
 * fixes rows instead of duplicating them.
 */
export default function ItemImportExportBar({ scope, packageId, disabled, invalidateKey, entityApi = vendorItemIoApi, entityLabel = 'items' }) {
  const qc = useQueryClient();
  const fileRef = useRef(null);
  const [format, setFormat] = useState('xlsx');
  const [importing, setImporting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [lastResult, setLastResult] = useState(null);

  if (disabled) return null;

  const api = scope === 'common'
    ? {
        template: () => entityApi.getCommonItemsTemplate(format),
        doImport: (formData) => entityApi.importCommonItems(formData),
        doExport: () => entityApi.exportCommonItems(format),
      }
    : {
        template: () => entityApi.getPackageItemsTemplate(packageId, format),
        doImport: (formData) => entityApi.importPackageItems(packageId, formData),
        doExport: () => entityApi.exportPackageItems(packageId, format),
      };

  const handleTemplate = async () => {
    try {
      const blob = await api.template();
      downloadBlob(blob, `${entityLabel}_template.${format}`);
    } catch {
      toast.error('Failed to download template.');
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const { blob, filename } = await api.doExport();
      downloadBlob(blob, filename);
    } catch {
      toast.error('Export failed.');
    } finally {
      setExporting(false);
    }
  };

  const handleFilePicked = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    setImporting(true);
    setLastResult(null);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const result = await api.doImport(formData);
      setLastResult(result);
      const summary = `${result.created} created, ${result.updated} updated${result.errors ? `, ${result.errors} error${result.errors === 1 ? '' : 's'}` : ''}.`;
      if (result.errors > 0) toast.warning(summary);
      else toast.success(summary);
      if (invalidateKey) qc.invalidateQueries(invalidateKey);
    } catch (err) {
      toast.error(err?.response?.data?.detail ?? 'Import failed.');
    } finally {
      setImporting(false);
    }
  };

  const errorRows = lastResult?.row_results?.filter((r) => r.action === 'error') ?? [];

  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <select
          className="admin-input"
          style={{ width: 90, height: 32, fontSize: 12 }}
          value={format}
          onChange={(e) => setFormat(e.target.value)}
        >
          <option value="xlsx">XLSX</option>
          <option value="csv">CSV</option>
        </select>
        <button type="button" className="btn btn-secondary btn-sm" onClick={handleTemplate}>Template</button>
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => fileRef.current?.click()} disabled={importing}>
          {importing ? 'Importing…' : 'Import'}
        </button>
        <input ref={fileRef} type="file" accept=".csv,.xlsx" hidden onChange={handleFilePicked} />
        <button type="button" className="btn btn-secondary btn-sm" onClick={handleExport} disabled={exporting}>
          {exporting ? 'Exporting…' : 'Export'}
        </button>
      </div>
      {errorRows.length > 0 && (
        <p style={{ margin: '6px 0 0', fontSize: 11, color: '#ef4444' }}>
          {errorRows.slice(0, 3).map((r) => `Row ${r.row}${r.name ? ` (${r.name})` : ''}: ${r.error}`).join('; ')}
          {errorRows.length > 3 ? ` … and ${errorRows.length - 3} more` : ''}
        </p>
      )}
    </div>
  );
}
