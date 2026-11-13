import Link from "next/link";
import { Icon, type IconName } from "../components/icon";

const features: { icon: IconName; title: string; text: string; color: string }[] = [
  { icon: "activity", title: "Every reading, in one place", text: "Keep glucose, blood pressure, heart rate and oxygen readings together, with the time and source of each record.", color: "mint" },
  { icon: "moon", title: "More of your everyday", text: "Add sleep duration, a personal profile and meal photos to give your records everyday context.", color: "lilac" },
  { icon: "users", title: "A shared view, with consent", text: "Connect with a provisioned physician, choose what to share and return to the same records together.", color: "blue" },
];

export default function HomePage() {
  return <main className="landing" id="top">
    <a className="skip-link" href="#about">Skip to content</a>
    <div className="demo-strip"><Icon name="shield" size={14} /> Demo with synthetic data. Not for medical use.</div>
    <header className="landing-nav wrap">
      <Link className="brand" href="/"><span className="brand-mark"><Icon name="activity" size={23} /></span><span>rpm<span className="brand-light"> platform</span></span></Link>
      <nav aria-label="Main navigation"><a href="#features">The platform</a><a href="#how-it-works">How it works</a><a href="#access">For patients & physicians</a></nav>
      <Link href="/login" className="nav-cta">Sign in <Icon name="arrow" size={16} /></Link>
    </header>
    <section className="hero wrap" id="about">
      <div className="hero-copy">
        <p className="eyebrow"><span /> HEALTH RECORDS. HUMAN CONTEXT.</p>
        <h1>Your everyday health.<br/><em>A clearer picture.</em></h1>
        <p className="hero-intro">A shared space for patients and physicians to explore diabetes and hypertension monitoring. Bring readings, sleep and everyday context together, one check-in at a time.</p>
        <div className="hero-actions"><Link href="/register" className="button-dark">Explore as a patient <Icon name="arrow" size={18} /></Link><Link href="/physician-access" className="button-outline">Physician account setup <Icon name="arrow" size={18} /></Link></div>
        <div className="hero-note"><Icon name="shield" size={24} /><p><strong>Built for learning. Designed around people.</strong><br/>An educational prototype using fictional information only.</p></div>
      </div>
      <div className="hero-art" aria-label="Illustrative preview of the patient workspace, using example data">
        <div className="art-grid" aria-hidden="true" />
        <div className="preview-card">
          <div className="preview-head"><span className="preview-logo"><Icon name="activity" size={20} /> rpm</span><span className="preview-tag">ILLUSTRATIVE PREVIEW</span></div>
          <div className="preview-welcome"><div><span>YOUR PERSONAL OVERVIEW</span><h2>A little more clarity.</h2><p>Make room for a daily check-in.</p></div><span className="preview-avatar"><Icon name="user" size={20} /></span></div>
          <div className="preview-metrics"><div><span className="preview-metric-icon mint"><Icon name="activity" /></span><strong>Readings</strong><small>Recorded with context</small></div><div><span className="preview-metric-icon lilac"><Icon name="moon" /></span><strong>Sleep</strong><small>Your reported hours</small></div></div>
          <div className="preview-chart"><div><strong>See your history</strong><span>Example only</span></div><svg aria-hidden="true" viewBox="0 0 320 90" fill="none"><path d="M0 20H320M0 45H320M0 70H320" stroke="#e7efeb" strokeDasharray="4 4"/><path d="M0 65C20 65 25 28 45 35S75 70 95 51 125 61 145 39 175 32 195 46 225 27 245 35 280 14 320 27" stroke="#248271" strokeWidth="3"/><path d="M0 65C20 65 25 28 45 35S75 70 95 51 125 61 145 39 175 32 195 46 225 27 245 35 280 14 320 27V90H0Z" fill="#e9f5ef" opacity=".6"/></svg><div className="preview-days"><span>MON</span><span>TUE</span><span>WED</span><span>THU</span><span>FRI</span><span>SAT</span><span>SUN</span></div></div>
          <div className="preview-team"><span className="preview-metric-icon blue"><Icon name="users" /></span><div><strong>Your care team</strong><p>Connected through your consent</p></div><Icon name="arrow" size={17} /></div>
        </div>
        <div className="floating-card"><span><Icon name="check" size={18} /></span><div><strong>A shared view of your records</strong><small>Patient + physician workspaces</small></div></div>
        <div className="art-caption"><Icon name="shield" size={14} /> Synthetic preview · No clinical interpretation</div>
      </div>
    </section>
    <div className="platform-strip wrap"><span>A place for the whole picture</span><div><Icon name="activity" size={18} /> Readings</div><div><Icon name="moon" size={18} /> Sleep</div><div><Icon name="meal" size={18} /> Meal photos</div><div><Icon name="users" size={18} /> Care team</div></div>
    <section className="features wrap" id="features"><div className="section-top"><div><p className="eyebrow">LESS SCATTERED. MORE CONNECTED.</p><h2>The details that help<br/><em>tell your story.</em></h2></div><p>Purposeful tools for recording, sharing and reviewing synthetic health information.</p></div><div className="feature-grid">{features.map((feature) => <article className="feature" key={feature.title}><span className={`feature-icon ${feature.color}`}><Icon name={feature.icon} size={25} /></span><h3>{feature.title}</h3><p>{feature.text}</p></article>)}</div></section>
    <section className="how-section" id="how-it-works"><div className="wrap"><div className="section-top"><div><p className="eyebrow">A SIMPLE WAY TO STAY ORGANIZED</p><h2>From daily check-in<br/><em>to shared context.</em></h2></div><p>Different workspaces. The same source records. Clear permissions at every step.</p></div><ol className="steps-grid"><li><span>01</span><h3>Make it your space</h3><p>Create a patient account and add a fictional profile, photo and personal details.</p></li><li><span>02</span><h3>Build your daily record</h3><p>Log readings and sleep, upload meal photos, and explore your history over time.</p></li><li><span>03</span><h3>Connect with a physician</h3><p>Choose a provisioned physician and grant consent. Authorized records become available in their workspace.</p></li></ol></div></section>
    <section className="access wrap" id="access"><div><p className="eyebrow">FIND YOUR WORKSPACE</p><h2>One platform.<br/><em>Two perspectives.</em></h2><p>Explore the demo from your side of the conversation.</p><div className="access-note"><Icon name="shield" size={20} /><span>Physician access requires an invitation and multi-factor authentication.</span></div></div><div className="access-cards"><article><span className="access-symbol mint"><Icon name="heart" size={26} /></span><p className="access-role">FOR PATIENTS</p><h3>Your day, in context.</h3><p>Set up your profile, record your check-ins and choose your care connections.</p><Link href="/register">Create patient account <Icon name="arrow" size={18} /></Link><Link className="access-secondary" href="/login?role=patient">Already registered? Sign in</Link></article><article className="physician-access-card"><span className="access-symbol blue"><Icon name="users" size={26} /></span><p className="access-role">FOR PHYSICIANS</p><h3>A focused review space.</h3><p>Find connected patients, review source records and manage persisted demo alerts.</p><Link href="/physician-access">Create physician account <Icon name="arrow" size={18} /></Link><Link className="access-secondary" href="/login?role=physician">Physician sign in</Link></article></div></section>
    <footer className="landing-footer"><div className="wrap footer-inner"><div><Link className="brand" href="/"><span className="brand-mark"><Icon name="activity" size={23} /></span><span>rpm<span className="brand-light"> platform</span></span></Link><p>Everyday records. Shared understanding.</p></div><p>Demo with synthetic data. Not for medical use.<br/>Not an emergency service. No clinical validation is claimed.</p><a href="#top" className="back-top" aria-label="Back to top">↑</a></div></footer>
  </main>;
}
