import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { vendorWalletApi } from '../../api';
import { formatCurrency, formatDateTime } from '../../../admin/utils/format';
import { SkeletonMetrics } from '../../../admin/components/ui/Skeleton';
import Pagination from '../../../admin/components/ui/Pagination';
import { usePagination } from '../../../admin/hooks/usePagination';
import EmptyState from '../../../admin/components/ui/EmptyState';

const TX_TYPE_COLOR = {
  credit: '#22c55e',
  debit: '#ef4444',
  hold: '#f59e0b',
  release: '#3b82f6',
};

const TX_TYPE_LABEL = {
  credit: 'Credit',
  debit: 'Debit',
  hold: 'On Hold',
  release: 'Released',
};

function MetricCard({ label, value, sub, color }) {
  return (
    <div className="admin-metric-card">
      <div className="admin-metric-label">{label}</div>
      <div className="admin-metric-value" style={color ? { color } : {}}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

export default function VendorEarningsPage() {
  const { page, perPage, setPage } = usePagination();
  const [txType, setTxType] = useState('');

  const { data: wallet, isLoading: walletLoading, error: walletError } = useQuery({
    queryKey: ['vendor-wallet'],
    queryFn: () => vendorWalletApi.get(),
    retry: 1,
  });

  const { data: txData, isLoading: txLoading } = useQuery({
    queryKey: ['vendor-wallet-transactions', { page, perPage, txType }],
    queryFn: () => vendorWalletApi.listTransactions({
      page,
      per_page: perPage,
      transaction_type: txType || undefined,
    }),
    retry: 1,
  });

  const txItems = txData?.items ?? [];
  const txTotal = txData?.total ?? 0;
  const txPages = txData?.pages ?? 1;

  if (walletError) {
    return (
      <div>
        <div className="admin-page-header">
          <div className="admin-page-header-left">
            <h1>Earnings</h1>
          </div>
        </div>
        <div style={{ padding: 48, textAlign: 'center' }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>💰</div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 8 }}>Earnings wallet not available yet.</p>
          <p style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>Your vendor earnings wallet will appear here once you complete your first booking.</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Earnings</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Your wallet balance and transaction history</p>
        </div>
      </div>

      {/* Wallet metrics */}
      {walletLoading ? (
        <SkeletonMetrics count={4} />
      ) : wallet ? (
        <div className="admin-metric-grid" style={{ marginBottom: 24 }}>
          <MetricCard
            label="Available Balance"
            value={formatCurrency(wallet.available_balance ?? 0)}
            color="#22c55e"
          />
          <MetricCard
            label="Pending Balance"
            value={formatCurrency(wallet.pending_balance ?? 0)}
            sub="Awaiting settlement"
          />
          <MetricCard
            label="Lifetime Credits"
            value={formatCurrency(wallet.lifetime_credits ?? 0)}
          />
          <MetricCard
            label="Lifetime Debits"
            value={formatCurrency(wallet.lifetime_debits ?? 0)}
          />
        </div>
      ) : (
        <div style={{ padding: 32, textAlign: 'center', marginBottom: 24 }}>
          <p style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>Wallet data not available.</p>
        </div>
      )}

      {/* Wallet status */}
      {wallet && (
        <div style={{ marginBottom: 20, display: 'flex', gap: 10, alignItems: 'center' }}>
          <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Wallet Status:</span>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 5,
            padding: '3px 10px', borderRadius: 99,
            background: wallet.wallet_status === 'ACTIVE' ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
            border: `1px solid ${wallet.wallet_status === 'ACTIVE' ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'}`,
            fontSize: 12, fontWeight: 600,
            color: wallet.wallet_status === 'ACTIVE' ? '#22c55e' : '#ef4444',
          }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'currentColor' }} />
            {wallet.wallet_status ?? 'Unknown'}
          </span>
          {wallet.last_transaction_at && (
            <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
              Last transaction: {formatDateTime(wallet.last_transaction_at)}
            </span>
          )}
        </div>
      )}

      {/* Transaction history */}
      <div className="admin-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
          <div style={{ fontWeight: 600, fontSize: 15 }}>Transaction History</div>
          <select
            className="admin-filters-select"
            style={{ width: 'auto' }}
            value={txType}
            onChange={(e) => { setTxType(e.target.value); setPage(1); }}
          >
            <option value="">All Types</option>
            <option value="credit">Credits</option>
            <option value="debit">Debits</option>
            <option value="hold">Holds</option>
            <option value="release">Releases</option>
          </select>
        </div>

        {txLoading ? (
          <div style={{ padding: 24 }}>
            {[0, 1, 2, 3, 4].map((i) => (
              <div key={i} className="skeleton skeleton-card" style={{ height: 52, marginBottom: 8 }} />
            ))}
          </div>
        ) : !txItems.length ? (
          <EmptyState
            title="No transactions yet"
            description="Your earnings transactions will appear here."
            icon="💳"
          />
        ) : (
          <>
            <div style={{ padding: '0 8px' }}>
              {txItems.map((tx) => (
                <div
                  key={tx.id}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 14,
                    padding: '14px 12px',
                    borderBottom: '1px solid var(--border-subtle)',
                  }}
                >
                  <div style={{
                    width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: `${TX_TYPE_COLOR[tx.transaction_type?.toLowerCase()] ?? 'var(--text-tertiary)'}15`,
                    color: TX_TYPE_COLOR[tx.transaction_type?.toLowerCase()] ?? 'var(--text-tertiary)',
                    fontWeight: 700, fontSize: 14,
                  }}>
                    {tx.transaction_type?.toLowerCase() === 'credit' ? '+' :
                     tx.transaction_type?.toLowerCase() === 'debit' ? '−' : '⟳'}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13.5, fontWeight: 500, color: 'var(--text-primary)' }}>
                      {tx.description ?? TX_TYPE_LABEL[tx.transaction_type?.toLowerCase()] ?? tx.transaction_type}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 1 }}>
                      {tx.reference_type && <span style={{ marginRight: 8 }}>{tx.reference_type}</span>}
                      {tx.created_at && formatDateTime(tx.created_at)}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{
                      fontSize: 15, fontWeight: 700,
                      color: TX_TYPE_COLOR[tx.transaction_type?.toLowerCase()] ?? 'var(--text-primary)',
                    }}>
                      {tx.transaction_type?.toLowerCase() === 'debit' ? '−' : '+'}
                      {formatCurrency(tx.amount ?? 0)}
                    </div>
                    {tx.new_balance !== undefined && (
                      <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>
                        Balance: {formatCurrency(tx.new_balance)}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <div style={{ padding: '12px 20px' }}>
              <Pagination page={page} pages={txPages} total={txTotal} perPage={perPage} onPageChange={setPage} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
