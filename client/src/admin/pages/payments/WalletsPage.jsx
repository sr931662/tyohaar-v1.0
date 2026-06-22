import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { walletsApi } from '../../api';
import { formatCurrency } from '../../utils/format';
import Modal from '../../components/ui/Modal';

export default function WalletsPage() {
  const [userId, setUserId] = useState('');
  const [walletResult, setWalletResult] = useState(null);
  const [walletLoading, setWalletLoading] = useState(false);
  const [creditOpen, setCreditOpen] = useState(false);
  const [debitOpen, setDebitOpen] = useState(false);
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');

  const lookupWallet = async () => {
    if (!userId.trim()) return;
    setWalletLoading(true);
    try {
      const data = await walletsApi.getById(userId);
      setWalletResult(data);
    } catch (err) {
      toast.error('Wallet not found for this user ID');
      setWalletResult(null);
    } finally {
      setWalletLoading(false);
    }
  };

  const creditMutation = useMutation({
    mutationFn: () => walletsApi.credit(userId, { amount: parseFloat(amount), description }),
    onSuccess: (data) => {
      toast.success(`Credited ${formatCurrency(parseFloat(amount))}`);
      setCreditOpen(false); setAmount(''); setDescription('');
      lookupWallet();
    },
    onError: () => toast.error('Credit failed'),
  });

  const debitMutation = useMutation({
    mutationFn: () => walletsApi.debit(userId, { amount: parseFloat(amount), description }),
    onSuccess: () => {
      toast.success(`Debited ${formatCurrency(parseFloat(amount))}`);
      setDebitOpen(false); setAmount(''); setDescription('');
      lookupWallet();
    },
    onError: () => toast.error('Debit failed'),
  });

  const freezeMutation = useMutation({
    mutationFn: (reason) => walletsApi.freeze(walletResult.id, reason),
    onSuccess: () => { toast.success('Wallet frozen'); lookupWallet(); },
    onError: () => toast.error('Failed'),
  });

  const unfreezeMutation = useMutation({
    mutationFn: () => walletsApi.unfreeze(walletResult.id),
    onSuccess: () => { toast.success('Wallet unfrozen'); lookupWallet(); },
    onError: () => toast.error('Failed'),
  });

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Wallet Management</h1>
          <p>Credit, debit, freeze, and manage user wallets</p>
        </div>
      </div>

      {/* Wallet Lookup */}
      <div className="admin-card" style={{ marginBottom: 24, maxWidth: 560 }}>
        <div className="admin-card-header"><div className="admin-card-title">Lookup Wallet by User ID</div></div>
        <div className="admin-card-body">
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              className="form-control"
              placeholder="Paste User UUID…"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && lookupWallet()}
            />
            <button className="btn btn-primary" onClick={lookupWallet} disabled={walletLoading || !userId.trim()}>
              {walletLoading ? '…' : 'Lookup'}
            </button>
          </div>
        </div>
      </div>

      {walletResult && (
        <div className="admin-card">
          <div className="admin-card-header">
            <div>
              <div className="admin-card-title">Wallet</div>
              <div className="admin-card-subtitle">ID: {walletResult.id}</div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-success btn-sm" onClick={() => { setAmount(''); setDescription(''); setCreditOpen(true); }}>+ Credit</button>
              <button className="btn btn-secondary btn-sm" onClick={() => { setAmount(''); setDescription(''); setDebitOpen(true); }}>− Debit</button>
              {walletResult.status === 'frozen' ? (
                <button className="btn btn-primary btn-sm" onClick={() => unfreezeMutation.mutate()}>Unfreeze</button>
              ) : (
                <button className="btn btn-danger btn-sm" onClick={() => freezeMutation.mutate('Admin freeze')}>Freeze</button>
              )}
            </div>
          </div>
          <div className="admin-card-body">
            <div className="admin-metric-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
              <div className="admin-metric-card">
                <div className="admin-metric-label">Balance</div>
                <div className="admin-metric-value">{formatCurrency(walletResult.balance ?? 0)}</div>
              </div>
              <div className="admin-metric-card">
                <div className="admin-metric-label">Status</div>
                <div className="admin-metric-value" style={{ fontSize: 16 }}>{walletResult.status ?? '—'}</div>
              </div>
              <div className="admin-metric-card">
                <div className="admin-metric-label">Currency</div>
                <div className="admin-metric-value" style={{ fontSize: 16 }}>{walletResult.currency ?? 'INR'}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Credit Modal */}
      <Modal open={creditOpen} onClose={() => setCreditOpen(false)} title="Credit Wallet"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setCreditOpen(false)}>Cancel</button>
            <button className="btn btn-success" onClick={() => creditMutation.mutate()} disabled={!amount || creditMutation.isPending}>
              {creditMutation.isPending ? 'Processing…' : 'Credit'}
            </button>
          </>
        }
      >
        <div className="form-group">
          <label className="form-label required">Amount (INR)</label>
          <input className="form-control" type="number" min={1} value={amount} onChange={e => setAmount(e.target.value)} placeholder="100" />
        </div>
        <div className="form-group">
          <label className="form-label required">Description</label>
          <input className="form-control" value={description} onChange={e => setDescription(e.target.value)} placeholder="Reason for credit…" />
        </div>
      </Modal>

      {/* Debit Modal */}
      <Modal open={debitOpen} onClose={() => setDebitOpen(false)} title="Debit Wallet"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setDebitOpen(false)}>Cancel</button>
            <button className="btn btn-danger" onClick={() => debitMutation.mutate()} disabled={!amount || debitMutation.isPending}>
              {debitMutation.isPending ? 'Processing…' : 'Debit'}
            </button>
          </>
        }
      >
        <div className="form-group">
          <label className="form-label required">Amount (INR)</label>
          <input className="form-control" type="number" min={1} value={amount} onChange={e => setAmount(e.target.value)} placeholder="100" />
        </div>
        <div className="form-group">
          <label className="form-label required">Description</label>
          <input className="form-control" value={description} onChange={e => setDescription(e.target.value)} placeholder="Reason for debit…" />
        </div>
      </Modal>
    </div>
  );
}
