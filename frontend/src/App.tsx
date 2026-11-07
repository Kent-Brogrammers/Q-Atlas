import { NavLink, Route, Routes } from 'react-router-dom';
import CompilerPage from './pages/CompilerPage';
import DashboardPage from './pages/DashboardPage';
import MaterialsPage from './pages/MaterialsPage';
import OptimizationPage from './pages/OptimizationPage';
import SearchPage from './pages/SearchPage';

const links = [
  ['/', 'Overview'], ['/compiler', 'Compiler'], ['/materials', 'Materials'],
  ['/optimization', 'Optimization'], ['/search', 'Search'],
] as const;

export default function App() {
  return (
    <div className="mx-auto max-w-5xl px-5 py-8">
      <header className="mb-8 border-b border-slate-200 pb-6">
        <p className="text-sm font-semibold uppercase tracking-widest text-indigo-700">Q-Atlas</p>
        <p className="mt-2 text-slate-600">Quantum experiments, measured honestly.</p>
        <nav aria-label="Main navigation" className="mt-5 flex flex-wrap gap-2">
          {links.map(([path, label]) => (
            <NavLink key={path} to={path} end={path === '/'} className={({ isActive }) =>
              `rounded-md px-3 py-2 text-sm ${isActive ? 'bg-indigo-700 text-white' : 'bg-white text-slate-700 hover:bg-slate-100'}`
            }>{label}</NavLink>
          ))}
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/compiler" element={<CompilerPage />} />
          <Route path="/materials" element={<MaterialsPage />} />
          <Route path="/optimization" element={<OptimizationPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="*" element={<h1 className="text-2xl font-semibold">Page not found</h1>} />
        </Routes>
      </main>
      <footer className="mt-10 border-t border-slate-200 pt-4 text-sm text-slate-500">
        Development foundation · Aer simulator only · No experimental measurements yet
      </footer>
    </div>
  );
}
