import { useState, useEffect } from 'react';

export function useAdminTheme() {
  const [theme, setTheme] = useState(() => localStorage.getItem('admin_theme') || 'light');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('admin_theme', theme);
  }, [theme]);

  const toggle = () => setTheme((t) => (t === 'light' ? 'dark' : 'light'));

  return { theme, toggle };
}
