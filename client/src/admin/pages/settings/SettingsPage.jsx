import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { settingsApi } from '../../api';
import { formatDate } from '../../utils/format';
import Modal, { ConfirmDialog } from '../../components/ui/Modal';
import { SkeletonTable } from '../../components/ui/Skeleton';
import RichTextEditor from '../../components/ui/RichTextEditor';

function FAQsTab() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [deleteId, setDeleteId] = useState(null);
  const [form, setForm] = useState({ question: '', answer: '', category: '', position: 0 });

  const { data: faqs = [], isLoading } = useQuery({
    queryKey: ['settings', 'faqs'],
    queryFn: () => settingsApi.listFAQs(),
  });

  const saveMutation = useMutation({
    mutationFn: (body) => editItem ? settingsApi.updateFAQ(editItem.id, body) : settingsApi.createFAQ(body),
    onSuccess: () => { toast.success(editItem ? 'Updated' : 'Created'); qc.invalidateQueries(['settings', 'faqs']); setOpen(false); setEditItem(null); },
    onError: () => toast.error('Failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => settingsApi.deleteFAQ(id),
    onSuccess: () => { toast.success('Deleted'); qc.invalidateQueries(['settings', 'faqs']); setDeleteId(null); },
    onError: () => toast.error('Failed'),
  });

  const openEdit = (f) => {
    setEditItem(f);
    setForm({ question: f.question, answer: f.answer, category: f.category ?? '', position: f.position ?? 0 });
    setOpen(true);
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <button className="btn btn-primary" onClick={() => { setEditItem(null); setForm({ question:'', answer:'', category:'', position:0 }); setOpen(true); }}>+ New FAQ</button>
      </div>
      {isLoading ? <SkeletonTable rows={5} cols={3} /> : (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead><tr><th>Question</th><th>Category</th><th>Pos</th><th>Actions</th></tr></thead>
            <tbody>
              {faqs.map((f) => (
                <tr key={f.id}>
                  <td style={{ maxWidth: 360 }}>{f.question}</td>
                  <td>{f.category ?? '—'}</td>
                  <td>{f.position}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => openEdit(f)}>Edit</button>
                      <button className="btn btn-danger btn-sm" onClick={() => setDeleteId(f.id)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
              {!faqs.length && <tr><td colSpan={4} className="admin-table-empty">No FAQs</td></tr>}
            </tbody>
          </table>
        </div>
      )}
      <Modal open={open} onClose={() => setOpen(false)} title={editItem ? 'Edit FAQ' : 'New FAQ'}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={() => saveMutation.mutate(form)} disabled={!form.question || saveMutation.isPending}>
              {saveMutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </>
        }
      >
        <div className="form-group"><label className="form-label required">Question</label><input className="form-control" value={form.question} onChange={e => setForm(f => ({ ...f, question: e.target.value }))} /></div>
        <div className="form-group"><label className="form-label required">Answer</label><textarea className="form-control" rows={4} value={form.answer} onChange={e => setForm(f => ({ ...f, answer: e.target.value }))} /></div>
        <div className="form-row-2">
          <div className="form-group"><label className="form-label">Category</label><input className="form-control" value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))} /></div>
          <div className="form-group"><label className="form-label">Position</label><input className="form-control" type="number" value={form.position} onChange={e => setForm(f => ({ ...f, position: parseInt(e.target.value) || 0 }))} /></div>
        </div>
      </Modal>
      <ConfirmDialog open={!!deleteId} onClose={() => setDeleteId(null)} onConfirm={() => deleteMutation.mutate(deleteId)}
        title="Delete FAQ" message="This FAQ will be deleted." danger loading={deleteMutation.isPending} />
    </div>
  );
}

function StatesTab() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [selectedState, setSelectedState] = useState(null);
  const [form, setForm] = useState({ name: '', code: '', is_active: true });
  const [cityForm, setCityForm] = useState({ name: '', is_active: true });
  const [cityOpen, setCityOpen] = useState(false);

  const { data: states = [], isLoading } = useQuery({
    queryKey: ['settings', 'states'],
    queryFn: () => settingsApi.listStates(),
  });

  const { data: cities = [] } = useQuery({
    queryKey: ['settings', 'cities', selectedState?.id],
    queryFn: () => settingsApi.listCities({ state_id: selectedState.id }),
    enabled: !!selectedState?.id,
  });

  const stateMutation = useMutation({
    mutationFn: (body) => editItem ? settingsApi.updateState(editItem.id, body) : settingsApi.createState(body),
    onSuccess: () => { toast.success(editItem ? 'Updated' : 'Created'); qc.invalidateQueries(['settings', 'states']); setOpen(false); setEditItem(null); },
    onError: () => toast.error('Failed'),
  });

  const deleteStateMutation = useMutation({
    mutationFn: (id) => settingsApi.deleteState(id),
    onSuccess: () => { toast.success('Deleted'); qc.invalidateQueries(['settings', 'states']); if (selectedState?.id === editItem?.id) setSelectedState(null); },
    onError: () => toast.error('Failed'),
  });

  const cityMutation = useMutation({
    mutationFn: (body) => settingsApi.createCity({ ...body, state_id: selectedState.id }),
    onSuccess: () => { toast.success('City added'); qc.invalidateQueries(['settings', 'cities', selectedState.id]); setCityOpen(false); setCityForm({ name: '', is_active: true }); },
    onError: () => toast.error('Failed'),
  });

  const deleteCityMutation = useMutation({
    mutationFn: (id) => settingsApi.deleteCity(id),
    onSuccess: () => { toast.success('Deleted'); qc.invalidateQueries(['settings', 'cities', selectedState?.id]); },
    onError: () => toast.error('Failed'),
  });

  return (
    <div className="grid-2">
      {/* States */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div style={{ fontWeight: 600, fontSize: 14 }}>States</div>
          <button className="btn btn-primary btn-sm" onClick={() => { setEditItem(null); setForm({ name: '', code: '', is_active: true }); setOpen(true); }}>+ Add State</button>
        </div>
        {isLoading ? <SkeletonTable rows={5} cols={3} /> : (
          <div className="admin-table-wrapper">
            <table className="admin-table">
              <thead><tr><th>Name</th><th>Code</th><th>Actions</th></tr></thead>
              <tbody>
                {states.map((s) => (
                  <tr key={s.id} style={{ cursor: 'pointer', background: selectedState?.id === s.id ? 'var(--brand-50)' : '' }} onClick={() => setSelectedState(s)}>
                    <td style={{ fontWeight: selectedState?.id === s.id ? 600 : 400 }}>{s.name}</td>
                    <td>{s.code ?? '—'}</td>
                    <td onClick={e => e.stopPropagation()}>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button className="btn btn-secondary btn-sm" onClick={() => { setEditItem(s); setForm({ name: s.name, code: s.code ?? '', is_active: s.is_active ?? true }); setOpen(true); }}>Edit</button>
                        <button className="btn btn-danger btn-sm" onClick={() => deleteStateMutation.mutate(s.id)}>Del</button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!states.length && <tr><td colSpan={3} className="admin-table-empty">No states</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Cities */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div style={{ fontWeight: 600, fontSize: 14 }}>Cities {selectedState && <span style={{ color: 'var(--brand-600)' }}>— {selectedState.name}</span>}</div>
          {selectedState && <button className="btn btn-primary btn-sm" onClick={() => setCityOpen(true)}>+ Add City</button>}
        </div>
        {!selectedState ? (
          <div style={{ padding: '32px 0', textAlign: 'center', color: 'var(--text-tertiary)', fontSize: 13 }}>Select a state to view cities</div>
        ) : (
          <div className="admin-table-wrapper">
            <table className="admin-table">
              <thead><tr><th>City</th><th>Actions</th></tr></thead>
              <tbody>
                {cities.map((c) => (
                  <tr key={c.id}>
                    <td>{c.name}</td>
                    <td><button className="btn btn-danger btn-sm" onClick={() => deleteCityMutation.mutate(c.id)}>Del</button></td>
                  </tr>
                ))}
                {!cities.length && <tr><td colSpan={2} className="admin-table-empty">No cities</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title={editItem ? 'Edit State' : 'Add State'}
        footer={<><button className="btn btn-secondary" onClick={() => setOpen(false)}>Cancel</button><button className="btn btn-primary" onClick={() => stateMutation.mutate(form)} disabled={!form.name || stateMutation.isPending}>{stateMutation.isPending ? 'Saving…' : 'Save'}</button></>}
      >
        <div className="form-group"><label className="form-label">Name *</label><input className="form-control" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} /></div>
        <div className="form-group"><label className="form-label">Code</label><input className="form-control" value={form.code} onChange={e => setForm(f => ({ ...f, code: e.target.value }))} placeholder="e.g. MH" /></div>
      </Modal>

      <Modal open={cityOpen} onClose={() => setCityOpen(false)} title={`Add City to ${selectedState?.name}`}
        footer={<><button className="btn btn-secondary" onClick={() => setCityOpen(false)}>Cancel</button><button className="btn btn-primary" onClick={() => cityMutation.mutate(cityForm)} disabled={!cityForm.name || cityMutation.isPending}>{cityMutation.isPending ? 'Saving…' : 'Add'}</button></>}
      >
        <div className="form-group"><label className="form-label">City Name *</label><input className="form-control" value={cityForm.name} onChange={e => setCityForm(f => ({ ...f, name: e.target.value }))} /></div>
      </Modal>
    </div>
  );
}

function LegalTab() {
  const qc = useQueryClient();
  const [termsOpen, setTermsOpen] = useState(false);
  const [privacyOpen, setPrivacyOpen] = useState(false);
  const [cancellationOpen, setCancellationOpen] = useState(false);
  const emptyForm = { title: '', content: '', version: '', effective_date: '', summary: '' };
  const [termsForm, setTermsForm] = useState(emptyForm);
  const [privacyForm, setPrivacyForm] = useState(emptyForm);
  const [cancellationForm, setCancellationForm] = useState(emptyForm);

  const { data: currentTerms } = useQuery({
    queryKey: ['settings', 'terms', 'current'],
    queryFn: () => settingsApi.getCurrentTerms(),
  });

  const { data: currentPrivacy } = useQuery({
    queryKey: ['settings', 'privacy', 'current'],
    queryFn: () => settingsApi.getCurrentPrivacy(),
  });

  const { data: currentCancellation } = useQuery({
    queryKey: ['settings', 'cancellation', 'current'],
    queryFn: () => settingsApi.getCurrentCancellationPolicy(),
  });

  const { data: termsVersions } = useQuery({
    queryKey: ['settings', 'terms', 'versions'],
    queryFn: () => settingsApi.listTermsVersions({ per_page: 20 }),
  });

  const { data: cancellationVersions } = useQuery({
    queryKey: ['settings', 'cancellation', 'versions'],
    queryFn: () => settingsApi.listCancellationPolicyVersions({ per_page: 20 }),
  });

  const createTermsMutation = useMutation({
    mutationFn: (body) => settingsApi.createTermsVersion(body),
    onSuccess: () => { toast.success('Terms version published'); qc.invalidateQueries(['settings', 'terms']); setTermsOpen(false); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed'),
  });

  const createPrivacyMutation = useMutation({
    mutationFn: (body) => settingsApi.createPrivacyVersion(body),
    onSuccess: () => { toast.success('Privacy policy published'); qc.invalidateQueries(['settings', 'privacy']); setPrivacyOpen(false); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed'),
  });

  const createCancellationMutation = useMutation({
    mutationFn: (body) => settingsApi.createCancellationPolicyVersion(body),
    onSuccess: () => { toast.success('Cancellation policy published'); qc.invalidateQueries(['settings', 'cancellation']); setCancellationOpen(false); },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed'),
  });

  return (
    <div className="grid-2">
      {/* Terms */}
      <div className="admin-card">
        <div className="admin-card-header">
          <div className="admin-card-title">Terms &amp; Conditions</div>
          <button className="btn btn-primary btn-sm" onClick={() => { setTermsForm({ ...emptyForm, title: currentTerms?.title ?? 'Terms & Conditions', content: currentTerms?.content ?? '' }); setTermsOpen(true); }}>Publish New</button>
        </div>
        <div className="admin-card-body">
          {currentTerms ? (
            <>
              <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 8 }}>
                Current: v{currentTerms.version} — {formatDate(currentTerms.effective_date ?? currentTerms.created_at)}
              </div>
              <div
                style={{ fontSize: 13, color: 'var(--text-secondary)', maxHeight: 160, overflowY: 'auto', lineHeight: 1.6 }}
                dangerouslySetInnerHTML={{ __html: currentTerms.content ?? '' }}
              />
            </>
          ) : (
            <div style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>No Terms published yet.</div>
          )}

          {termsVersions?.items?.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Version History</div>
              {termsVersions.items.map((v) => (
                <div key={v.id} style={{ fontSize: 12, color: 'var(--text-tertiary)', padding: '3px 0' }}>
                  v{v.version} — {formatDate(v.created_at)} {v.is_current && <span style={{ color: 'var(--brand-600)', fontWeight: 600 }}>(current)</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Privacy Policy */}
      <div className="admin-card">
        <div className="admin-card-header">
          <div className="admin-card-title">Privacy Policy</div>
          <button className="btn btn-primary btn-sm" onClick={() => { setPrivacyForm({ ...emptyForm, title: currentPrivacy?.title ?? 'Privacy Policy', content: currentPrivacy?.content ?? '' }); setPrivacyOpen(true); }}>Publish New</button>
        </div>
        <div className="admin-card-body">
          {currentPrivacy ? (
            <>
              <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 8 }}>
                Current: v{currentPrivacy.version} — {formatDate(currentPrivacy.effective_date ?? currentPrivacy.created_at)}
              </div>
              <div
                style={{ fontSize: 13, color: 'var(--text-secondary)', maxHeight: 160, overflowY: 'auto', lineHeight: 1.6 }}
                dangerouslySetInnerHTML={{ __html: currentPrivacy.content ?? '' }}
              />
            </>
          ) : (
            <div style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>No Privacy Policy published yet.</div>
          )}
        </div>
      </div>

      {/* Cancellation & Refund Policy */}
      <div className="admin-card">
        <div className="admin-card-header">
          <div className="admin-card-title">Cancellation &amp; Refund Policy</div>
          <button className="btn btn-primary btn-sm" onClick={() => { setCancellationForm({ ...emptyForm, title: currentCancellation?.title ?? 'Cancellation & Refund Policy', content: currentCancellation?.content ?? '' }); setCancellationOpen(true); }}>Publish New</button>
        </div>
        <div className="admin-card-body">
          {currentCancellation ? (
            <>
              <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 8 }}>
                Current: v{currentCancellation.version} — {formatDate(currentCancellation.effective_date ?? currentCancellation.created_at)}
              </div>
              <div
                style={{ fontSize: 13, color: 'var(--text-secondary)', maxHeight: 160, overflowY: 'auto', lineHeight: 1.6 }}
                dangerouslySetInnerHTML={{ __html: currentCancellation.content ?? '' }}
              />
            </>
          ) : (
            <div style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>No Cancellation & Refund Policy published yet.</div>
          )}

          {cancellationVersions?.items?.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Version History</div>
              {cancellationVersions.items.map((v) => (
                <div key={v.id} style={{ fontSize: 12, color: 'var(--text-tertiary)', padding: '3px 0' }}>
                  v{v.version} — {formatDate(v.created_at)}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Terms publish modal */}
      <Modal open={termsOpen} onClose={() => setTermsOpen(false)} title="Publish New Terms Version"
        footer={<><button className="btn btn-secondary" onClick={() => setTermsOpen(false)}>Cancel</button><button className="btn btn-primary" onClick={() => createTermsMutation.mutate(termsForm)} disabled={!termsForm.title || !termsForm.content || !termsForm.version || !termsForm.effective_date || createTermsMutation.isPending}>{createTermsMutation.isPending ? 'Publishing…' : 'Publish'}</button></>}
      >
        <div className="form-row-2">
          <div className="form-group"><label className="form-label">Version *</label><input className="form-control" value={termsForm.version} onChange={e => setTermsForm(f => ({ ...f, version: e.target.value }))} placeholder="e.g. 1.2" /></div>
          <div className="form-group"><label className="form-label">Effective Date *</label><input type="date" className="form-control" value={termsForm.effective_date} onChange={e => setTermsForm(f => ({ ...f, effective_date: e.target.value }))} /></div>
        </div>
        <div className="form-group"><label className="form-label">Title *</label><input className="form-control" value={termsForm.title} onChange={e => setTermsForm(f => ({ ...f, title: e.target.value }))} /></div>
        <div className="form-group">
          <label className="form-label">Content *</label>
          <RichTextEditor value={termsForm.content} onChange={(html) => setTermsForm(f => ({ ...f, content: html }))} placeholder="Write the Terms & Conditions content…" />
        </div>
        <div className="form-group"><label className="form-label">Summary</label><input className="form-control" value={termsForm.summary} onChange={e => setTermsForm(f => ({ ...f, summary: e.target.value }))} placeholder="Short summary of changes for users" /></div>
      </Modal>

      {/* Privacy publish modal */}
      <Modal open={privacyOpen} onClose={() => setPrivacyOpen(false)} title="Publish New Privacy Policy"
        footer={<><button className="btn btn-secondary" onClick={() => setPrivacyOpen(false)}>Cancel</button><button className="btn btn-primary" onClick={() => createPrivacyMutation.mutate(privacyForm)} disabled={!privacyForm.title || !privacyForm.content || !privacyForm.version || !privacyForm.effective_date || createPrivacyMutation.isPending}>{createPrivacyMutation.isPending ? 'Publishing…' : 'Publish'}</button></>}
      >
        <div className="form-row-2">
          <div className="form-group"><label className="form-label">Version *</label><input className="form-control" value={privacyForm.version} onChange={e => setPrivacyForm(f => ({ ...f, version: e.target.value }))} placeholder="e.g. 1.2" /></div>
          <div className="form-group"><label className="form-label">Effective Date *</label><input type="date" className="form-control" value={privacyForm.effective_date} onChange={e => setPrivacyForm(f => ({ ...f, effective_date: e.target.value }))} /></div>
        </div>
        <div className="form-group"><label className="form-label">Title *</label><input className="form-control" value={privacyForm.title} onChange={e => setPrivacyForm(f => ({ ...f, title: e.target.value }))} /></div>
        <div className="form-group">
          <label className="form-label">Content *</label>
          <RichTextEditor value={privacyForm.content} onChange={(html) => setPrivacyForm(f => ({ ...f, content: html }))} placeholder="Write the Privacy Policy content…" />
        </div>
        <div className="form-group"><label className="form-label">Summary</label><input className="form-control" value={privacyForm.summary} onChange={e => setPrivacyForm(f => ({ ...f, summary: e.target.value }))} /></div>
      </Modal>

      {/* Cancellation policy publish modal */}
      <Modal open={cancellationOpen} onClose={() => setCancellationOpen(false)} title="Publish New Cancellation & Refund Policy"
        footer={<><button className="btn btn-secondary" onClick={() => setCancellationOpen(false)}>Cancel</button><button className="btn btn-primary" onClick={() => createCancellationMutation.mutate(cancellationForm)} disabled={!cancellationForm.title || !cancellationForm.content || !cancellationForm.version || !cancellationForm.effective_date || createCancellationMutation.isPending}>{createCancellationMutation.isPending ? 'Publishing…' : 'Publish'}</button></>}
      >
        <div className="form-row-2">
          <div className="form-group"><label className="form-label">Version *</label><input className="form-control" value={cancellationForm.version} onChange={e => setCancellationForm(f => ({ ...f, version: e.target.value }))} placeholder="e.g. 1.2" /></div>
          <div className="form-group"><label className="form-label">Effective Date *</label><input type="date" className="form-control" value={cancellationForm.effective_date} onChange={e => setCancellationForm(f => ({ ...f, effective_date: e.target.value }))} /></div>
        </div>
        <div className="form-group"><label className="form-label">Title *</label><input className="form-control" value={cancellationForm.title} onChange={e => setCancellationForm(f => ({ ...f, title: e.target.value }))} /></div>
        <div className="form-group">
          <label className="form-label">Content *</label>
          <RichTextEditor value={cancellationForm.content} onChange={(html) => setCancellationForm(f => ({ ...f, content: html }))} placeholder="Write the Cancellation & Refund Policy content…" />
        </div>
        <div className="form-group"><label className="form-label">Summary</label><input className="form-control" value={cancellationForm.summary} onChange={e => setCancellationForm(f => ({ ...f, summary: e.target.value }))} placeholder="Short summary shown to customers" /></div>
      </Modal>
    </div>
  );
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('faqs');

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Platform Settings</h1>
          <p>Configure FAQs, locations, and legal documents</p>
        </div>
      </div>

      <div className="admin-tabs">
        {[['faqs', 'FAQs'], ['locations', 'States & Cities'], ['legal', 'Terms & Privacy']].map(([key, label]) => (
          <button key={key} className={`admin-tab${activeTab === key ? ' active' : ''}`} onClick={() => setActiveTab(key)}>
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'faqs' && <FAQsTab />}
      {activeTab === 'locations' && <StatesTab />}
      {activeTab === 'legal' && <LegalTab />}
    </div>
  );
}
