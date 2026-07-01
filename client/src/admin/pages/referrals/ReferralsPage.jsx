import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { referralsApi } from '../../api';
import Pagination from '../../components/ui/Pagination';
import Skeleton from '../../components/ui/Skeleton';
import EmptyState from '../../components/ui/EmptyState';
import StatusBadge from '../../components/ui/StatusBadge';

export default function ReferralsPage() {
  const [page, setPage] = useState(1);
  const perPage = 20;

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['referrals', 'stats'],
    queryFn: () => referralsApi.stats(),
  });

  const { data, isLoading } = useQuery({
    queryKey: ['referrals', 'list', { page, perPage }],
    queryFn: () => referralsApi.list({ page, per_page: perPage }),
  });

  const referrals = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Referrals</h1>
          <p className="admin-page-subtitle">Track referral codes, conversions, and reward payouts.</p>
        </div>
      </div>

      {/* Stats row */}
      <div className="admin-stats-grid" style={{ marginBottom: 24 }}>
        {statsLoading ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} height={80} radius={12} />)
        ) : (
          <>
            <div className="admin-stat-card">
              <div className="stat-value">{stats?.total_referrals ?? 0}</div>
              <div className="stat-label">Total Referrals</div>
            </div>
            <div className="admin-stat-card">
              <div className="stat-value">{stats?.successful_referrals ?? 0}</div>
              <div className="stat-label">Successful</div>
            </div>
            <div className="admin-stat-card">
              <div className="stat-value">{stats?.pending_rewards ?? 0}</div>
              <div className="stat-label">Pending Rewards</div>
            </div>
            <div className="admin-stat-card">
              <div className="stat-value">₹{(stats?.total_reward_value ?? 0).toLocaleString()}</div>
              <div className="stat-label">Total Rewards Issued</div>
            </div>
          </>
        )}
      </div>

      {/* Referrals table */}
      <div className="admin-card">
        <div className="admin-card-header">
          <h2 className="admin-card-title">All Referrals</h2>
          <span className="admin-badge">{total} total</span>
        </div>

        {isLoading ? (
          <div style={{ padding: 24 }}>
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} height={44} radius={8} style={{ marginBottom: 8 }} />
            ))}
          </div>
        ) : referrals.length === 0 ? (
          <EmptyState
            icon="🎁"
            title="No referrals yet"
            description="Referral activity will appear here once customers start sharing their codes."
          />
        ) : (
          <>
            <div className="admin-table-wrapper">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Referrer</th>
                    <th>Referee</th>
                    <th>Code</th>
                    <th>Status</th>
                    <th>Reward</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {referrals.map((r) => (
                    <tr key={r.id}>
                      <td>
                        <div style={{ fontWeight: 600 }}>{r.referrer?.full_name ?? '—'}</div>
                        <div style={{ fontSize: 12, color: 'var(--ink-3)' }}>{r.referrer?.phone ?? r.referrer?.email ?? ''}</div>
                      </td>
                      <td>
                        <div style={{ fontWeight: 600 }}>{r.referred?.full_name ?? '—'}</div>
                        <div style={{ fontSize: 12, color: 'var(--ink-3)' }}>{r.referred?.phone ?? r.referred?.email ?? ''}</div>
                      </td>
                      <td>
                        <code style={{ fontSize: 12, background: 'var(--surface-2)', padding: '2px 6px', borderRadius: 4 }}>
                          {r.referral_code ?? '—'}
                        </code>
                      </td>
                      <td>
                        <StatusBadge status={r.status} />
                      </td>
                      <td>
                        {r.reward_value ? (
                          <span style={{ fontWeight: 700, color: 'var(--leaf)' }}>
                            ₹{r.reward_value.toLocaleString()}
                          </span>
                        ) : '—'}
                      </td>
                      <td style={{ color: 'var(--ink-3)', fontSize: 13 }}>
                        {r.created_at ? new Date(r.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {totalPages > 1 && (
              <div style={{ padding: '16px 24px', borderTop: '1px solid var(--line)' }}>
                <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
