import './LandingPage.css'

const BrandMark = () => (
  <>
    Banks-
    <span style={{ display: 'inline-block', transform: 'scaleX(-1)' }}>R</span>
    -Us
  </>
)

const NAV_LINKS = ['Personal', 'Wealth', 'Corporate', 'Markets', 'Insights']

const TRUST_ITEMS = [
  { label: 'Regulatory', icon: 'bank' },
  { label: 'Partner Inst.', icon: 'shield-check' },
  { label: 'Secure Data', icon: 'shield' },
  { label: 'Compliance', icon: 'gavel' },
]

function TrustIcon({ name }) {
  switch (name) {
    case 'bank':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M3 10.5 12 4l9 6.5M4.5 10.5v8M9 10.5v8M15 10.5v8M19.5 10.5v8M2.5 20.5h19" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )
    case 'gavel':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="m9 6 7 7M4 20l5-5M13.5 3.5l7 7-3 3-7-7 3-3ZM6.5 12.5l5 5-3 3-5-5 3-3Z" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )
    case 'shield-check':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3Z" strokeLinejoin="round" />
          <path d="m9 12 2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )
    default:
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3Z" strokeLinejoin="round" />
        </svg>
      )
  }
}

export default function LandingPage({ onLogin, onGetStarted }) {
  return (
    <div className="landing">
      <header className="landing-header">
        <div className="landing-header-inner">
          <div className="landing-brand">
            <BrandMark />
          </div>

          <div className="landing-actions">
            <button type="button" className="landing-login-btn" onClick={onLogin}>
              Login
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M14 5l7 7-7 7M4 12h16" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      <main>
        <section className="landing-hero">
          <div className="hero-glow" aria-hidden="true" />
          <div className="landing-hero-inner">
            <h1 className="hero-title">
              Private Banking &amp; Global Wealth Management
            </h1>
            <p className="hero-subtitle">
              Delivering institutional precision and tailored strategies to
              safeguard and accelerate multi-generational wealth.
            </p>
            <div className="hero-buttons">
              <button type="button" className="hero-btn-primary" onClick={onGetStarted}>
                Get Started
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M5 12h14M13 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
              <a href="#features" className="hero-btn-secondary">
                Learn More
              </a>
            </div>
          </div>
        </section>

        <section className="trust-bar">
          {TRUST_ITEMS.map((item) => (
            <div key={item.label} className="trust-item">
              <TrustIcon name={item.icon} />
              <span>{item.label}</span>
            </div>
          ))}
        </section>

        <section id="features" className="landing-features">
          <div className="features-heading">
            <h2>Uncompromising Standards</h2>
            <p>
              Our architecture is built on the pillars of absolute security,
              bespoke management, and unrestricted access to global
              opportunities.
            </p>
          </div>

          <div className="features-grid">
            <div className="feature-card feature-security">
              <div className="feature-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <rect x="5" y="11" width="14" height="9" rx="1.5" />
                  <path d="M8 11V7a4 4 0 0 1 8 0v4" strokeLinecap="round" />
                </svg>
              </div>
              <h3>Institutional Security</h3>
              <p>
                Military-grade encryption and multi-layered authentication
                protocols ensure your assets and data remain impenetrable.
                Built for the highest stakes.
              </p>
              <div className="feature-graphic feature-graphic-mesh" aria-hidden="true">
                <svg viewBox="0 0 400 140" preserveAspectRatio="none">
                  <g stroke="rgba(178,200,235,0.5)" strokeWidth="1">
                    <line x1="20" y1="100" x2="120" y2="40" />
                    <line x1="120" y1="40" x2="220" y2="70" />
                    <line x1="220" y1="70" x2="320" y2="30" />
                    <line x1="120" y1="40" x2="180" y2="110" />
                    <line x1="220" y1="70" x2="300" y2="110" />
                    <line x1="20" y1="100" x2="180" y2="110" />
                    <line x1="300" y1="110" x2="380" y2="60" />
                  </g>
                  <g fill="#b0c8eb">
                    <circle cx="20" cy="100" r="3.5" />
                    <circle cx="120" cy="40" r="3.5" />
                    <circle cx="220" cy="70" r="4.5" />
                    <circle cx="320" cy="30" r="3.5" />
                    <circle cx="180" cy="110" r="3.5" />
                    <circle cx="300" cy="110" r="3.5" />
                    <circle cx="380" cy="60" r="3.5" />
                  </g>
                </svg>
              </div>
            </div>

            <div className="feature-card feature-portfolio">
              <div className="feature-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <circle cx="12" cy="12" r="9" />
                  <path d="M12 3v9l7.79 4.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <h3>Tailored Portfolio Management</h3>
              <p>
                Bespoke investment strategies designed by elite analysts,
                aligning precisely with your risk tolerance and
                multi-generational objectives.
              </p>
              <div className="feature-bars">
                {[
                  ['Equities', 45],
                  ['Fixed Income', 35],
                  ['Alternatives', 20],
                ].map(([label, pct]) => (
                  <div key={label} className="feature-bar-row">
                    <div className="feature-bar-label">
                      <span>{label}</span>
                      <span className="feature-bar-pct">{pct}%</span>
                    </div>
                    <div className="feature-bar-track">
                      <div className="feature-bar-fill" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="feature-card feature-markets">
              <div className="feature-markets-text">
                <div className="feature-icon feature-icon-dark">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="12" cy="12" r="9" />
                    <path d="M3 12h18M12 3c2.5 2.7 4 6 4 9s-1.5 6.3-4 9c-2.5-2.7-4-6-4-9s1.5-6.3 4-9Z" />
                  </svg>
                </div>
                <h3>Global Market Access</h3>
                <p>
                  Direct execution capabilities across major global
                  exchanges, private equity opportunities, and emerging
                  markets, providing unparalleled liquidity and
                  diversification.
                </p>
                <a href="#features" className="feature-link">
                  Explore Markets
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M5 12h14M13 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </a>
              </div>
              <div className="feature-graphic feature-graphic-chart" aria-hidden="true">
                <svg viewBox="0 0 400 160" preserveAspectRatio="none">
                  <polyline
                    points="0,130 50,120 90,135 140,90 190,100 240,55 290,70 340,30 400,45"
                    fill="none"
                    stroke="#0762ff"
                    strokeWidth="2.5"
                  />
                  <polyline
                    points="0,130 50,120 90,135 140,90 190,100 240,55 290,70 340,30 400,45"
                    fill="url(#chartFade)"
                    stroke="none"
                  />
                  <defs>
                    <linearGradient id="chartFade" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#0762ff" stopOpacity="0.25" />
                      <stop offset="100%" stopColor="#0762ff" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                </svg>
              </div>
            </div>
          </div>
        </section>

        <section className="landing-about">
          <div className="about-visual" aria-hidden="true">
            <div className="about-visual-glow" />
          </div>
          <div className="about-text">
            <h2>Heritage of Excellence</h2>
            <p>
              For over decades, Banks-Я-Us has navigated complex financial
              landscapes with absolute discretion and technical rigor. We
              believe true wealth management requires a synthesis of deep
              market intelligence and personalized structural planning.
            </p>
            <p className="about-muted">
              Our commitment is to be the steadfast anchor for your legacy,
              ensuring precision in every transaction and clarity in every
              strategy.
            </p>
            <a href="#features" className="about-link">
              Read Our Manifesto
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M5 12h14M13 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </a>
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <div className="footer-top">
          <div className="footer-brand">
            <BrandMark />
          </div>
          <nav className="footer-links">
            <a href="#features">Privacy Policy</a>
            <a href="#features">Security</a>
            <a href="#features">Terms of Service</a>
            <a href="#features">Regulatory Disclosures</a>
            <a href="#features">Sitemap</a>
            <a href="#features">Contact Us</a>
          </nav>
        </div>
        <p className="footer-copyright">
          © {new Date().getFullYear()} Banks-Я-Us Institutional Banking. All
          rights reserved. Member FDIC. Equal Housing Lender.
        </p>
      </footer>
    </div>
  )
}
