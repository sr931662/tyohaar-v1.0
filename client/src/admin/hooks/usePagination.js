import { useState } from 'react';

export function usePagination(initialPage = 1, initialPerPage = 20) {
  const [page, setPage] = useState(initialPage);
  const [perPage] = useState(initialPerPage);

  const reset = () => setPage(1);

  return { page, perPage, setPage, reset };
}
