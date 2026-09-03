import { ArrowRight, Check, ChevronDown, Menu, Play, ShieldCheck, Sparkles, X, Zap } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Brand } from '../components/Brand'

const steps = [
  ['01', 'Connect the work', 'Bring requirements, test cases and environments into one shared verification record.'],
  ['02', 'Run with context', 'Execute repeatable suites while every result stays tied to the right release.'],
  ['03', 'Capture the proof', 'Collect outcomes, evidence and issues as the verification work happens.'],
  ['04', 'Ship with confidence', 'Review a clear, defensible verdict and align every stakeholder.'],
]
const features = [
  ['Traceable by design', 'Follow the path from requirement to test, evidence, issue and final verdict.'],
  ['Evidence that stays useful', 'Keep screenshots, logs and results with the execution that produced them.'],
  ['A calmer command centre', 'See release health, risk and coverage without another status spreadsheet.'],
  ['Built for real workflows', 'Structure projects, suites, cases and environments around your team.'],
  ['Fast, focused triage', 'Turn failed checks into actionable issues while every detail is close at hand.'],
  ['Intelligence with context', 'Surface patterns and gaps from your own connected verification record.'],
]
const faqs = [
  ['What is VeriGate?', 'VeriGate is a verification command centre connecting test planning, execution, evidence, issues and release decisions in one traceable workspace.'],
  ['Is it only for automated testing?', 'No. VeriGate supports automated, manual and exploratory verificationâ€”the goal is a complete record of what was checked and what the evidence proves.'],
  ['Can I use my current tools?', 'Yes. VeriGate is designed to sit across your existing delivery workflow. Integration availability will expand as the platform develops.'],
  ['How does VeriGate protect project data?', 'VeriGate uses authenticated workspaces and a security-first architecture. Deployment-specific compliance and retention details will be published before general availability.'],
]

function BackgroundEffects() {
  const canvasRef = useRef(null)
  useEffect(() => {
    const canvas = canvasRef.current, context = canvas?.getContext('2d')
    if (!canvas || !context) return
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)'), mobile = window.matchMedia('(max-width: 700px)')
    let width, height, dpr, frame, start = performance.now(), visible = !document.hidden, pointerX = 0, pointerY = 0, targetX = 0, targetY = 0
    const hash = (x, y, z) => { const value = Math.sin(x * 127.1 + y * 311.7 + z * 74.7) * 43758.5453; return value - Math.floor(value) }
    const smooth = value => value * value * (3 - 2 * value)
    const noise = (x, y, z) => { const xi=Math.floor(x), yi=Math.floor(y), zi=Math.floor(z), xf=smooth(x-xi), yf=smooth(y-yi), zf=smooth(z-zi); const mix=(a,b,t)=>a+(b-a)*t; const layer = dz => mix(mix(hash(xi,yi,zi+dz),hash(xi+1,yi,zi+dz),xf),mix(hash(xi,yi+1,zi+dz),hash(xi+1,yi+1,zi+dz),xf),yf); return mix(layer(0),layer(1),zf) * 2 - 1 }
    const field = (x, z, time) => noise(x*.72,z*.72,time*.11)*1.15 + noise(x*1.55+8,z*1.55-3,time*.17)*.42 + noise(x*3.2-4,z*3.2+7,time*.08)*.12
    const resize = () => { width=window.innerWidth; height=window.innerHeight; dpr=Math.min(window.devicePixelRatio||1,mobile.matches?1.25:1.6); canvas.width=Math.round(width*dpr); canvas.height=Math.round(height*dpr); canvas.style.width=`${width}px`; canvas.style.height=`${height}px`; context.setTransform(dpr,0,0,dpr,0,0) }
    const project = (x,z,y,scroll,time) => { const scale=Math.max(width,height)*.17*(1+scroll*.08), depth=5.4+z*.34, perspective=3.8/depth; return { x:width*.5+(x+pointerX*.16+scroll*.7)*scale*perspective, y:height*.5+(z*.37-y*.8-1.0+pointerY*.12-scroll*.28+Math.sin(time*.07)*.04)*scale*perspective } }
    const draw = now => { if (!visible) return; const time=reduced.matches?0:(now-start)/1000, scroll=Math.min(1,window.scrollY/Math.max(1,document.documentElement.scrollHeight-height)); targetX+=(pointerX-targetX)*.04; targetY+=(pointerY-targetY)*.04; pointerX=targetX; pointerY=targetY; context.clearRect(0,0,width,height); const cols=mobile.matches?25:42, rows=mobile.matches?19:30, points=[]; for(let row=0;row<rows;row++){ const line=[]; for(let col=0;col<cols;col++){ const baseX=(col/(cols-1)-.5)*12.8, baseZ=(row/(rows-1)-.5)*9.8, x=baseX+noise(col*.31,row*.27,2)*.11, z=baseZ+noise(col*.23+7,row*.29-4,3)*.09, edge=Math.pow(Math.abs(x)/6.4,2)*.2, y=field(x,z,time)+edge+noise(x*.24+20,z*.24-11,time*.035)*.7, radius=Math.sqrt(Math.pow(x/6.5,2)+Math.pow(z/5,2)), boundary=1.02+noise(x*.3+30,z*.3-18,time*.045)*.17; line.push({ ...project(x,z,y,scroll,time), active:radius<boundary }) } points.push(line) }
      const gradient=context.createLinearGradient(width*.08,height*.15,width*.92,height*.88); gradient.addColorStop(0,'#7c3aed'); gradient.addColorStop(.42,'#d946ef'); gradient.addColorStop(1,'#f43f8f'); const edgeLine=(a,b,alpha,glow=false)=>{ if(!a?.active||!b?.active)return; context.globalAlpha=alpha; context.lineWidth=glow?1.15:.48; context.lineCap='round'; context.strokeStyle=gradient; context.shadowColor=glow?'#ec4899':'transparent'; context.shadowBlur=glow?9:0; context.beginPath(); context.moveTo(a.x,a.y); context.lineTo(b.x,b.y); context.stroke() }; for(let row=0;row<rows;row++){ for(let col=0;col<cols;col++){ const point=points[row][col], right=points[row]?.[col+1], down=points[row+1]?.[col], diagonal=points[row+1]?.[col+(row%2?1:-1)]; edgeLine(point,right,.38); edgeLine(point,down,.3); edgeLine(point,diagonal,.31); if((row*cols+col)%29===0){ edgeLine(point,right,.12,true); edgeLine(point,diagonal,.1,true) } } }
      context.globalAlpha=1; const step=mobile.matches?31:19; for(let index=7;index<rows*cols;index+=step){ const row=Math.floor(index/cols), col=index%cols, point=points[row]?.[col]; if(!point)continue; const prominent=index%5===0, pulse=.42+Math.sin(time*.7+index)*.2; context.fillStyle=index%3===0?`rgba(255,91,186,${pulse})`:`rgba(184,166,255,${pulse})`; context.shadowColor=index%3===0?'#f044a7':'#8b5cf6'; context.shadowBlur=prominent?14:5; context.beginPath(); context.arc(point.x,point.y,prominent?1.8:.72,0,Math.PI*2); context.fill() } context.shadowBlur=0; if(!reduced.matches) frame=requestAnimationFrame(draw) }
    const move = event => { targetX=(event.clientX/width-.5)*.7; targetY=(event.clientY/height-.5)*.45 }
    const visibility = () => { visible=!document.hidden; if(visible&&!reduced.matches){ start=performance.now()-1000; cancelAnimationFrame(frame); frame=requestAnimationFrame(draw) } }
    resize(); window.addEventListener('resize',resize); window.addEventListener('pointermove',move,{passive:true}); document.addEventListener('visibilitychange',visibility); draw(performance.now())
    return () => { cancelAnimationFrame(frame); window.removeEventListener('resize',resize); window.removeEventListener('pointermove',move); document.removeEventListener('visibilitychange',visibility) }
  }, [])
  return <div className="landing-fx" aria-hidden="true"><canvas ref={canvasRef} className="mesh-canvas" /><div className="mesh-vignette" /></div>
}

function GlowCursor() {
  const dotRef = useRef(null), ringRef = useRef(null)
  useEffect(() => {
    if (!window.matchMedia('(pointer: fine)').matches || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    let x = -100, y = -100, ringX = -100, ringY = -100, frame
    const move = (event) => { x = event.clientX; y = event.clientY; dotRef.current?.style.setProperty('transform', `translate3d(${x}px,${y}px,0)`) }
    const hover = (event) => ringRef.current?.classList.toggle('is-hovering', Boolean(event.target.closest('a,button,input,select,textarea,summary')))
    const draw = () => { ringX += (x - ringX) * .16; ringY += (y - ringY) * .16; ringRef.current?.style.setProperty('transform', `translate3d(${ringX}px,${ringY}px,0)`); frame = requestAnimationFrame(draw) }
    window.addEventListener('pointermove', move); document.addEventListener('pointerover', hover); frame = requestAnimationFrame(draw)
    return () => { window.removeEventListener('pointermove', move); document.removeEventListener('pointerover', hover); cancelAnimationFrame(frame) }
  }, [])
  return <><span ref={dotRef} className="glow-cursor glow-cursor--dot" aria-hidden="true" /><span ref={ringRef} className="glow-cursor glow-cursor--ring" aria-hidden="true" /></>
}

function ProductPreview() {
  return <div className="landing-product" aria-label="VeriGate product dashboard preview">
    <div className="landing-product__bar"><div className="landing-product__brand"><span /><b>VERIGATE</b></div><div className="landing-product__controls"><i /><i /><i /></div></div>
    <div className="landing-product__body"><aside aria-hidden="true"><span className="is-active" /><span /><span /><span /><span /></aside><div className="landing-product__main">
      <div className="preview-heading"><div><small>RELEASE / VG-204</small><strong>Verification overview</strong></div><em><i /> Live workspace</em></div>
      <div className="preview-score"><div><small>RELEASE CONFIDENCE</small><strong>94<span>%</span></strong><p>Ready for final review</p></div><div className="score-ring"><span>94</span></div></div>
      <div className="preview-metrics"><div><small>Coverage</small><strong>128 / 136</strong><i><span style={{ width: '86%' }} /></i></div><div><small>Passed</small><strong>117</strong><i><span style={{ width: '92%' }} /></i></div><div><small>Open issues</small><strong>03</strong><i><span className="is-warn" style={{ width: '28%' }} /></i></div></div>
      <div className="preview-table"><div className="preview-table__head"><span>Latest verification</span><span>Status</span></div>{[['Authentication flow', 'Passed'], ['Payment recovery', 'Passed'], ['Mobile navigation', 'Review']].map(([name, status]) => <div className="preview-row" key={name}><span><i />{name}</span><em className={status === 'Review' ? 'is-review' : ''}>{status}</em></div>)}</div>
    </div></div>
  </div>
}

function FeatureVisual({ type }) {
  if (type === 'trace') return <div className="feature-visual trace-visual" aria-label="Requirement traceability visualization"><div className="trace-origin"><ShieldCheck /><span><small>Requirement</small><b>Secure sign-in</b></span></div><div className="trace-line"><i /><i /><i /></div><div className="trace-nodes"><span>Test suite <b>AUTH-01</b></span><span>Evidence <b>12 items</b></span><span>Verdict <b>Passed</b></span></div></div>
  return <div className="feature-visual evidence-visual" aria-label="Verification evidence visualization"><div className="evidence-top"><small>LIVE EXECUTION</small><span><i /> Capturing</span></div><div className="evidence-code"><span><b>01</b> POST /api/auth/login</span><span><b>02</b> expect(response.status).toBe(200)</span><span><b>03</b> evidence.capture('session')</span></div><div className="evidence-proof"><Check /><span><small>PROOF ATTACHED</small><b>Session restored securely</b></span><em>02:14</em></div></div>
}

export function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false), [openFaq, setOpenFaq] = useState(0)
  useEffect(() => { document.body.classList.add('has-landing'); return () => document.body.classList.remove('has-landing') }, [])
  const closeMenu = () => setMenuOpen(false)
  const scrollToSection = (event, sectionId) => {
    event.preventDefault(); closeMenu()
    const id = sectionId.replace('#', ''), section = document.getElementById(id)
    if (!section) return
    requestAnimationFrame(() => requestAnimationFrame(() => {
      const target = section.querySelector(':scope > .landing-container') || section
      const headerHeight = document.querySelector('.landing-header')?.getBoundingClientRect().height || 76
      const top = target.getBoundingClientRect().top + window.scrollY - headerHeight - 18
      window.history.replaceState(null, '', `#${id}`)
      window.scrollTo({ top, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
    }))
  }
  return <div className="landing-page">
    <BackgroundEffects /><GlowCursor />
    <a className="skip-link" href="#main-content">Skip to content</a>
    <header className="landing-header"><div className="landing-container landing-nav"><Link to="/" className="landing-logo" aria-label="VeriGate home"><Brand /></Link><nav className={menuOpen ? 'is-open' : ''} aria-label="Landing navigation">{[['how','How it works'],['features','Features'],['technology','Technology'],['faq','FAQ']].map(([target,label]) => <a href={`#${target}`} onClick={(event) => scrollToSection(event, target)} key={target}>{label}</a>)}<div className="landing-nav__mobile-actions"><Link to="/login">Sign in</Link><Link to="/register" className="landing-button landing-button--primary">Get started</Link></div></nav><div className="landing-nav__actions"><Link to="/login" className="landing-signin">Sign in</Link><Link to="/register" className="landing-button landing-button--small">Get started <ArrowRight /></Link></div><button className="landing-menu" aria-label={menuOpen ? 'Close menu' : 'Open menu'} aria-expanded={menuOpen} onClick={() => setMenuOpen(v => !v)}>{menuOpen ? <X /> : <Menu />}</button></div></header>
    <main id="main-content">
      <section className="landing-hero"><div className="hero-ambient" aria-hidden="true"><span /><span /><span /></div><div className="landing-grid" aria-hidden="true" /><div className="landing-container landing-hero__content"><div className="landing-kicker"><Sparkles /> Verification, reimagined <span>Built for modern teams</span></div><h1>Every test tells a story.<br /><span>Make yours undeniable.</span></h1><p>VeriGate turns scattered tests, evidence and issues into one living verification recordâ€”so your team can ship with clarity, not guesswork.</p><div className="landing-hero__actions"><Link to="/register" className="landing-button landing-button--primary landing-button--large">Create your workspace <ArrowRight /></Link><a href="#how" className="landing-button landing-button--ghost landing-button--large"><Play /> See how it works</a></div><div className="landing-proof"><span><Check /> No credit card required</span><span><Check /> Set up in minutes</span><span><Check /> Your evidence stays yours</span></div><div className="hero-product-wrap"><div className="hero-orbit hero-orbit--one" /><div className="hero-orbit hero-orbit--two" /><ProductPreview /></div></div></section>
      <section className="brand-statement landing-section"><div className="landing-container"><p className="landing-eyebrow">THE VERIFICATION LAYER</p><h2>Tests produce results.<br />VeriGate produces <span>confidence.</span></h2><p>One calm, connected place where engineering work becomes release-ready proof.</p></div></section>
      <section className="landing-section how-section" id="how"><div className="landing-container"><div className="section-heading"><div><p className="landing-eyebrow">HOW IT WORKS</p><h2>From scattered checks<br />to a clear verdict.</h2></div><p>VeriGate connects the full verification journey without forcing your team into a rigid new process.</p></div><div className="steps-grid">{steps.map(([number,title,copy]) => <article key={number}><span>{number}</span><div className="step-icon"><i /><i /></div><h3>{title}</h3><p>{copy}</p></article>)}</div></div></section>
      <section className="landing-section showcase-section" id="features"><div className="landing-container">{[['END-TO-END TRACEABILITY','See the proof behind every decision.','Move from a release verdict back through evidence, execution, test coverage and requirementsâ€”without chasing links across tools.','trace'],['EVIDENCE IN CONTEXT','Capture what matters while it matters.','Keep logs, screenshots, outcomes and issues attached to the exact run that produced them. Less reconstruction. Better answers.','evidence']].map(([eyebrow,title,copy,type], index) => <div className={`feature-showcase ${index ? 'feature-showcase--reverse' : ''}`} key={title}><div className="feature-copy"><p className="landing-eyebrow">{eyebrow}</p><h2>{title}</h2><p>{copy}</p><ul><li><Check /> Connected verification records</li><li><Check /> Clear ownership and status</li><li><Check /> Audit-ready history</li></ul></div><FeatureVisual type={type} /></div>)}</div></section>
      <section className="landing-section feature-grid-section"><div className="landing-container"><div className="section-heading section-heading--center"><div><p className="landing-eyebrow">ONE CONNECTED WORKSPACE</p><h2>Everything you need to verify<br />with confidence.</h2></div></div><div className="feature-card-grid">{features.map(([title,copy], index) => <article key={title}><span className="feature-card__number">0{index + 1}</span><div className="feature-card__glyph"><i /><i /></div><h3>{title}</h3><p>{copy}</p><a href="#cta">Explore capability <ArrowRight /></a></article>)}</div></div></section>
      <section className="landing-section technology-section" id="technology"><div className="landing-container technology-layout"><div><p className="landing-eyebrow">BUILT FOR THE SIGNAL</p><h2>Your verification data,<br /><span>finally connected.</span></h2><p>A focused foundation for project structure, test intelligence, execution history, evidence and issuesâ€”designed to grow with your engineering organization.</p></div><div className="tech-stack"><div className="tech-core"><span><Zap /></span><small>VERIGATE CORE</small><strong>Traceability engine</strong></div>{['Projects','Test suites','Evidence','Issues'].map((item,index) => <div className={`tech-node tech-node--${index + 1}`} key={item}><i />{item}</div>)}</div></div><div className="landing-container trust-row">{['SECURITY-FIRST','API-READY','TRACEABLE','TEAM-CENTRIC','AUDIT-FRIENDLY'].map(x => <span key={x}>{x}</span>)}</div></section>
      <section className="landing-section faq-section" id="faq"><div className="landing-container faq-layout"><div><p className="landing-eyebrow">FAQ</p><h2>Questions,<br />answered clearly.</h2><p>Still evaluating? Start a workspace and explore the product at your own pace.</p><Link to="/register">Get started <ArrowRight /></Link></div><div className="faq-list">{faqs.map(([question,answer],index) => { const open = openFaq === index; return <article key={question} className={open ? 'is-open' : ''}><h3><button onClick={() => setOpenFaq(open ? -1 : index)} aria-expanded={open} aria-controls={`faq-answer-${index}`}>{question}<ChevronDown /></button></h3><div id={`faq-answer-${index}`} className="faq-answer" hidden={!open}><p>{answer}</p></div></article> })}</div></div></section>
      <section className="final-cta" id="cta"><div className="landing-grid" aria-hidden="true" /><div className="cta-glow" aria-hidden="true" /><div className="landing-container"><p className="landing-eyebrow">YOUR NEXT RELEASE STARTS HERE</p><h2>Make confidence<br /><span>part of the process.</span></h2><p>Bring your verification work into one connected, defensible record.</p><div><Link to="/register" className="landing-button landing-button--primary landing-button--large">Create your workspace <ArrowRight /></Link><Link to="/login" className="landing-button landing-button--ghost landing-button--large">Sign in</Link></div></div></section>
    </main>
    <footer className="landing-footer"><div className="landing-container"><div className="footer-main"><div><Brand /><p>Verification clarity for teams that care what the evidence proves.</p></div><div><strong>Product</strong><a href="#how" onClick={(event) => scrollToSection(event, '#how')}>How it works</a><a href="#features" onClick={(event) => scrollToSection(event, '#features')}>Features</a><a href="#technology" onClick={(event) => scrollToSection(event, '#technology')}>Technology</a><a href="#faq" onClick={(event) => scrollToSection(event, '#faq')}>FAQ</a></div><div><strong>Workspace</strong><Link to="/login">Sign in</Link><Link to="/register">Create account</Link><Link to="/app">Dashboard</Link></div><div><strong>Company</strong><a href="mailto:hello@verigate.dev">Contact</a><span>Privacy</span><span>Terms</span></div></div><div className="footer-bottom"><span>Â© {new Date().getFullYear()} VeriGate. All rights reserved.</span><span>Built for evidence. Designed for confidence.</span></div></div></footer>
  </div>
}

