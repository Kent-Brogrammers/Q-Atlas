// Presentation routes only; these do not change the backend experiment contract.
export const primaryNavigation = [
  { href: '/', title: 'Overview', icon: 'home' },
  { href: '/neutrinos/', title: 'Neutrino Lab', icon: 'activity' },
  { href: '/methodology/', title: 'Methodology', icon: 'book' }
] as const;
