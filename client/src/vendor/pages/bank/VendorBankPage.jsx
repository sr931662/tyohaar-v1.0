import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { vendorProfileApi } from '../../api';
import { ConfirmDialog } from '../../../admin/components/ui/Modal';

const ACCOUNT_TYPES = ['savings', 'current', 'salary'];
const DOC_TYPES = ['pan_card', 'aadhar', 'cancelled_cheque', 'passbook'];

function AddBankModal({ vendorId, onClose }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    account_holder_name: '',
    account_number: '',
    ifsc_code: '',
    bank_name: '',
    branch_name: '',
    is_primary: false,
  });
  const [errors, setErrors] = useState({});

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const validate = () => {
    const e = {};
    if (!form.account_holder_name.trim()) e.account_holder_name = 'Required.';
    if (!form.account_number.trim()) e.account_number = 'Required.';
    if (!form.ifsc_code.trim() || form.ifsc_code.trim().length !== 11) e.ifsc_code = 'IFSC must be exactly 11 characters.';
    if (!form.bank_name.trim()) e.bank_name = 'Required.';
    setErrors(e);
    return !Object.keys(e).length;
  };

  const mutation = useMutation({
    mutationFn: (body) => vendorProfileApi.addBankAccount(vendorId, body),
    onSuccess: () => {
      toast.success('Bank account added.');
      qc.invalidateQueries(['vendor-bank-accounts', vendorId]);
      onClose();
    },
    onError: (err) => toast.error(err?.response?.data?.detail ?? 'Failed to add bank account.'),
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validate()) return;
    mutation.mutate({
      vendor_id: vendorId,
      account_holder_name: form.account_holder_name.trim(),
      account_number: form.account_number.trim(),
      ifsc_code: form.ifsc_code.trim().toUpperCase(),
      bank_name: form.bank_name.trim(),
      branch_name: form.branch_name.trim() || undefined,
      is_primary: form.is_primary,
    });
  };

  const inputRow = (label, key, props = {}) => (
    <div>
      <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>{label}</label>
      <input className="admin-input" value={form[key]} onChange={(e) => set(key, e.target.value)} {...props} />
      {errors[key] && <p style={{ color: 'var(--color-error,#ef4444)', fontSize: 12, marginTop: 4 }}>{errors[key]}</p>}
    </div>
  );

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal" style={{ maxWidth: 480 }} onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <h2 className="admin-modal-title">Add Bank Account</h2>
          <button className="admin-modal-close" onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit} style={{ padding: '0 24px 24px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          {inputRow('Account Holder Name *', 'account_holder_name', { placeholder: 'As on bank records' })}
          {inputRow('Account Number *', 'account_number', { placeholder: 'Full account number' })}
          <div className="form-row-2">
            <div>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6 }}>IFSC Code *</label>
              <input className="admin-input" value={form.ifsc_code} onChange={(e) => set('ifsc_code', e.target.value.toUpperCase())} placeholder="e.g. SBIN0001234" maxLength={11} />
              {errors.ifsc_code && <p style={{ color: 'var(--color-error,#ef4444)', fontSize: 12, marginTop: 4 }}>{errors.ifsc_code}</p>}
            </div>
            <div>
              {inputRow('Bank Name *', 'bank_name', { placeholder: 'e.g. State Bank of India' })}
            </div>
          </div>
          {inputRow('Branch Name', 'branch_name', { placeholder: 'e.g. Andheri West (optional)' })}
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer', userSelect: 'none' }}>
            <input type="checkbox" checked={form.is_primary} onChange={(e) => set('is_primary', e.target.checked)} />
            Set as primary payout account
          </label>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 4 }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>
              {mutation.isPending ? 'Adding…' : 'Add Account'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function BankCard({ account, onDelete }) {
  return (
    <div className="admin-card" style={{ padding: '18px 20px', display: 'flex', alignItems: 'flex-start', gap: 16 }}>
      <div style={{
        width: 44, height: 44, borderRadius: 12, flexShrink: 0,
        background: 'rgba(59,130,246,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20,
      }}>
        🏦
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>{account.bank_name}</span>
          {account.is_primary && (
            <span style={{ fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 99, background: 'rgba(34,197,94,0.12)', color: '#22c55e', border: '1px solid rgba(34,197,94,0.25)' }}>
              Primary
            </span>
          )}
          {account.is_verified && (
            <span style={{ fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 99, background: 'rgba(59,130,246,0.1)', color: '#3b82f6', border: '1px solid rgba(59,130,246,0.2)' }}>
              Verified
            </span>
          )}
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
          {account.account_holder_name} · ••••{account.account_number_masked}
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 3 }}>
          IFSC: {account.ifsc_code}{account.branch_name ? ` · ${account.branch_name}` : ''}
        </div>
      </div>
      <button
        className="btn btn-sm"
        style={{ background: 'transparent', border: '1px solid var(--border-subtle)', color: '#ef4444', flexShrink: 0 }}
        onClick={() => onDelete(account)}
      >
        Remove
      </button>
    </div>
  );
}

export default function VendorBankPage() {
  const qc = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const { data: vendor } = useQuery({
    queryKey: ['vendor', 'me'],
    queryFn: () => vendorProfileApi.getMe(),
    retry: (count, err) => err?.response?.status !== 404 && count < 2,
  });

  const { data: accounts = [], isLoading } = useQuery({
    queryKey: ['vendor-bank-accounts', vendor?.id],
    queryFn: () => vendorProfileApi.listBankAccounts(vendor.id),
    enabled: !!vendor?.id,
  });

  const deleteMutation = useMutation({
    mutationFn: (bankId) => vendorProfileApi.deleteBankAccount(vendor.id, bankId),
    onSuccess: () => {
      toast.success('Bank account removed.');
      qc.invalidateQueries(['vendor-bank-accounts', vendor.id]);
      setConfirmDelete(null);
    },
    onError: () => toast.error('Failed to remove bank account.'),
  });

  if (!vendor) {
    return (
      <div style={{ padding: 48, textAlign: 'center' }}>
        <p style={{ color: 'var(--text-secondary)' }}>Please create your vendor profile first.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Bank Accounts</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Manage your payout bank accounts.</p>
        </div>
        <div className="admin-page-header-actions">
          <button className="btn btn-primary" onClick={() => setShowAdd(true)}>+ Add Account</button>
        </div>
      </div>

      {/* Info banner */}
      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', background: 'rgba(245,158,11,0.07)', border: '1px solid rgba(245,158,11,0.18)', borderRadius: 10, padding: '11px 16px', marginBottom: 24, fontSize: 13, color: '#f59e0b' }}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginTop: 1, flexShrink: 0 }}><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <span>Bank accounts are used for payouts after successful event bookings. Maximum 3 accounts allowed. Account numbers are stored encrypted.</span>
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {[0, 1].map((i) => <div key={i} className="skeleton skeleton-card" style={{ height: 90 }} />)}
        </div>
      ) : !accounts.length ? (
        <div className="admin-card" style={{ padding: 48, textAlign: 'center' }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>🏦</div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 16 }}>No bank accounts added yet.</p>
          <button className="btn btn-primary" onClick={() => setShowAdd(true)}>+ Add Your First Account</button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {accounts.map((acc) => (
            <BankCard key={acc.id} account={acc} onDelete={setConfirmDelete} />
          ))}
        </div>
      )}

      {showAdd && <AddBankModal vendorId={vendor.id} onClose={() => setShowAdd(false)} />}

      <ConfirmDialog
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        onConfirm={() => deleteMutation.mutate(confirmDelete.id)}
        title="Remove Bank Account"
        message={`Remove the bank account ending in ••••${confirmDelete?.account_number_masked}? This cannot be undone.`}
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
