// Presentation routes only; these do not change the backend experiment contract.
export const primaryNavigation = [
  { href: '/', title: 'Overview', mobileTitle: 'Overview', icon: 'home' },
  { href: '/neutrinos/', title: 'Neutrino Lab', mobileTitle: 'Neutrinos', icon: 'activity' },
  { href: '/compiler/', title: 'Python Compiler', mobileTitle: 'Compiler', icon: 'code' },
  { href: '/hardware/', title: 'Physical QPU Analytics', mobileTitle: 'QPU', icon: 'activity' },
  { href: '/methodology/', title: 'Methodology', mobileTitle: 'Methods', icon: 'book' }
] as const;
