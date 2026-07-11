// Primary navigation anchors for the marketing site.
export const navLinks = [
  { label: 'Occasions', href: '#occasions' },
  { label: 'How it works', href: '#how' },
  { label: 'Partners', href: '#partners' },
  { label: 'Stories', href: '#stories' },
  // Vendor/staff login — an app route (not an in-page anchor), rendered as a
  // React Router Link so switching to it is a client-side transition.
  { label: 'Workspace', href: '/workspace/login', isRoute: true },
];

export const footerColumns = [
  {
    title: 'Product',
    links: [
      { label: 'Occasions', href: '#occasions' },
      { label: 'How it works', href: '#how' },
      { label: 'Partners', href: '#partners' },
      { label: 'Pricing', href: '#' },
    ],
  },
  {
    title: 'For partners',
    links: [
      { label: 'Become a partner', href: '#' },
      { label: 'Partner login', href: '#' },
      { label: 'Standards & vetting', href: '#' },
    ],
  },
  {
    title: 'Company',
    links: [
      { label: 'Our story', href: '/about' },
      { label: 'Careers', href: '#' },
      { label: 'Press', href: '#' },
      { label: 'Contact', href: '#' },
    ],
  },
];
