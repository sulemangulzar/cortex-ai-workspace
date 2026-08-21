import { useState } from 'react'
import './App.css'
import Workspace from './Workspace.jsx'

const API_URL = import.meta.env.VITE_API_URL ?? `http://${window.location.hostname}:8000`

async function fetchApi(url, options) {
  try {
    return await fetch(url, options)
  } catch {
    throw new Error(`Cannot connect to the API at ${API_URL}. Make sure FastAPI is running.`)
  }
}

const features = [
  ['01', 'Build in context', 'Keep your code, docs, and ideas together in one focused workspace.'],
  ['02', 'See the whole picture', 'Turn complex work into clear projects, steps, and decisions.'],
  ['03', 'Stay in motion', 'A quieter interface that helps you focus on what matters next.'],
]

function ArrowUpRight() {
  return <span aria-hidden="true" className="text-lg leading-none">↗</span>
}

function Logo({ href, onClick }) {
  const content = <><span className="grid h-9 w-9 place-items-center rounded-xl border border-white/20 bg-linear-to-br from-white to-white/70 text-black shadow-[0_0_24px_rgba(255,255,255,0.16)] transition duration-300 group-hover:shadow-[0_0_30px_rgba(255,255,255,0.3)]"><svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true"><path d="M17.5 5.5a8 8 0 1 0 0 13" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" /><path d="M17.5 5.5v4.2M17.5 5.5h-4.2" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" /></svg></span><span className="text-[15px] tracking-[-0.04em]">cortex<span className="text-white/40">.ai</span></span></>
  if (href) return <a href={href} className="group flex items-center gap-3 font-mono font-bold tracking-tight">{content}</a>
  return <button type="button" onClick={onClick} className="group flex items-center gap-3 font-mono font-bold tracking-tight">{content}</button>
}

function Field({ label, name, type = 'text', value, onChange, required = false }) {
  return <label className="block font-mono text-[10px] uppercase tracking-[0.18em] text-white/40">{label}<input required={required} name={name} type={type} value={value} onChange={onChange} className="mt-2 block w-full rounded-lg border border-white/15 bg-white/3 px-4 py-3.5 font-mono text-sm normal-case tracking-normal text-white outline-none transition placeholder:text-white/20 focus:border-white/60 focus:bg-white/6" /></label>
}

function AuthForm({ mode, onSwitch, onBack, onAuthenticated }) {
  const isSignup = mode === 'signup'
  const [form, setForm] = useState({ email: '', identifier: '', password: '', first_name: '', last_name: '', username: '' })
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  function updateField(event) {
    setForm({ ...form, [event.target.name]: event.target.value })
  }

  async function submit(event) {
    event.preventDefault()
    setLoading(true)
    setMessage('')
    const endpoint = isSignup ? '/auth/v1/signup' : '/auth/v1/login'
    const body = isSignup ? form : { identifier: form.identifier, password: form.password }
    try {
      const response = await fetchApi(`${API_URL}${endpoint}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify(body) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail?.[0]?.msg ?? data.detail ?? 'Something went wrong')
      if (!isSignup && data.access_token) {
        localStorage.setItem('access_token', data.access_token)
        onAuthenticated(data.access_token)
      }
      setMessage(isSignup ? 'Account created. You can now sign in.' : 'You are signed in.')
      if (isSignup) onSwitch('login')
    } catch (error) {
      setMessage(error.message)
    } finally {
      setLoading(false)
    }
  }

  return <main className="min-h-screen bg-[#080808] px-6 text-white selection:bg-white selection:text-black"><nav className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-x-4 gap-y-3 py-6 lg:px-4"><Logo onClick={onBack} /><button onClick={() => onSwitch(isSignup ? 'login' : 'signup')} className="max-w-56 text-right font-mono text-[10px] leading-4 text-white/50 transition hover:text-white sm:max-w-none sm:text-xs">{isSignup ? 'Already have an account? Sign in' : 'New here? Create an account'}</button></nav><section className="mx-auto flex max-w-7xl justify-center pb-20 pt-16 sm:pt-24"><div className="w-full max-w-md"><p className="font-mono text-[10px] uppercase tracking-[0.25em] text-white/35">/ {isSignup ? 'create account' : 'sign in'}</p><h1 className="mt-5 font-mono text-4xl tracking-[-0.06em] sm:text-5xl">{isSignup ? 'Start with a clear space.' : 'Welcome back.'}</h1><p className="mt-5 font-mono text-xs leading-6 text-white/40">{isSignup ? 'Set up your workspace and make room for better thinking.' : 'Continue where you left off.'}</p><form onSubmit={submit} className="mt-10 space-y-4">{isSignup && <div className="grid gap-4 sm:grid-cols-2"><Field label="First name" name="first_name" value={form.first_name} onChange={updateField} /><Field label="Last name" name="last_name" value={form.last_name} onChange={updateField} /></div>}{isSignup && <Field label="Username" name="username" value={form.username} onChange={updateField} required />}<Field label={isSignup ? 'Email' : 'Email or username'} name={isSignup ? 'email' : 'identifier'} type={isSignup ? 'email' : 'text'} value={isSignup ? form.email : form.identifier} onChange={updateField} required /><Field label="Password" name="password" type="password" value={form.password} onChange={updateField} required /><button disabled={loading} className="mt-4 flex w-full items-center justify-center rounded-full bg-white px-6 py-3.5 font-mono text-xs text-black transition hover:bg-white/85 disabled:cursor-wait disabled:opacity-50">{loading ? 'Working...' : isSignup ? 'Create account →' : 'Sign in →'}</button></form>{message && <p className="mt-5 border-l border-white/40 pl-3 font-mono text-xs leading-5 text-white/60">{message}</p>}</div></section></main>
}

function Landing({ onAuth }) {
  const [menuOpen, setMenuOpen] = useState(false)
  return <main className="min-h-screen overflow-hidden bg-[#080808] text-white selection:bg-white selection:text-black"><div className="pointer-events-none fixed inset-0 z-0 bg-[radial-gradient(circle_at_50%_0%,rgba(255,255,255,0.07),transparent_28rem)]" /><nav className="relative z-10 mx-auto flex max-w-7xl items-center justify-between px-6 py-6 lg:px-10"><Logo href="#top" /><div className="hidden items-center gap-8 font-mono text-xs text-white/50 md:flex"><a className="transition hover:text-white" href="#top">Home</a><a className="transition hover:text-white" href="#product">Product</a><a className="transition hover:text-white" href="#principles">Principles</a><a className="transition hover:text-white" href="#contact">Contact</a></div><div className="hidden items-center gap-4 font-mono text-xs sm:flex"><button onClick={() => onAuth('login')} className="text-white/55 transition hover:text-white">Sign in</button><button onClick={() => onAuth('signup')} className="rounded-full border border-white/20 px-4 py-2 transition hover:border-white/60 hover:bg-white hover:text-black">Create account <ArrowUpRight /></button></div><button aria-label="Toggle navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)} className="rounded-md border border-white/20 p-2 font-mono transition-transform duration-200 active:scale-90 md:hidden">{menuOpen ? '×' : '≡'}</button></nav><div className={`relative z-20 mx-6 overflow-hidden rounded-xl border border-white/15 bg-[#101010] font-mono text-sm transition-all duration-300 ease-out md:hidden ${menuOpen ? 'max-h-96 translate-y-0 p-5 opacity-100' : 'pointer-events-none max-h-0 -translate-y-2 border-transparent p-0 opacity-0'}`}><div className="flex flex-col gap-5 text-white/60"><a href="#top" onClick={() => setMenuOpen(false)}>Home →</a><a href="#product" onClick={() => setMenuOpen(false)}>Product →</a><a href="#principles" onClick={() => setMenuOpen(false)}>Principles →</a><a href="#contact" onClick={() => setMenuOpen(false)}>Contact →</a><button className="text-left text-white" onClick={() => { setMenuOpen(false); onAuth('login') }}>Sign in ↗</button><button className="text-left text-white" onClick={() => { setMenuOpen(false); onAuth('signup') }}>Create account ↗</button></div></div><section id="top" className="relative z-10 mx-auto max-w-7xl px-6 pb-20 pt-24 sm:pb-28 sm:pt-32 lg:px-10 lg:pt-40"><div className="max-w-4xl"><p className="mb-8 font-mono text-[10px] uppercase tracking-[0.25em] text-white/35">A workspace for focused work</p><h1 className="font-mono text-5xl font-medium leading-[1.03] tracking-[-0.08em] sm:text-7xl lg:text-[7.5rem]">Make space<br /><span className="text-white/35">for better</span><br />thinking<span className="text-white/30">_</span></h1><p className="mt-8 max-w-xl font-mono text-sm leading-7 text-white/45 sm:text-base">Cortex is a focused workspace for turning complex ideas into clear, connected, and useful work.</p><div className="mt-10 flex flex-col gap-3 font-mono text-xs sm:flex-row"><button onClick={() => onAuth('signup')} className="group inline-flex items-center justify-center gap-3 rounded-full bg-white px-6 py-3.5 text-black transition hover:bg-white/85">Start building <span className="transition group-hover:translate-x-1">→</span></button><a href="#principles" className="inline-flex items-center justify-center gap-3 rounded-full border border-white/15 px-6 py-3.5 text-white/65 transition hover:border-white/50 hover:text-white">See how it works <ArrowUpRight /></a></div></div></section><section id="product" className="relative z-10 mx-auto max-w-7xl px-6 pb-28 lg:px-10"><div className="overflow-hidden rounded-2xl border border-white/15 bg-[#0d0d0d] shadow-[0_0_70px_rgba(255,255,255,0.05)]"><div className="flex items-center justify-between border-b border-white/10 px-5 py-4 font-mono text-[10px] text-white/35"><span>cortex / workspace / overview</span><span className="hidden sm:block">⌘ K</span></div><div className="p-6 sm:p-10"><p className="font-mono text-[10px] uppercase tracking-[0.25em] text-white/30">Your workspace</p><h2 className="mt-3 font-mono text-2xl tracking-tight text-white sm:text-3xl">A calmer place to build.</h2><div className="mt-10 grid gap-4 sm:grid-cols-2"><div className="rounded-xl border border-white/15 bg-white/4 p-5"><div className="font-mono text-[10px] text-white/35">ACTIVE PROJECT</div><div className="mt-12 font-mono text-lg text-white">Cortex architecture</div><div className="mt-3 h-1 overflow-hidden rounded-full bg-white/10"><div className="h-full w-2/3 rounded-full bg-white" /></div></div><div className="rounded-xl border border-white/10 bg-white/2 p-5"><div className="font-mono text-[10px] text-white/35">NOTE</div><div className="mt-12 font-mono text-lg text-white/80">Reduce the noise.</div><div className="mt-3 font-mono text-[10px] leading-5 text-white/35">Leave room for the right questions.</div></div></div></div></div></section><section id="principles" className="relative z-10 mx-auto max-w-7xl border-t border-white/10 px-6 py-24 lg:px-10"><div className="grid gap-12 lg:grid-cols-[0.8fr_1.2fr]"><div><p className="font-mono text-[10px] uppercase tracking-[0.25em] text-white/35">/ principles</p><h2 className="mt-5 max-w-md font-mono text-3xl leading-tight tracking-[-0.06em] sm:text-5xl">Less interface.<br /><span className="text-white/35">More focus.</span></h2></div><div className="grid gap-4 sm:grid-cols-3">{features.map(([number, title, description]) => <article key={number} className="border-t border-white/20 pt-4 transition duration-500 hover:-translate-y-1 hover:border-white/60"><div className="font-mono text-xs text-white/30">{number}</div><h3 className="mt-10 font-mono text-sm">{title}</h3><p className="mt-4 font-mono text-xs leading-6 text-white/40">{description}</p></article>)}</div></div></section><section id="contact" className="relative z-10 mx-auto max-w-7xl border-t border-white/10 px-6 py-24 lg:px-10"><div className="grid gap-10 rounded-2xl border border-white/15 bg-white/3 p-7 sm:p-10 lg:grid-cols-[1fr_auto] lg:items-end"><div><p className="font-mono text-[10px] uppercase tracking-[0.25em] text-white/35">/ contact</p><h2 className="mt-5 max-w-xl font-mono text-3xl leading-tight tracking-[-0.06em] sm:text-5xl">Have a thoughtful<br /><span className="text-white/35">question?</span></h2><p className="mt-5 max-w-md font-mono text-xs leading-6 text-white/40">Tell us what you are building, what is unclear, or where you want to go next.</p></div><a href="mailto:suleman_gulzar@icloud.com" className="inline-flex w-fit items-center gap-3 rounded-full bg-white px-6 py-3.5 font-mono text-xs text-black transition hover:bg-white/85">suleman_gulzar@icloud.com <ArrowUpRight /></a></div></section><footer className="relative z-10 mx-auto flex max-w-7xl flex-col gap-6 border-t border-white/10 px-6 py-8 font-mono text-[10px] text-white/30 sm:flex-row sm:items-center sm:justify-between lg:px-10"><span>© 2026 cortex.ai</span><span>made for curious minds<span className="text-white">_</span></span><a href="#top" className="text-white/60 transition hover:text-white">back to top ↑</a></footer></main>
}

function App() {
  const [authMode, setAuthMode] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem('access_token'))
  if (token) return <Workspace token={token} onTokenChange={setToken} onLogout={() => { localStorage.removeItem('access_token'); setToken(null) }} />
  if (authMode) return <AuthForm mode={authMode} onSwitch={setAuthMode} onBack={() => setAuthMode(null)} onAuthenticated={setToken} />
  return <Landing onAuth={setAuthMode} />
}

export default App
