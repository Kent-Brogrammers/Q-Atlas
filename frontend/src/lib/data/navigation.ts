// Presentation routes only; these do not change the backend experiment contract.
export const primaryNavigation = [
  { href: '/', title: 'Overview', icon: 'home' },
  { href: '/compiler/', title: 'Python Compiler', icon: 'code' },
  { href: '/neutrinos/', title: 'Neutrino Lab', icon: 'activity' },
  { href: '/search/', title: 'Grover Search', icon: 'search' },
  { href: '/methodology/', title: 'Methodology', icon: 'book' }
] as const;
