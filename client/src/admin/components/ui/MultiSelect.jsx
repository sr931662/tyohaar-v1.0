import { useMemo, useRef, useState } from 'react';

/**
 * Searchable multi-select with removable chips. Options: [{value, label}].
 * value: array of selected option values (strings). onChange(newArray).
 *
 * Built for entity-scope pickers (vendors/packages/occasions/membership
 * tiers) where options come from an existing list endpoint — this
 * component only handles selection UI, callers own fetching `options`.
 */
export default function MultiSelect({ options = [], value = [], onChange, placeholder = 'Search…', loading = false, disabled = false }) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const inputRef = useRef(null);

  const selectedSet = useMemo(() => new Set(value), [value]);
  const labelFor = (v) => options.find((o) => o.value === v)?.label ?? v;

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return options
      .filter((o) => !selectedSet.has(o.value))
      .filter((o) => !q || o.label.toLowerCase().includes(q))
      .slice(0, 50);
  }, [options, selectedSet, query]);

  const addValue = (v) => {
    onChange([...value, v]);
    setQuery('');
    inputRef.current?.focus();
  };

  const removeValue = (v) => {
    onChange(value.filter((x) => x !== v));
  };

  return (
    <div style={{ position: 'relative' }}>
      <div
        className="form-control"
        style={{
          display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center',
          minHeight: 40, padding: '6px 8px', cursor: disabled ? 'not-allowed' : 'text',
        }}
        onClick={() => !disabled && inputRef.current?.focus()}
      >
        {value.map((v) => (
          <span
            key={v}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 4,
              background: 'var(--brand-100)', color: 'var(--brand-700)',
              borderRadius: 12, padding: '2px 8px', fontSize: 12, fontWeight: 600,
            }}
          >
            {labelFor(v)}
            {!disabled && (
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); removeValue(v); }}
                style={{ border: 'none', background: 'none', cursor: 'pointer', color: 'var(--brand-700)', fontSize: 13, lineHeight: 1, padding: 0 }}
              >
                ✕
              </button>
            )}
          </span>
        ))}
        <input
          ref={inputRef}
          disabled={disabled}
          value={query}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          placeholder={value.length ? '' : placeholder}
          style={{ border: 'none', outline: 'none', flex: 1, minWidth: 100, fontSize: 13, background: 'transparent', color: 'var(--text-primary)' }}
        />
      </div>
      {open && !disabled && (
        <div
          style={{
            position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 20,
            marginTop: 4, maxHeight: 220, overflowY: 'auto',
            background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
            borderRadius: 8, boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
          }}
        >
          {loading ? (
            <div style={{ padding: '10px 12px', fontSize: 12.5, color: 'var(--text-tertiary)' }}>Loading…</div>
          ) : filtered.length === 0 ? (
            <div style={{ padding: '10px 12px', fontSize: 12.5, color: 'var(--text-tertiary)' }}>No matches</div>
          ) : (
            filtered.map((o) => (
              <div
                key={o.value}
                onMouseDown={(e) => { e.preventDefault(); addValue(o.value); }}
                style={{ padding: '8px 12px', fontSize: 13, cursor: 'pointer', color: 'var(--text-primary)' }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--bg-base)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
              >
                {o.label}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
