import { CoachChat } from './index.js';
import IntersectionScene from './IntersectionScene.jsx';
import { scenarios } from '../data/drivingScenarios.js';
import { useState } from 'react';

export default function LearningWorkspace() {
  const [scenarioId, setScenarioId] = useState('four_way_stop');
  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="DriveWise AI home">
          <span className="brand-mark" aria-hidden="true">↗</span><span>DriveWise <small>AI</small></span>
        </a>
        <div className="topbar-right"><span className="practice-tag"><i />Practice mode</span><a href="#quick-rules">Quick rules <span>↗</span></a></div>
      </header>
      <nav className="main-nav" aria-label="Main navigation">
        <a className="nav-active" href="#studio">Learning Studio</a>
        <a href="#sample-prompts">Practice prompts</a>
        <a href="#scene">Intersection scene</a>
      </nav>
      <main id="top">
        <section className="hero" id="studio">
          <div className="hero-content">
            <div className="eyebrow"><span className="eyebrow-dot" />LEARNING STUDIO <span>/</span> RIGHT-OF-WAY BASICS</div>
            <h1>Make your next move<br /><em>with confidence.</em></h1>
            <p>Practice four-way-stop decisions with a calm driving coach and a clear intersection walkthrough.</p>
            <div className="hero-actions"><a className="hero-button" href="#conversation">Continue practice <span>↗</span></a><a className="hero-link" href="#scene">Explore the intersection <span>↓</span></a></div>
          </div>
          <div className="hero-art" aria-hidden="true"><div className="sun-disc" /><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="mini-road"><span /><i /><b>STOP</b></div><div className="hero-car">DW</div><div className="spark spark-one">✦</div><div className="spark spark-two">✳</div><span className="art-label">A LITTLE PRACTICE<br />GOES A LONG WAY</span></div>
        </section>
        <div className="section-intro"><div><span className="section-kicker">TODAY’S LESSON</span><h2>Four-way stop fundamentals</h2></div><span className="lesson-progress">LESSON 01 <i /> FOUR-WAY STOP</span></div>
        <div className="workspace-grid">
          <CoachChat onScenarioChange={setScenarioId} />
          <IntersectionScene scenarioId={scenarioId} />
        </div>
        <section className="quick-rules" id="quick-rules">
          <div className="rules-heading"><span className="rules-icon">✦</span><div><span className="section-kicker">KEEP IN MIND</span><h2>Three things before you go</h2></div></div>
          <div className="rule-list"><div><b>01</b><span>Come to a complete stop.</span></div><div><b>02</b><span>Check every approach and the crosswalk.</span></div><div><b>03</b><span>Move only when it’s your turn and safe.</span></div></div>
        </section>
      </main>
      <footer><span className="footer-brand">DriveWise <small>AI</small></span><span>Practice makes safer decisions. <i>Always follow local traffic laws.</i></span><span className="footer-local"><i />Local practice experience</span></footer>
    </div>
  );
}
