// Presentation routes only; these do not change the backend experiment contract.
export const primaryNavigation = [
  { href: '/', title: 'Overview', mobileTitle: 'Overview', icon: 'home' },
  { href: '/compiler/', title: 'Python Compiler', mobileTitle: 'Compiler', icon: 'code' },
  { href: '/neutrinos/', title: 'Neutrino Lab', mobileTitle: 'Neutrinos', icon: 'activity' },
  { href: '/search/', title: 'Grover Search', mobileTitle: 'Search', icon: 'search' },
  { href: '/methodology/', title: 'Methodology', mobileTitle: 'Methods', icon: 'book' }
] as const;
