import { useEffect, useState } from 'react';

const ROADMAP = ['Upload', 'Analyse', 'Wardrobe', 'Recommend', 'Learn', 'Stylist'];

export default function App() {
  const [api, setApi] = useState({ state: 'checking' });

  useEffect(() => {
    fetch('/api/health')
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data) => setApi({ state: 'online', data }))
      .catch(() => setApi({ state: 'offline' }));
  }, []);

  return (
    <main className="shell">
      <div className="glow" aria-hidden="true" />
      <section className="hero">
        <span className="eyebrow">AI-Powered Personal Styling</span>
        <h1 className="logo">SLAYIN</h1>
        <p className="tagline">Your wardrobe, understood. Your outfits, elevated.</p>

        <div id="api-status" className={`status status--${api.state}`}>
          <span className="dot" />
          {api.state === 'checking' && 'Connecting to API…'}
          {api.state === 'online' && `API online · ${api.data.env}`}
          {api.state === 'offline' && 'API offline — run: python -m src.main'}
        </div>

        <ol className="roadmap">
          {ROADMAP.map((step, i) => (
            <li key={step} style={{ animationDelay: `${i * 80}ms` }}>
              <span>{String(i + 1).padStart(2, '0')}</span>
              {step}
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}
