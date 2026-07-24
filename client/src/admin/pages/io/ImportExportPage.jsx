import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ioApi } from '../../api';
import { formatDateTime } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import { SkeletonTable } from '../../components/ui/Skeleton';

// Must match the backend's actual column definitions (_ENTITY_COLUMNS in
// io_service.py) — entity types not recognized there would silently
// download a blank template.
const ENTITY_TYPES = [
  'vendors', 'customers', 'packages', 'package_categories', 'cities', 'states',
  'coupons', 'faqs', 'notification_templates', 'settings', 'memberships', 'vendor_services',
];

// Every entity type above now has real row-insert logic in _insert_row()
// on the backend (io_service.py) — kept as an explicit set (mirroring the
// backend's EXECUTABLE_ENTITY_TYPES) so a future entity added to the list
// above without backend wiring still shows the "validate only" warning
// instead of silently failing every row at execute time.
const EXECUTABLE_ENTITY_TYPES = new Set(ENTITY_TYPES);

// Export now covers the same entities as Import (see _fetch_export_rows
// in io_service.py) plus bookings/payments, which have no import path.
const EXPORT_ENTITY_TYPES = [
  'vendors', 'customers', 'bookings', 'payments', 'packages', 'package_categories',
  'cities', 'states', 'coupons', 'notification_templates', 'settings', 'memberships',
  'vendor_services', 'faqs',
];

const ENTITY_HINTS = {
  packages: 'To attach a package to a vendor, include a "vendor_phone" column matching that vendor\'s registered phone number. "category" matches an existing package category name (leave blank to skip). Packages import as Draft — publish them from Vendor Packages after review.',
  vendors: 'A new login account is created automatically from "phone" if one doesn\'t already exist. "vendor_type" should be one of: decorator, caterer, photographer, videographer, baker, florist, entertainer, venue, planner.',
  cities: 'Import States first — "state" must exactly match an existing state name (case-insensitive).',
  coupons: '"discount_type" must be one of: percentage, fixed_amount, fixed_price, free_service, cashback. Coupons import as Draft — publish them from Discounts after review.',
  notification_templates: '"channel" must be one of: push, sms, email, whatsapp, in_app — add one row per channel needed for the same "template_key". "notification_category" must match a known event type, e.g. booking_confirmed, payment_received.',
  memberships: '"tier" must be one of: free, silver, gold, platinum. Each tier can only exist once — importing a tier that already has a plan will fail that row.',
  vendor_services: '"vendor_phone" must match a registered vendor\'s phone number. "category" must match an existing Vendor Category name. Services import as inactive — publish them from Vendors after review.',
};

function entityLabel(entityType) {
  return entityType.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

function ImportTab() {
  const qc = useQueryClient();
  const fileRef = useRef(null);
  const [entityType, setEntityType] = useState('packages');
  const [file, setFile] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [validating, setValidating] = useState(false);

  const { data: importLogsData, isLoading: logsLoading } = useQuery({
    queryKey: ['io', 'import-logs'],
    queryFn: () => ioApi.listImportLogs(),
  });
  const logs = importLogsData?.items ?? [];

  const undoMutation = useMutation({
    mutationFn: (logId) => ioApi.undoImport(logId),
    onSuccess: (result) => {
      toast.success(result?.message ?? 'Import rolled back.');
      qc.invalidateQueries(['io', 'import-logs']);
    },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Rollback failed'),
  });

  const downloadTemplate = async () => {
    try {
      const blob = await ioApi.getTemplate(entityType);
      downloadBlob(blob, `${entityType}_template.xlsx`);
    } catch {
      toast.error('Failed to download template');
    }
  };

  const handleValidate = async () => {
    if (!file) return;
    setValidating(true);
    setValidationResult(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('entity_type', entityType);
      // Backend returns { log_id, preview: { can_proceed, total_rows, valid_rows,
      // invalid_rows, sample_errors, ... } } — flatten it so the rest of this
      // component can read plain `valid` / `total_rows` / `errors` etc. fields.
      const result = await ioApi.validateImport(formData);
      setValidationResult({
        log_id: result.log_id,
        valid: result.preview?.can_proceed ?? false,
        total_rows: result.preview?.total_rows ?? 0,
        valid_rows: result.preview?.valid_rows ?? 0,
        error_count: result.preview?.invalid_rows ?? 0,
        errors: result.preview?.sample_errors ?? [],
      });
    } catch (err) {
      toast.error(err?.response?.data?.detail ?? 'Validation failed');
    } finally {
      setValidating(false);
    }
  };

  const executeMutation = useMutation({
    mutationFn: async () => {
      // The backend re-parses the file at execute time rather than storing
      // the upload from /validate — the same file has to be resent here
      // alongside the log_id that /validate returned for it.
      const formData = new FormData();
      formData.append('file', file);
      formData.append('log_id', validationResult.log_id);
      return ioApi.executeImport(formData);
    },
    onSuccess: (result) => {
      const errorCount = result?.error_summary?.total_errors ?? 0;
      if (result?.status === 'COMPLETED') {
        toast.success(`Imported ${result.inserted_rows ?? 0} rows successfully.`);
      } else {
        toast.error(`Import finished with errors — ${result?.inserted_rows ?? 0} rows inserted, ${errorCount} failed. See history below.`);
      }
      setFile(null); setValidationResult(null);
      if (fileRef.current) fileRef.current.value = '';
      qc.invalidateQueries(['io', 'import-logs']);
    },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Import failed'),
  });

  return (
    <div className="grid-2">
      {/* Upload Panel */}
      <div>
        <div className="admin-card" style={{ marginBottom: 16 }}>
          <div className="admin-card-header"><div className="admin-card-title">Import Data</div></div>
          <div className="admin-card-body">
            <div className="form-group">
              <label className="form-label">Entity Type</label>
              <select className="form-control" value={entityType} onChange={e => { setEntityType(e.target.value); setFile(null); setValidationResult(null); }}>
                {ENTITY_TYPES.map(t => (
                  <option key={t} value={t}>
                    {entityLabel(t)}{!EXECUTABLE_ENTITY_TYPES.has(t) ? ' (validate only — import not wired up yet)' : ''}
                  </option>
                ))}
              </select>
            </div>
            {!EXECUTABLE_ENTITY_TYPES.has(entityType) ? (
              <div style={{ padding: '10px 14px', borderRadius: 8, background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)', fontSize: 12.5, color: '#f59e0b', marginBottom: 16 }}>
                You can validate a "{entityType}" file to preview row errors, but executing the import isn't implemented for this entity type yet.
              </div>
            ) : ENTITY_HINTS[entityType] && (
              <div style={{ padding: '10px 14px', borderRadius: 8, background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)', fontSize: 12.5, color: 'var(--color-info, #3b82f6)', marginBottom: 16 }}>
                {ENTITY_HINTS[entityType]}
              </div>
            )}
            <button className="btn btn-secondary btn-sm" onClick={downloadTemplate} style={{ marginBottom: 16 }}>
              Download {entityLabel(entityType)} template
            </button>
            <div className="form-group">
              <label className="form-label">Upload Excel / CSV</label>
              <input ref={fileRef} className="form-control" type="file" accept=".xlsx,.csv" onChange={e => { setFile(e.target.files[0]); setValidationResult(null); }} />
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button className="btn btn-secondary" onClick={handleValidate} disabled={!file || validating}>
                {validating ? 'Validating…' : 'Validate'}
              </button>
              <button className="btn btn-primary" onClick={() => executeMutation.mutate()} disabled={!validationResult?.valid || executeMutation.isPending}>
                {executeMutation.isPending ? 'Importing…' : 'Execute Import'}
              </button>
            </div>
          </div>
        </div>

        {validationResult && (
          <div className={`admin-card ${validationResult.valid ? '' : 'border-danger'}`}>
            <div className="admin-card-header">
              <div className="admin-card-title">Validation Result</div>
              <StatusBadge status={validationResult.valid ? 'success' : 'failed'} />
            </div>
            <div className="admin-card-body">
              <div className="detail-row"><span className="detail-label">Total Rows</span><span>{validationResult.total_rows}</span></div>
              <div className="detail-row"><span className="detail-label">Valid Rows</span><span style={{ color: 'var(--color-success)' }}>{validationResult.valid_rows}</span></div>
              <div className="detail-row"><span className="detail-label">Errors</span><span style={{ color: 'var(--color-danger)' }}>{validationResult.error_count ?? 0}</span></div>
              {validationResult.errors?.slice(0, 5).map((e, i) => (
                <div key={i} style={{ fontSize: 12, color: 'var(--color-danger)', marginTop: 4 }}>Row {e.row}: {e.message}</div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Logs */}
      <div>
        <div className="admin-card">
          <div className="admin-card-header"><div className="admin-card-title">Import History</div></div>
          <div className="admin-card-body" style={{ padding: 0 }}>
            {logsLoading ? <SkeletonTable rows={5} cols={5} /> : (
              <div className="admin-table-wrapper">
                <table className="admin-table">
                  <thead><tr><th>Type</th><th>Rows</th><th>Status</th><th>When</th><th></th></tr></thead>
                  <tbody>
                    {logs.map((log) => (
                      <tr key={log.id}>
                        <td>{log.entity_type}</td>
                        <td>{log.inserted_rows ?? 0} / {log.total_rows}</td>
                        <td><StatusBadge status={log.status} /></td>
                        <td style={{ fontSize: 11 }}>{formatDateTime(log.created_at)}</td>
                        <td>
                          {log.status === 'COMPLETED' && (
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => undoMutation.mutate(log.id)}
                              disabled={undoMutation.isPending}
                            >
                              Undo
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                    {!logs.length && <tr><td colSpan={5} className="admin-table-empty">No imports yet</td></tr>}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ExportTab() {
  const qc = useQueryClient();
  const [entityType, setEntityType] = useState('packages');
  const [exporting, setExporting] = useState(false);
  const [format, setFormat] = useState('excel');
  const [downloadingId, setDownloadingId] = useState(null);

  const { data: exportLogsData, isLoading: logsLoading } = useQuery({
    queryKey: ['io', 'export-logs'],
    queryFn: () => ioApi.listExportLogs(),
  });
  const logs = exportLogsData?.items ?? [];

  const handleExport = async () => {
    setExporting(true);
    try {
      const result = await ioApi.triggerExport({ entity_type: entityType, format: format === 'excel' ? 'XLSX' : format.toUpperCase() });
      toast.success(`${result.message ?? 'Export complete'} (${result.estimated_rows ?? 0} rows)`);
      qc.invalidateQueries(['io', 'export-logs']);
    } catch (err) {
      toast.error(err?.response?.data?.detail ?? 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  const handleDownload = async (log) => {
    setDownloadingId(log.id);
    try {
      const { blob, filename } = await ioApi.downloadExport(log.id);
      downloadBlob(blob, filename);
    } catch (err) {
      toast.error(err?.response?.data?.detail ?? 'Download failed');
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <div className="grid-2">
      <div className="admin-card">
        <div className="admin-card-header"><div className="admin-card-title">Export Data</div></div>
        <div className="admin-card-body">
          <div className="form-group">
            <label className="form-label">Entity Type</label>
            <select className="form-control" value={entityType} onChange={e => setEntityType(e.target.value)}>
              {EXPORT_ENTITY_TYPES.map(t => <option key={t} value={t}>{entityLabel(t)}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Format</label>
            <select className="form-control" value={format} onChange={e => setFormat(e.target.value)}>
              <option value="excel">Excel (.xlsx)</option>
              <option value="csv">CSV</option>
              <option value="json">JSON</option>
            </select>
          </div>
          <button className="btn btn-primary" onClick={handleExport} disabled={exporting}>
            {exporting ? 'Exporting…' : 'Export'}
          </button>
        </div>
      </div>

      <div className="admin-card">
        <div className="admin-card-header"><div className="admin-card-title">Export History</div></div>
        <div className="admin-card-body" style={{ padding: 0 }}>
          {logsLoading ? <SkeletonTable rows={5} cols={5} /> : (
            <div className="admin-table-wrapper">
              <table className="admin-table">
                <thead><tr><th>Type</th><th>Format</th><th>Rows</th><th>Status</th><th>When</th><th></th></tr></thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id}>
                      <td>{log.entity_type}</td>
                      <td>{log.format ?? 'excel'}</td>
                      <td>{log.row_count ?? 0}</td>
                      <td><StatusBadge status={log.status} /></td>
                      <td style={{ fontSize: 11 }}>{formatDateTime(log.created_at)}</td>
                      <td>
                        {log.status === 'COMPLETED' && log.row_count > 0 && (
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => handleDownload(log)}
                            disabled={downloadingId === log.id}
                          >
                            {downloadingId === log.id ? 'Downloading…' : 'Download'}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {!logs.length && <tr><td colSpan={6} className="admin-table-empty">No exports yet</td></tr>}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ImportExportPage() {
  const [activeTab, setActiveTab] = useState('import');

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Import / Export</h1>
          <p>Bulk import data via Excel/CSV or export records</p>
        </div>
      </div>

      <div className="admin-tabs">
        <button className={`admin-tab${activeTab === 'import' ? ' active' : ''}`} onClick={() => setActiveTab('import')}>Import</button>
        <button className={`admin-tab${activeTab === 'export' ? ' active' : ''}`} onClick={() => setActiveTab('export')}>Export</button>
      </div>

      {activeTab === 'import' && <ImportTab />}
      {activeTab === 'export' && <ExportTab />}
    </div>
  );
}
