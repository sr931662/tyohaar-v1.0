import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ioApi } from '../../api';
import { formatDateTime } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import { SkeletonTable } from '../../components/ui/Skeleton';

const ENTITY_TYPES = ['vendors', 'packages', 'customers', 'bookings', 'products'];

function ImportTab() {
  const qc = useQueryClient();
  const fileRef = useRef(null);
  const [entityType, setEntityType] = useState('vendors');
  const [file, setFile] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [validating, setValidating] = useState(false);

  const { data: logs = [], isLoading: logsLoading } = useQuery({
    queryKey: ['io', 'import-logs'],
    queryFn: () => ioApi.listImportLogs(),
  });

  const downloadTemplate = async () => {
    try {
      const blob = await ioApi.getTemplate(entityType);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `${entityType}_template.xlsx`; a.click();
      URL.revokeObjectURL(url);
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
      const result = await ioApi.validateImport(formData);
      setValidationResult(result);
    } catch (err) {
      toast.error('Validation failed');
    } finally {
      setValidating(false);
    }
  };

  const executeMutation = useMutation({
    mutationFn: async () => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('entity_type', entityType);
      return ioApi.executeImport(formData);
    },
    onSuccess: () => {
      toast.success('Import queued successfully');
      setFile(null); setValidationResult(null);
      if (fileRef.current) fileRef.current.value = '';
      qc.invalidateQueries(['io', 'import-logs']);
    },
    onError: () => toast.error('Import failed'),
  });

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
      {/* Upload Panel */}
      <div>
        <div className="admin-card" style={{ marginBottom: 16 }}>
          <div className="admin-card-header"><div className="admin-card-title">Import Data</div></div>
          <div className="admin-card-body">
            <div className="form-group">
              <label className="form-label">Entity Type</label>
              <select className="form-control" value={entityType} onChange={e => { setEntityType(e.target.value); setFile(null); setValidationResult(null); }}>
                {ENTITY_TYPES.map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
              </select>
            </div>
            <button className="btn btn-secondary btn-sm" onClick={downloadTemplate} style={{ marginBottom: 16 }}>
              Download {entityType} template
            </button>
            <div className="form-group">
              <label className="form-label">Upload Excel / CSV</label>
              <input ref={fileRef} className="form-control" type="file" accept=".xlsx,.csv" onChange={e => { setFile(e.target.files[0]); setValidationResult(null); }} />
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
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
            {logsLoading ? <SkeletonTable rows={5} cols={4} /> : (
              <table className="admin-table">
                <thead><tr><th>Type</th><th>Rows</th><th>Status</th><th>When</th></tr></thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id}>
                      <td>{log.entity_type}</td>
                      <td>{log.total_rows}</td>
                      <td><StatusBadge status={log.status} /></td>
                      <td style={{ fontSize: 11 }}>{formatDateTime(log.created_at)}</td>
                    </tr>
                  ))}
                  {!logs.length && <tr><td colSpan={4} className="admin-table-empty">No imports yet</td></tr>}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ExportTab() {
  const [entityType, setEntityType] = useState('vendors');
  const [exporting, setExporting] = useState(false);
  const [format, setFormat] = useState('excel');

  const { data: logs = [], isLoading: logsLoading } = useQuery({
    queryKey: ['io', 'export-logs'],
    queryFn: () => ioApi.listExportLogs(),
  });

  const handleExport = async () => {
    setExporting(true);
    try {
      const result = await ioApi.triggerExport({ entity_type: entityType, format });
      toast.success(`Export queued (ID: ${result.export_id ?? result.id ?? 'N/A'})`);
    } catch {
      toast.error('Export failed');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
      <div className="admin-card">
        <div className="admin-card-header"><div className="admin-card-title">Export Data</div></div>
        <div className="admin-card-body">
          <div className="form-group">
            <label className="form-label">Entity Type</label>
            <select className="form-control" value={entityType} onChange={e => setEntityType(e.target.value)}>
              {ENTITY_TYPES.map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Format</label>
            <select className="form-control" value={format} onChange={e => setFormat(e.target.value)}>
              <option value="excel">Excel (.xlsx)</option>
              <option value="csv">CSV</option>
            </select>
          </div>
          <button className="btn btn-primary" onClick={handleExport} disabled={exporting}>
            {exporting ? 'Queuing…' : 'Export'}
          </button>
        </div>
      </div>

      <div className="admin-card">
        <div className="admin-card-header"><div className="admin-card-title">Export History</div></div>
        <div className="admin-card-body" style={{ padding: 0 }}>
          {logsLoading ? <SkeletonTable rows={5} cols={4} /> : (
            <table className="admin-table">
              <thead><tr><th>Type</th><th>Format</th><th>Status</th><th>When</th></tr></thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td>{log.entity_type}</td>
                    <td>{log.format ?? 'excel'}</td>
                    <td><StatusBadge status={log.status} /></td>
                    <td style={{ fontSize: 11 }}>{formatDateTime(log.created_at)}</td>
                  </tr>
                ))}
                {!logs.length && <tr><td colSpan={4} className="admin-table-empty">No exports yet</td></tr>}
              </tbody>
            </table>
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
