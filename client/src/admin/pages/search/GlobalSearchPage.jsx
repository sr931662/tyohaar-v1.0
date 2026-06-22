import { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { searchApi } from '../../api';
import { useDebounce } from '../../hooks/useDebounce';

const SECTION_META = {
  vendors: { label: 'Vendors', path: '/admin/vendors', icon: '🏪' },
  customers: { label: 'Customers', path: '/admin/customers', icon: '👤' },
  bookings: { label: 'Bookings', path: '/admin/bookings', icon: '📅' },
  packages: { label: 'Packages', path: '/admin/packages', icon: '📦' },
  payments: { label: 'Payments', path: '/admin/payments', icon: '💳' },
};

export default function GlobalSearchPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [query, setQuery] = useState(searchParams.get('q') ?? '');
  const debouncedQuery = useDebounce(query, 500);

  const { data, isLoading } = useQuery({
    queryKey: ['search', debouncedQuery],
    queryFn: () => searchApi.globalSearch(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
  });

  const totalResults = data ? Object.values(data).reduce((sum, arr) => sum + (arr?.length ?? 0), 0) : 0;

  return (
    <div>
      <div className="admin-page-header">
        <div className="admin-page-header-left">
          <h1>Global Search</h1>
          <p>Search across vendors, customers, bookings, packages, and payments</p>
        </div>
      </div>

      <div className="admin-card" style={{ marginBottom: 24 }}>
        <div className="admin-card-body">
          <div className="admin-filters-search" style={{ maxWidth: 600 }}>
            <span style={{ color: 'var(--text-tertiary)', fontSize: 18 }}>⌕</span>
            <input
              autoFocus
              style={{ fontSize: 16 }}
              placeholder="Search for vendors, customers, bookings…"
              value={query}
              onChange={e => setQuery(e.target.value)}
            />
          </div>
          {debouncedQuery.length >= 2 && (
            <div style={{ marginTop: 8, fontSize: 13, color: 'var(--text-tertiary)' }}>
              {isLoading ? 'Searching…' : `${totalResults} results for "${debouncedQuery}"`}
            </div>
          )}
        </div>
      </div>

      {debouncedQuery.length < 2 && (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-tertiary)' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🔍</div>
          <div>Type at least 2 characters to search</div>
        </div>
      )}

      {data && !isLoading && Object.entries(data).map(([section, results]) => {
        if (!results?.length) return null;
        const meta = SECTION_META[section] ?? { label: section, path: `/admin/${section}`, icon: '📄' };

        return (
          <div key={section} className="admin-card" style={{ marginBottom: 16 }}>
            <div className="admin-card-header">
              <div className="admin-card-title">{meta.icon} {meta.label} ({results.length})</div>
              <button className="btn btn-secondary btn-sm" onClick={() => navigate(meta.path)}>View All</button>
            </div>
            <div className="admin-card-body" style={{ padding: 0 }}>
              <table className="admin-table">
                <tbody>
                  {results.slice(0, 5).map((item) => (
                    <tr key={item.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`${meta.path}/${item.id}`)}>
                      <td>
                        <div className="admin-user-name">{item.name ?? item.title ?? item.subject ?? item.id?.slice(0, 12)}</div>
                        {(item.email || item.customer_name || item.status) && (
                          <div className="admin-user-email">{item.email ?? item.customer_name ?? item.status}</div>
                        )}
                      </td>
                      <td style={{ width: 80, textAlign: 'right', color: 'var(--text-tertiary)', fontSize: 12 }}>→</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}

      {data && !isLoading && totalResults === 0 && (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-tertiary)' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>😶</div>
          <div>No results found for "{debouncedQuery}"</div>
        </div>
      )}
    </div>
  );
}
