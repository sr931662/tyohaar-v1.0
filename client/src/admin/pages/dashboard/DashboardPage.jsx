import { useQuery } from '@tanstack/react-query';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { analyticsApi } from '../../api';
import { formatCurrency, formatNumber, formatPercent, timeAgo } from '../../utils/format';
import StatusBadge from '../../components/ui/StatusBadge';
import { SkeletonMetrics } from '../../components/ui/Skeleton';

const COLORS = ['#7c3aed', '#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6'];

function MetricCard({ label, value, trend, trendLabel, icon, iconBg }) {
  return (
    <div className="admin-metric-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div className="admin-metric-label">{label}</div>
          <div className="admin-metric-value">{value ?? '—'}</div>
          {trend != null && (
            <div className={`admin-metric-trend ${trend >= 0 ? 'up' : 'down'}`}>
              {trend >= 0 ? '↑' : '↓'} {Math.abs(trend).toFixed(1)}% {trendLabel ?? 'vs last month'}
            </div>
          )}
        </div>
        {icon && (
          <div className="admin-metric-icon" style={{ background: iconBg ?? 'var(--brand-100)', color: 'var(--brand-600)' }}>
            <span style={{ fontSize: 18 }}>{icon}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function PendingActionsCard({ data }) {
  if (!data) return null;
  const items = [
    { label: 'Pending Vendor Approvals', value: data.vendor_approvals, icon: '🏪', color: 'warning' },
    { label: 'Pending Booking Confirmations', value: data.booking_confirmations, icon: '📅', color: 'warning' },
    { label: 'Open Support Tickets', value: data.support_tickets, icon: '🎧', color: 'info' },
    { label: 'Media Awaiting Moderation', value: data.media_moderation, icon: '🖼️', color: 'neutral' },
  ].filter(i => i.value > 0);

  if (!items.length) return (
    <div className="admin-card">
      <div className="admin-card-header"><div className="admin-card-title">⚡ Pending Actions</div></div>
      <div className="admin-card-body" style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '32px 20px' }}>
        ✅ All clear — no pending actions!
      </div>
    </div>
  );

  return (
    <div className="admin-card">
      <div className="admin-card-header">
        <div>
          <div className="admin-card-title">⚡ Pending Actions</div>
          <div className="admin-card-subtitle">{items.length} item{items.length !== 1 ? 's' : ''} needing attention</div>
        </div>
      </div>
      <div style={{ padding: '8px 20px 16px' }}>
        {items.map((item) => (
          <div key={item.label} className="admin-data-list-item">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span>{item.icon}</span>
              <span style={{ fontSize: 13.5, color: 'var(--text-primary)' }}>{item.label}</span>
            </div>
            <span className={`badge badge-${item.color}`} style={{ fontWeight: 700 }}>{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ActivityFeed({ data }) {
  if (!data?.length) return null;
  return (
    <div className="admin-card">
      <div className="admin-card-header">
        <div className="admin-card-title">🕐 Recent Activity</div>
      </div>
      <div style={{ padding: '8px 20px 16px' }}>
        {data.slice(0, 10).map((item, i) => (
          <div key={i} className="admin-activity-item">
            <div className="admin-activity-icon">
              {item.type === 'booking' ? '📅' : item.type === 'vendor' ? '🏪' : item.type === 'payment' ? '💳' : '📌'}
            </div>
            <div className="admin-activity-content">
              <div className="admin-activity-text">{item.summary}</div>
              <div className="admin-activity-time">{timeAgo(item.timestamp)}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { data: dashboard, isLoading: loadingDash } = useQuery({
    queryKey: ['analytics', 'dashboard'],
    queryFn: () => analyticsApi.dashboard(),
    staleTime: 60000,
  });

  const { data: revenueChart, isLoading: loadingRevChart } = useQuery({
    queryKey: ['analytics', 'charts', 'revenue'],
    queryFn: () => analyticsApi.revenueChart({ period: '30d' }),
    staleTime: 60000,
  });

  const { data: bookingsChart } = useQuery({
    queryKey: ['analytics', 'charts', 'bookings'],
    queryFn: () => analyticsApi.bookingsChart({ period: '30d' }),
    staleTime: 60000,
  });

  const { data: usersChart } = useQuery({
    queryKey: ['analytics', 'charts', 'users'],
    queryFn: () => analyticsApi.usersChart({ period: '30d' }),
    staleTime: 60000,
  });

  const { data: categoryDist } = useQuery({
    queryKey: ['analytics', 'charts', 'categories'],
    queryFn: () => analyticsApi.categoryDistribution(),
    staleTime: 120000,
  });

  const { data: pendingActions } = useQuery({
    queryKey: ['analytics', 'pending-actions'],
    queryFn: () => analyticsApi.pendingActions(),
    staleTime: 30000,
    refetchInterval: 60000,
  });

  const { data: activityFeed } = useQuery({
    queryKey: ['analytics', 'activity-feed'],
    queryFn: () => analyticsApi.activityFeed({ limit: 10 }),
    staleTime: 30000,
    refetchInterval: 30000,
  });

  const { data: platformHealth } = useQuery({
    queryKey: ['analytics', 'platform-health'],
    queryFn: () => analyticsApi.platformHealth(),
    staleTime: 30000,
    refetchInterval: 60000,
  });

  const rev = dashboard?.revenue ?? {};
  const book = dashboard?.bookings ?? {};
  const users = dashboard?.users ?? {};
  const vendors = dashboard?.vendors ?? {};
  const wallets = dashboard?.wallets ?? {};

  // TimeSeriesChart shape: { series: [{ name, data: [{date, ...}] }] }
  const revenueData = revenueChart?.series?.[0]?.data ?? [];

  // Bookings chart has one series per status; pivot into one row per date
  // so the BarChart can read pending/confirmed/cancelled off each point.
  const bookingsBuckets = {};
  for (const s of bookingsChart?.series ?? []) {
    for (const point of s.data ?? []) {
      const row = bookingsBuckets[point.date] ?? { date: point.date };
      row[s.name.toLowerCase()] = point.value;
      bookingsBuckets[point.date] = row;
    }
  }
  const bookData = Object.values(bookingsBuckets).sort((a, b) => a.date.localeCompare(b.date));

  const userData = (usersChart?.series?.[0]?.data ?? []).map((p) => ({ date: p.date, registrations: p.value }));

  // PieChartData shape: { segments: [{label, value, pct}] }
  const catData = (categoryDist?.segments ?? []).map((s) => ({ name: s.label, count: s.value }));

  const activity = Array.isArray(activityFeed) ? activityFeed : activityFeed?.items ?? [];

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Executive Dashboard</h1>
          <p>Platform-wide overview and key metrics</p>
        </div>
      </div>

      {/* Metric Cards */}
      {loadingDash ? (
        <SkeletonMetrics count={6} />
      ) : (
        <div className="admin-metric-grid">
          <MetricCard
            label="Total Revenue"
            value={formatCurrency(rev.total_lifetime)}
            trend={rev.growth_pct_mom}
            icon="💰"
            iconBg="var(--success-50)"
          />
          <MetricCard
            label="Active Bookings"
            value={formatNumber((book.confirmed ?? 0) + (book.in_progress ?? 0))}
            icon="📅"
            iconBg="var(--info-50)"
          />
          <MetricCard
            label="Total Users"
            value={formatNumber(users.total)}
            icon="👥"
            iconBg="var(--brand-50)"
          />
          <MetricCard
            label="Active Vendors"
            value={formatNumber(vendors.verified)}
            icon="🏪"
            iconBg="var(--warning-50)"
          />
          <MetricCard
            label="Wallet Balance"
            value={formatCurrency(wallets?.total_balance)}
            icon="👛"
            iconBg="var(--brand-50)"
          />
          <MetricCard
            label="Pending Approvals"
            value={formatNumber(pendingActions?.vendor_approvals ?? 0)}
            icon="⚡"
            iconBg="var(--error-50)"
          />
        </div>
      )}

      {/* Charts Row 1 */}
      <div className="admin-chart-grid" style={{ marginBottom: 24 }}>
        {/* Revenue Chart */}
        <div className="admin-card">
          <div className="admin-card-header">
            <div>
              <div className="admin-card-title">Revenue Over Time</div>
              <div className="admin-card-subtitle">Last 30 days</div>
            </div>
          </div>
          <div className="admin-card-body" style={{ padding: '16px 8px 8px' }}>
            {loadingRevChart ? (
              <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <span className="spinner" style={{ width: 24, height: 24 }} />
              </div>
            ) : revenueData.length ? (
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={revenueData}>
                  <defs>
                    <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.15} />
                      <stop offset="95%" stopColor="#7c3aed" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${(v/1000).toFixed(0)}k`} />
                  <Tooltip formatter={(v) => formatCurrency(v)} />
                  <Area type="monotone" dataKey="revenue" stroke="#7c3aed" fill="url(#revGrad)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-tertiary)' }}>
                No data yet
              </div>
            )}
          </div>
        </div>

        {/* Pending Actions */}
        <PendingActionsCard data={pendingActions} />
      </div>

      {/* Charts Row 2 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 24 }}>
        {/* Bookings Chart */}
        <div className="admin-card">
          <div className="admin-card-header">
            <div className="admin-card-title">Bookings by Status</div>
          </div>
          <div className="admin-card-body" style={{ padding: '12px 8px 8px' }}>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={bookData.slice(-14)}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="confirmed" fill="#22c55e" radius={[2,2,0,0]} />
                <Bar dataKey="pending" fill="#f59e0b" radius={[2,2,0,0]} />
                <Bar dataKey="cancelled" fill="#ef4444" radius={[2,2,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Users Chart */}
        <div className="admin-card">
          <div className="admin-card-header">
            <div className="admin-card-title">New Users</div>
          </div>
          <div className="admin-card-body" style={{ padding: '12px 8px 8px' }}>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={userData.slice(-14)}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Line type="monotone" dataKey="registrations" stroke="#3b82f6" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Category Distribution */}
        <div className="admin-card">
          <div className="admin-card-header">
            <div className="admin-card-title">Category Distribution</div>
          </div>
          <div className="admin-card-body" style={{ padding: '12px 8px 8px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            {catData.length ? (
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={catData} dataKey="count" nameKey="name" cx="50%" cy="50%" innerRadius={50} outerRadius={80}>
                    {catData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: 200, display: 'flex', alignItems: 'center', color: 'var(--text-tertiary)' }}>No data</div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="admin-section-grid">
        <ActivityFeed data={activity} />

        {/* Platform Health */}
        {platformHealth && (
          <div className="admin-card">
            <div className="admin-card-header">
              <div className="admin-card-title">🏥 Platform Health</div>
            </div>
            <div style={{ padding: '8px 20px 16px' }}>
              {Object.entries(platformHealth).map(([key, val]) => (
                <div key={key} className="admin-data-list-item">
                  <span style={{ fontSize: 13, color: 'var(--text-secondary)', textTransform: 'capitalize' }}>
                    {key.replace(/_/g, ' ')}
                  </span>
                  <StatusBadge status={String(val)} />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
