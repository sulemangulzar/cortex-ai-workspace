import { useState } from 'react'
import './App.css'

const features = [
  {
    number: '01',
    title: 'Build in context',
    description: 'Bring your code, docs, and ideas into one focused workspace designed for momentum.',
  },
  {
    number: '02',
    title: 'Think in systems',
    description: 'Turn scattered thoughts into clear project maps, useful decisions, and shippable work.',
  },
  {
    number: '03',
    title: 'Move with intent',
    description: 'A calm interface that keeps the signal high and the noise out of your workflow.',
  },
]

function ArrowUpRight() {
  return <span aria-hidden="true" className="text-lg leading-none">↗</span>
}

function App() {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <main className="min-h-screen overflow-hidden bg-[#080808] text-white selection:bg-white selection:text-black">
      <div className="pointer-events-none fixed inset-0 z-0 bg-[radial-gradient(circle_at_50%_0%,rgba(255,255,255,0.09),transparent_28rem)]" />
      <div className="pointer-events-none absolute left-1/2 top-24 z-0 h-72 w-72 -translate-x-1/2 animate-pulse rounded-full bg-white/10 blur-[120px]" />

      <nav className="relative z-10 mx-auto flex max-w-7xl items-center justify-between px-6 py-6 lg:px-10">
        <a href="#top" className="flex items-center gap-3 font-mono text-sm font-bold tracking-tight">
          <span className="grid h-8 w-8 place-items-center rounded-lg border border-white/20 bg-white text-sm text-black shadow-[0_0_22px_rgba(255,255,255,0.28)]">C</span>
          <span>CORTEX<span className="text-white/40">_AI</span></span>
        </a>

        <div className="hidden items-center gap-8 font-mono text-xs text-white/50 md:flex">
          <a className="transition hover:text-white" href="#product">[ product ]</a>
          <a className="transition hover:text-white" href="#principles">[ principles ]</a>
          <a className="transition hover:text-white" href="#contact">[ contact ]</a>
        </div>

        <a href="#launch" className="hidden items-center gap-2 rounded-full border border-white/20 px-4 py-2 font-mono text-xs text-white transition hover:border-white/60 hover:bg-white hover:text-black sm:flex">
          Enter workspace <ArrowUpRight />
        </a>
        <button aria-label="Toggle navigation" onClick={() => setMenuOpen(!menuOpen)} className="rounded-md border border-white/20 p-2 font-mono text-white md:hidden">
          {menuOpen ? '×' : '≡'}
        </button>
      </nav>

      {menuOpen && (
        <div className="relative z-20 mx-6 rounded-xl border border-white/15 bg-[#101010] p-5 font-mono text-sm md:hidden">
          <div className="flex flex-col gap-5 text-white/60">
            <a href="#product" onClick={() => setMenuOpen(false)}>product →</a>
            <a href="#principles" onClick={() => setMenuOpen(false)}>principles →</a>
            <a href="#contact" onClick={() => setMenuOpen(false)}>contact →</a>
            <a href="#launch" onClick={() => setMenuOpen(false)} className="text-white">Enter workspace ↗</a>
          </div>
        </div>
      )}

      <section id="top" className="relative z-10 mx-auto max-w-7xl px-6 pb-20 pt-20 sm:pb-28 sm:pt-28 lg:px-10 lg:pt-36">
        <div className="max-w-4xl">
          <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/4 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.2em] text-white/50">
            <span className="relative flex h-1.5 w-1.5"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-white opacity-60" /><span className="relative inline-flex h-1.5 w-1.5 animate-pulse rounded-full bg-white shadow-[0_0_12px_white]" /></span>
            A clearer place to build
          </div>
          <h1 className="font-mono text-5xl font-medium leading-[1.03] tracking-[-0.08em] text-white transition duration-500 hover:text-white/90 sm:text-7xl lg:text-[7.5rem]">
            Make space
            <br />
            <span className="text-white/35">for better</span>
            <br />
            thinking<span className="text-white/30">_</span>
          </h1>
          <p className="mt-8 max-w-xl font-mono text-sm leading-7 text-white/45 sm:text-base">
            Cortex is a focused workspace for turning complex ideas into clear, connected, and useful work.
          </p>
          <div className="mt-10 flex flex-col gap-3 font-mono text-xs sm:flex-row">
            <a id="launch" href="#product" className="group inline-flex items-center justify-center gap-3 rounded-full bg-white px-6 py-3.5 text-black transition hover:bg-white/85">
              Start building <span className="transition group-hover:translate-x-1">→</span>
            </a>
            <a href="#principles" className="inline-flex items-center justify-center gap-3 rounded-full border border-white/15 px-6 py-3.5 text-white/65 transition hover:border-white/50 hover:text-white">
              See how it works <ArrowUpRight />
            </a>
          </div>
        </div>
      </section>

      <section id="product" className="relative z-10 mx-auto max-w-7xl px-6 pb-28 lg:px-10">
        <div className="group relative overflow-hidden rounded-2xl border border-white/15 bg-[#0d0d0d] shadow-[0_0_80px_rgba(255,255,255,0.06)] transition duration-700 hover:border-white/30 hover:shadow-[0_0_100px_rgba(255,255,255,0.1)]">
          <div className="absolute -right-24 -top-24 h-64 w-64 animate-pulse rounded-full bg-white/10 blur-[90px] transition duration-700 group-hover:bg-white/20" />
                    <div className="pointer-events-none absolute -right-24 top-16 h-72 w-72 animate-[spin_30s_linear_infinite] rounded-full border border-dashed border-white/10" />
          <div className="flex items-center justify-between border-b border-white/10 px-5 py-4 font-mono text-[10px] text-white/35 sm:px-7">
            <div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-white/30" /><span className="h-2 w-2 rounded-full bg-white/15" /><span className="h-2 w-2 rounded-full bg-white/10" /></div>
            <span>cortex / workspace / overview</span>
            <span className="hidden sm:block">⌘ K</span>
          </div>
          <div className="grid min-h-95 md:grid-cols-[190px_1fr]">
            <aside className="hidden border-r border-white/10 p-5 md:block">
              <div className="mb-8 font-mono text-[10px] uppercase tracking-widest text-white/25">workspace</div>
              <div className="space-y-4 font-mono text-xs text-white/40"><div className="text-white">◈ Overview</div><div>◇ Projects</div><div>◇ Signals</div><div>◇ Archive</div></div>
              <div className="mt-28 border-t border-white/10 pt-4 font-mono text-[10px] text-white/25">v 0.1.0 / online</div>
            </aside>
            <div className="relative p-6 sm:p-10">
              <div className="flex items-start justify-between"><div><p className="font-mono text-[10px] uppercase tracking-[0.25em] text-white/30">Monday, 08:42</p><h2 className="mt-3 font-mono text-2xl tracking-tight text-white sm:text-3xl">Good morning, builder.</h2></div><div className="hidden rounded-full border border-white/15 px-3 py-1.5 font-mono text-[10px] text-white/40 sm:block">+ New project</div></div>
              <div className="mt-10 grid gap-4 sm:grid-cols-2"><div className="rounded-xl border border-white/15 bg-white/4 p-5 transition duration-500 hover:-translate-y-1 hover:bg-white/[0.07]"><div className="flex justify-between font-mono text-[10px] text-white/35"><span>ACTIVE PROJECT</span><span>01</span></div><div className="mt-12 font-mono text-lg text-white">Cortex architecture</div><div className="mt-3 h-1 overflow-hidden rounded-full bg-white/10"><div className="h-full w-2/3 rounded-full bg-white shadow-[0_0_14px_white]" /></div><div className="mt-3 font-mono text-[10px] text-white/35">67% in motion</div></div><div className="rounded-xl border border-white/10 bg-white/2 p-5 transition duration-500 hover:-translate-y-1 hover:border-white/20 hover:bg-white/4"><div className="font-mono text-[10px] text-white/35">RECENT SIGNAL</div><div className="mt-12 font-mono text-lg text-white/80">Reduce the noise.</div><div className="mt-3 font-mono text-[10px] leading-5 text-white/35">The best systems leave room for the right questions.</div></div></div>
              <div className="mt-4 flex items-center justify-between border-t border-white/10 pt-5 font-mono text-[10px] text-white/30"><span>3 projects in focus</span><span>Last synced just now ↗</span></div>
            </div>
          </div>
        </div>
      </section>

      <section id="principles" className="relative z-10 mx-auto max-w-7xl border-t border-white/10 px-6 py-24 lg:px-10">
        <div className="grid gap-12 lg:grid-cols-[0.8fr_1.2fr]"><div><p className="font-mono text-[10px] uppercase tracking-[0.25em] text-white/35">/ principles</p><h2 className="mt-5 max-w-md font-mono text-3xl leading-tight tracking-[-0.06em] text-white sm:text-5xl">Less interface.<br /><span className="text-white/35">More intelligence.</span></h2></div><div className="grid gap-4 sm:grid-cols-3">{features.map((feature) => <article key={feature.number} className="border-t border-white/20 pt-4 transition duration-500 hover:-translate-y-1 hover:border-white/60"><div className="font-mono text-xs text-white/30">{feature.number}</div><h3 className="mt-10 font-mono text-sm text-white">{feature.title}</h3><p className="mt-4 font-mono text-xs leading-6 text-white/40">{feature.description}</p></article>)}</div></div>
      </section>

      <footer id="contact" className="relative z-10 mx-auto flex max-w-7xl flex-col gap-6 border-t border-white/10 px-6 py-8 font-mono text-[10px] text-white/30 sm:flex-row sm:items-center sm:justify-between lg:px-10"><span>© 2025 CORTEX_AI</span><span>made for the curious minds<span className="text-white">_</span></span><a href="#top" className="text-white/60 transition hover:text-white">back to top ↑</a></footer>
    </main>
  )
}

export default App
