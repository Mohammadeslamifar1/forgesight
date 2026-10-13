import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowUpRight,
  ChartNoAxesCombined,
  ChevronRight,
  CircleDot,
  Database,
  Focus,
  Layers3,
  Menu,
  ScanLine,
  ShieldCheck,
  X,
} from 'lucide-react';
import { api, percent } from './api';
import type { Benchmark, Inspection, Model } from './types';
import Workbench from './Workbench';
import { BenchmarkPage, HistoryPage, ModelPage } from './Pages';

type Page = 'inspect' | 'benchmark' | 'model' | 'history';
const nav = [
  { id: 'inspect' as const, label: 'Inspection studio', icon: ScanLine },
  { id: 'benchmark' as const, label: 'Model performance', icon: ChartNoAxesCombined },
  { id: 'model' as const, label: 'Model card', icon: Layers3 },
  { id: 'history' as const, label: 'Inspection history', icon: Database },
];
function route(): Page {
  const value = location.hash.slice(1);
  return nav.some((n) => n.id === value) ? (value as Page) : 'inspect';
}

export default function App() {
  const [page, setPage] = useState<Page>(route);
  const [menu, setMenu] = useState(false);
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const model = useQuery({
    queryKey: ['model'],
    queryFn: () =>
      api<{ metadata: Model | null; error: string | null; runtime_device: string }>('/model'),
  });
  const benchmark = useQuery({
    queryKey: ['benchmark'],
    queryFn: () => api<Benchmark>('/benchmark'),
    retry: false,
  });
  useEffect(() => {
    const update = () => setPage(route());
    window.addEventListener('hashchange', update);
    return () => window.removeEventListener('hashchange', update);
  }, []);
  const navigate = (next: Page) => {
    location.hash = next;
    setPage(next);
    setMenu(false);
  };
  const current = nav.find((n) => n.id === page)!;
  return (
    <div className="app">
      <a
        href="#content"
        className="skip-link"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById('content')?.focus();
        }}
      >
        Skip to content
      </a>
      {menu && (
        <button className="backdrop" aria-label="Close navigation" onClick={() => setMenu(false)} />
      )}
      <aside className={`sidebar ${menu ? 'open' : ''}`}>
        <div className="brand">
          <span className="brand-mark">
            <Focus size={25} strokeWidth={1.6} />
          </span>
          <span>
            ForgeSight<span className="brand-caption">VISUAL INTELLIGENCE</span>
          </span>
        </div>
        <div className="workspace">
          <span className="workspace-icon">
            <Layers3 size={18} />
          </span>
          <span>
            <strong>Inspection lab</strong>
            <small>Local workspace</small>
          </span>
          <span className="status-dot" />
        </div>
        <div className="nav-label">WORKBENCH</div>
        <nav aria-label="Main navigation">
          {nav.map((item) => (
            <button
              key={item.id}
              onClick={() => navigate(item.id)}
              className={`nav-item ${page === item.id ? 'active' : ''}`}
              aria-current={page === item.id ? 'page' : undefined}
            >
              <item.icon size={18} />
              <span>{item.label}</span>
              {page === item.id && <ChevronRight size={15} />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <ShieldCheck size={22} />
            <strong>Evidence before decisions.</strong>
            <p>
              A model flags the unusual.
              <br />
              You decide what it means.
            </p>
            <button onClick={() => navigate('model')}>
              Explore the model <ArrowUpRight size={14} />
            </button>
          </div>
          <div className="sidebar-footer">
            <CircleDot size={15} />
            <span>LOCAL INFERENCE</span>
            <span className="version">v0.1</span>
          </div>
        </div>
      </aside>
      <div className="shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon mobile-toggle"
              aria-label={menu ? 'Close navigation' : 'Open navigation'}
              onClick={() => setMenu(!menu)}
            >
              {menu ? <X size={20} /> : <Menu size={20} />}
            </button>
            <span>Inspection lab</span>
            <ChevronRight size={13} />
            <strong>{current.label}</strong>
          </div>
          <div className="topbar-status">
            <span className="status-dot" />
            {model.data?.metadata ? 'Model online' : 'Model setup'}
            <span className="topbar-divider" />
            {model.data?.runtime_device.toUpperCase() || '—'} · Local
          </div>
        </header>
        <main id="content" tabIndex={-1}>
          {model.isPending ? (
            <div className="empty-state">
              <div className="spinner" />
              <h1>Connecting to the lab</h1>
            </div>
          ) : model.error ? (
            <div className="empty-state" role="alert">
              <h1>The API is unavailable</h1>
              <p>Start run.py in PyCharm, then try again.</p>
              <button className="button primary" onClick={() => void model.refetch()}>
                Retry connection
              </button>
            </div>
          ) : !model.data?.metadata ? (
            <div className="empty-state">
              <Focus size={44} />
              <h1>Your inspection lab starts here.</h1>
              <p>Download the benchmark, fit the normal-only model, and measure it.</p>
              <code>python -m forgesight.cli setup</code>
              <p>Then restart the server to load the model.</p>
              <small>{model.data?.error}</small>
            </div>
          ) : (
            <>
              {page === 'inspect' && (
                <>
                  <div className="page-heading">
                    <div>
                      <div className="eyebrow">
                        <span /> PERCEPTION / INSPECTION STUDIO
                      </div>
                      <h1>
                        Anomalies, in focus<span className="orange">.</span>
                      </h1>
                      <p>
                        From normal appearance to visible evidence. Inspect a part, understand the
                        result.
                      </p>
                    </div>
                    <span className="dataset-tag">
                      <span className="tiny-square" /> MVTec AD / Bottle
                    </span>
                  </div>
                  <div className="metrics-strip">
                    <div>
                      <span className="metric-label">FEATURE ENCODER</span>
                      <strong>
                        ResNet-18 <small>FROZEN</small>
                      </strong>
                    </div>
                    <div>
                      <span className="metric-label">IMAGE AUROC</span>
                      <strong>
                        {percent(benchmark.data?.image_auroc)} <small>HELD-OUT TEST</small>
                      </strong>
                    </div>
                    <div>
                      <span className="metric-label">LOCALIZATION AUROC</span>
                      <strong>
                        {percent(benchmark.data?.pixel_auroc)} <small>PIXEL LEVEL</small>
                      </strong>
                    </div>
                    <div>
                      <span className="metric-label">NORMAL TRAINING IMAGES</span>
                      <strong>
                        {model.data.metadata.fit_count} <small>NO DEFECT LABELS</small>
                      </strong>
                    </div>
                  </div>
                  <Workbench
                    model={model.data.metadata}
                    result={inspection}
                    setResult={setInspection}
                  />
                </>
              )}
              {page === 'benchmark' && (
                <BenchmarkPage
                  report={benchmark.data}
                  error={benchmark.error?.message}
                  model={model.data.metadata}
                />
              )}
              {page === 'model' && <ModelPage model={model.data.metadata} />}
              {page === 'history' && (
                <HistoryPage
                  onOpen={(value) => {
                    setInspection(value);
                    navigate('inspect');
                  }}
                />
              )}
            </>
          )}
          <footer className="page-footer">
            <span>
              FORGESIGHT <span className="footer-separator">/</span> An inspection system you can
              interrogate.
            </span>
            <span>Research prototype · Human review required</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
