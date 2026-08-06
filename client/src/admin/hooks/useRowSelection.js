import { useEffect, useState } from 'react';

/**
 * Generalizes the selected/toggleAll/toggleItem trio hand-rolled per-page
 * (PackagesPage, VendorsPage) into one hook, plus clears selection whenever
 * any of `resetKeys` changes (page, search, filters) so a bulk action can
 * never fire against a stale selection hidden on a page the admin left.
 */
export function useRowSelection(items, resetKeys = []) {
  const [selected, setSelected] = useState([]);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { setSelected([]); }, resetKeys);

  const toggleItem = (id) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const toggleAll = () =>
    setSelected((s) => (s.length === items.length && items.length > 0 ? [] : items.map((i) => i.id)));

  const clear = () => setSelected([]);

  return {
    selected,
    toggleItem,
    toggleAll,
    clear,
    isAllSelected: items.length > 0 && selected.length === items.length,
    isSomeSelected: selected.length > 0 && selected.length < items.length,
  };
}
