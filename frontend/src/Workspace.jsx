import { useCallback, useEffect, useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL ?? `http://${window.location.hostname}:8000`

async function fetchApi(url, options) {
  try {
    return await fetch(url, options)
  } catch {
    throw new Error(`Cannot connect to the API at ${API_URL}. Make sure FastAPI is running.`)
  }
}

function Brand() {
  return <div className="flex items-center gap-3 font-mono text-sm font-bold tracking-tight"><span className="grid h-9 w-9 place-items-center rounded-xl bg-white text-black shadow-[0_0_24px_rgba(255,255,255,0.15)]"><svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" aria-hidden="true"><path d="M17.5 5.5a8 8 0 1 0 0 13M17.5 5.5v4.2M17.5 5.5h-4.2" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" /></svg></span><span>cortex<span className="text-white/35">.ai</span></span></div>
}

function Metric({ label, value, detail }) {
  return <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-5 transition hover:border-white/25 hover:bg-white/[0.055]"><p className="text-[10px] uppercase tracking-[0.2em] text-white/35">{label}</p><p className="mt-6 text-3xl tracking-[-0.08em]">{value}</p><p className="mt-2 text-[10px] text-white/35">{detail}</p></div>
}

function Workspace({ token, onLogout, onTokenChange }) {
  const [page, setPage] = useState('overview')
  const [projects, setProjects] = useState([])
  const [selected, setSelected] = useState(null)
  const [runs, setRuns] = useState([])
  const [chats, setChats] = useState([])
  const [activeChat, setActiveChat] = useState(null)
  const [messages, setMessages] = useState([])
  const [mode, setMode] = useState('chat')
  const [draft, setDraft] = useState('')
  const [requirement, setRequirement] = useState('')
  const [newProject, setNewProject] = useState({ name: '', description: '' })
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(true)

  const request = useCallback(async (path, options = {}) => {
    const send = (accessToken) => fetchApi(`${API_URL}${path}`, { ...options, credentials: 'include', headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json', ...options.headers } })
    let accessToken = token
    let response = await send(accessToken)

    if (response.status === 401 && !path.startsWith('/auth/v1/')) {
      const refreshResponse = await fetchApi(`${API_URL}/auth/v1/refresh`, { method: 'POST', credentials: 'include' })
      if (refreshResponse.ok) {
        const refreshed = await refreshResponse.json()
        accessToken = refreshed.access_token
        localStorage.setItem('access_token', accessToken)
        onTokenChange(accessToken)
        response = await send(accessToken)
      } else {
        onLogout()
        throw new Error('Your session expired. Please sign in again.')
      }
    }

    const data = response.status === 204 ? null : await response.json()
    if (!response.ok) throw new Error(data?.detail?.[0]?.msg ?? data?.detail ?? 'Request failed')
    return data
  }, [onLogout, onTokenChange, token])

  useEffect(() => {
    request('/projects').then((data) => { setProjects(data); setSelected(null); setPage('overview') }).catch((error) => setNotice(error.message)).finally(() => setLoading(false))
  }, [request])

  useEffect(() => {
    if (!selected) return
    Promise.allSettled([request(`/projects/${selected.id}/chats`), request(`/projects/${selected.id}/builds`)]).then(([chatResult, buildResult]) => {
      if (chatResult.status === 'fulfilled') {
        setChats(chatResult.value)
        setActiveChat(chatResult.value[0] ?? null)
      } else {
        setNotice(chatResult.reason.message)
      }
      if (buildResult.status === 'fulfilled') setRuns(buildResult.value)
      else setNotice(buildResult.reason.message)
    })
  }, [request, selected])

  useEffect(() => {
    if (!selected || !activeChat) return
    request(`/projects/${selected.id}/chats/${activeChat.id}/messages`).then(setMessages).catch((error) => setNotice(error.message))
  }, [request, selected, activeChat])

  useEffect(() => {
    if (!selected || page !== 'project') return
    const refreshRuns = () => request(`/projects/${selected.id}/builds`).then(setRuns).catch((error) => setNotice(error.message))
    const interval = window.setInterval(refreshRuns, 4000)
    return () => window.clearInterval(interval)
  }, [page, request, selected])

  async function createProject(event) {
    event.preventDefault()
    try { const project = await request('/projects', { method: 'POST', body: JSON.stringify(newProject) }); setProjects((current) => [project, ...current]); setSelected(project); setNewProject({ name: '', description: '' }); setPage('project'); setNotice('Project created.') } catch (error) { setNotice(error.message) }
  }

  async function createChat() {
    if (!selected) return
    try { const chat = await request(`/projects/${selected.id}/chats`, { method: 'POST', body: JSON.stringify({ title: 'New conversation' }) }); setChats((current) => [chat, ...current]); setActiveChat(chat); setMessages([]); setMode('chat') } catch (error) { setNotice(error.message) }
  }

  async function sendMessage(event) {
    event.preventDefault()
    if (!draft.trim() || !selected || !activeChat) return
    try { const message = await request(`/projects/${selected.id}/chats/${activeChat.id}/messages`, { method: 'POST', body: JSON.stringify({ content: draft }) }); setMessages((current) => [...current, message]); setDraft('') } catch (error) { setNotice(error.message) }
  }

  async function startBuild(event) {
    event.preventDefault()
    if (!requirement.trim() || !selected) return
    try { const result = await request(`/projects/${selected.id}/builds`, { method: 'POST', body: JSON.stringify({ requirement }) }); setRuns((current) => [result.run, ...current]); setRequirement(''); setNotice('Build request queued.') } catch (error) { setNotice(error.message) }
  }

  function openProject(project) { setSelected(project); setPage('project'); setMode('chat') }
  const completed = runs.filter((run) => run.status === 'COMPLETED').length

  if (loading) return <main className="grid min-h-screen place-items-center bg-[#080808] font-mono text-xs text-white/45">Loading workspace...</main>

  return <main className="min-h-screen bg-[#080808] font-mono text-white"><div className="flex min-h-screen"><aside className="hidden w-64 shrink-0 flex-col border-r border-white/10 bg-[#0b0b0b] px-5 py-6 lg:flex"><Brand /><div className="mt-16"><p className="mb-4 px-3 text-[10px] uppercase tracking-[0.25em] text-white/25">Workspace</p><div className="space-y-1"><NavItem active={page === 'overview'} onClick={() => setPage('overview')} icon="⌂">Overview</NavItem><NavItem active={page === 'projects'} onClick={() => setPage('projects')} icon="▦">Projects <span className="ml-auto text-[10px] text-white/25">{projects.length}</span></NavItem></div><div className="mt-7 border-t border-white/10 pt-5"><p className="mb-3 px-3 text-[10px] uppercase tracking-[0.2em] text-white/25">Your projects</p><div className="max-h-64 space-y-1 overflow-y-auto">{projects.map((project) => <button key={project.id} onClick={() => openProject(project)} className={`w-full truncate rounded-lg px-3 py-2.5 text-left text-xs transition ${selected?.id === project.id && page === 'project' ? 'bg-white/10 text-white' : 'text-white/40 hover:bg-white/5 hover:text-white'}`}>{project.name}</button>)}{projects.length === 0 && <p className="px-3 text-[10px] leading-5 text-white/25">No projects yet.</p>}</div></div></div><div className="mt-auto rounded-2xl border border-white/10 bg-white/[0.03] p-4"><div className="flex items-center gap-2 text-xs text-white/65"><span className="h-1.5 w-1.5 rounded-full bg-white" /> Workspace ready</div><p className="mt-3 text-[10px] leading-5 text-white/30">Ideas become plans here.</p></div></aside><div className="min-w-0 flex-1"><header className="flex items-center justify-between border-b border-white/10 px-5 py-5 sm:px-8"><div className="lg:hidden"><Brand /></div><div className="hidden items-center gap-2 text-xs text-white/35 lg:flex"><span>CORTEX</span><span>/</span><span>{page === 'project' ? selected?.name : page}</span></div><div className="flex items-center gap-3"><button onClick={() => setPage('projects')} className="rounded-lg border border-white/15 px-3 py-2 text-xs text-white/55 transition hover:border-white/40 hover:text-white">All projects</button><button onClick={onLogout} className="rounded-lg border border-white/15 px-3 py-2 text-xs text-white/55 transition hover:border-white/40 hover:text-white">Log out</button></div></header><div className="mx-auto max-w-[1500px] px-5 py-7 sm:px-8 lg:px-12 lg:py-10">{notice && <div className="mb-6 flex items-center justify-between rounded-xl border border-white/15 bg-white/[0.03] px-4 py-3 text-xs text-white/60"><span>{notice}</span><button onClick={() => setNotice('')} className="text-white/35 hover:text-white">×</button></div>}{page === 'overview' && <Overview projects={projects} runs={runs} completed={completed} onProjects={() => setPage('projects')} onOpen={openProject} />}{page === 'projects' && <Projects projects={projects} newProject={newProject} setNewProject={setNewProject} onCreate={createProject} onOpen={openProject} />}{page === 'project' && selected && <ProjectChat project={selected} mode={mode} setMode={setMode} chats={chats} activeChat={activeChat} setActiveChat={setActiveChat} messages={messages} draft={draft} setDraft={setDraft} requirement={requirement} setRequirement={setRequirement} onCreateChat={createChat} onSend={sendMessage} onBuild={startBuild} runs={runs} onBack={() => setPage('projects')} />}</div></div></div></main>
}

function NavItem({ active, onClick, icon, children }) { return <button onClick={onClick} className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-xs transition ${active ? 'bg-white text-black' : 'text-white/45 hover:bg-white/5 hover:text-white'}`}><span className="w-4 text-center">{icon}</span>{children}</button> }

function Overview({ projects, runs, completed, onProjects, onOpen }) {
  return <section><div className="flex flex-wrap items-end justify-between gap-6"><div><p className="text-[10px] uppercase tracking-[0.25em] text-white/30">Overview</p><h1 className="mt-4 text-4xl tracking-[-0.09em] sm:text-6xl">Good to see you<span className="text-white/30">_</span></h1><p className="mt-4 max-w-lg text-xs leading-6 text-white/40">A quiet command center for your projects, conversations, and engineering work.</p></div><button onClick={onProjects} className="rounded-full bg-white px-5 py-3 text-xs text-black transition hover:bg-white/85">View projects →</button></div><div className="mt-12 grid gap-4 sm:grid-cols-3"><Metric label="Projects" value={projects.length} detail="active workspaces" /><Metric label="Build runs" value={runs.length} detail="engineering attempts" /><Metric label="Completed" value={completed} detail="runs shipped" /></div><div className="mt-8 grid gap-6 xl:grid-cols-[1.25fr_0.75fr]"><div className="rounded-2xl border border-white/10 bg-white/[0.025] p-6"><div className="flex items-center justify-between"><div><p className="text-[10px] uppercase tracking-[0.2em] text-white/30">Recent projects</p><h2 className="mt-3 text-xl tracking-[-0.05em]">Your workspaces</h2></div><button onClick={onProjects} className="text-xs text-white/40 hover:text-white">See all ↗</button></div><div className="mt-7 grid gap-3 sm:grid-cols-2">{projects.slice(0, 4).map((project) => <button key={project.id} onClick={() => onOpen(project)} className="group rounded-xl border border-white/10 p-4 text-left transition hover:-translate-y-0.5 hover:border-white/35 hover:bg-white/[0.04]"><div className="flex items-center justify-between"><span className="h-2 w-2 rounded-full bg-white/45" /><span className="text-[10px] text-white/25">OPEN ↗</span></div><p className="mt-9 truncate text-sm text-white/85">{project.name}</p><p className="mt-2 truncate text-[10px] text-white/35">{project.description ?? 'No description yet.'}</p></button>)}{projects.length === 0 && <p className="col-span-2 py-10 text-center text-xs text-white/30">Your first project is waiting.</p>}</div></div><div className="rounded-2xl border border-white/10 bg-white/[0.025] p-6"><p className="text-[10px] uppercase tracking-[0.2em] text-white/30">Activity</p><h2 className="mt-3 text-xl tracking-[-0.05em]">Latest runs</h2><div className="mt-7 space-y-5">{runs.slice(0, 5).map((run) => <div key={run.id} className="flex gap-3 border-l border-white/20 pl-4"><span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-white/50" /><div><p className="text-xs text-white/70">{run.current_stage ?? 'Build queued'}</p><p className="mt-1 text-[10px] text-white/30">{run.status}</p></div></div>)}{runs.length === 0 && <p className="text-xs text-white/30">No activity yet.</p>}</div></div></div></section>
}

function Projects({ projects, newProject, setNewProject, onCreate, onOpen }) {
  return <section><div className="flex flex-wrap items-end justify-between gap-6"><div><p className="text-[10px] uppercase tracking-[0.25em] text-white/30">Projects</p><h1 className="mt-4 text-4xl tracking-[-0.09em] sm:text-6xl">Every idea,<br /><span className="text-white/35">in one place.</span></h1></div><p className="max-w-xs text-xs leading-6 text-white/35">Choose a project to open its conversations and build workspace.</p></div><div className="mt-12 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{projects.map((project, index) => <button key={project.id} onClick={() => onOpen(project)} className="group min-h-52 rounded-2xl border border-white/10 bg-white/[0.025] p-6 text-left transition duration-300 hover:-translate-y-1 hover:border-white/35 hover:bg-white/[0.05]"><div className="flex items-center justify-between text-[10px] text-white/30"><span>0{index + 1}</span><span className="transition group-hover:text-white">Open project ↗</span></div><h2 className="mt-16 truncate text-lg tracking-[-0.04em]">{project.name}</h2><p className="mt-3 line-clamp-2 text-xs leading-5 text-white/35">{project.description ?? 'A new space for your next build.'}</p></button>)}<form onSubmit={onCreate} className="min-h-52 rounded-2xl border border-dashed border-white/20 p-6"><p className="text-[10px] uppercase tracking-[0.2em] text-white/35">New project</p><input required value={newProject.name} onChange={(event) => setNewProject({ ...newProject, name: event.target.value })} placeholder="Project name" className="mt-8 w-full border-b border-white/15 bg-transparent pb-3 text-sm outline-none placeholder:text-white/25 focus:border-white/60" /><input value={newProject.description} onChange={(event) => setNewProject({ ...newProject, description: event.target.value })} placeholder="Short description" className="mt-4 w-full border-b border-white/15 bg-transparent pb-3 text-xs outline-none placeholder:text-white/25 focus:border-white/60" /><button className="mt-6 rounded-full bg-white px-4 py-2 text-xs text-black">Create →</button></form></div></section>
}

function ProjectChat({ project, mode, setMode, chats, activeChat, setActiveChat, messages, draft, setDraft, requirement, setRequirement, onCreateChat, onSend, onBuild, runs, onBack }) {
  return <section><button onClick={onBack} className="mb-6 text-xs text-white/35 transition hover:text-white">← All projects</button><div className="flex flex-wrap items-end justify-between gap-5 border-b border-white/10 pb-7"><div><p className="text-[10px] uppercase tracking-[0.25em] text-white/30">Project workspace</p><h1 className="mt-3 text-3xl tracking-[-0.07em] sm:text-5xl">{project.name}</h1><p className="mt-3 max-w-xl text-xs text-white/35">{project.description ?? 'A focused space for your next idea.'}</p></div><div className="flex rounded-xl border border-white/10 p-1 text-xs"><button onClick={() => setMode('chat')} className={`rounded-lg px-5 py-2.5 transition ${mode === 'chat' ? 'bg-white text-black' : 'text-white/45 hover:text-white'}`}>Chat</button><button onClick={() => setMode('build')} className={`rounded-lg px-5 py-2.5 transition ${mode === 'build' ? 'bg-white text-black' : 'text-white/45 hover:text-white'}`}>Build</button></div></div>{mode === 'chat' ? <div className="mt-7 grid min-h-[620px] gap-5 rounded-2xl border border-white/10 bg-white/[0.02] p-4 sm:p-6 md:grid-cols-[210px_minmax(0,1fr)]"><aside className="border-b border-white/10 pb-4 md:border-b-0 md:border-r md:pb-0 md:pr-5"><div className="flex items-center justify-between"><p className="text-[10px] uppercase tracking-[0.2em] text-white/30">Conversations</p><button onClick={onCreateChat} className="text-lg text-white/55 hover:text-white">+</button></div><div className="mt-5 space-y-1">{chats.map((chat) => <button key={chat.id} onClick={() => setActiveChat(chat)} className={`w-full truncate rounded-lg px-3 py-3 text-left text-xs ${activeChat?.id === chat.id ? 'bg-white/10 text-white' : 'text-white/40 hover:bg-white/5 hover:text-white'}`}>{chat.title}</button>)}{chats.length === 0 && <button onClick={onCreateChat} className="mt-4 w-full rounded-lg border border-dashed border-white/15 px-3 py-4 text-xs text-white/35">Start a conversation</button>}</div></aside><div className="flex min-h-[520px] min-w-0 flex-col"><div className="border-b border-white/10 pb-4 text-sm text-white/75">{activeChat?.title ?? 'New conversation'}</div><div className="flex-1 space-y-4 overflow-y-auto py-6">{messages.length ? messages.map((message) => <div key={message.id} className={`max-w-[80%] rounded-xl px-4 py-3 text-xs leading-6 ${message.role === 'USER' ? 'ml-auto bg-white text-black' : 'bg-white/5 text-white/65'}`}>{message.content}</div>) : <div className="mx-auto mt-24 max-w-sm text-center"><p className="text-lg text-white/70">What are you thinking about?</p><p className="mt-3 text-xs leading-6 text-white/30">Ask a question, explore a direction, or shape your next build.</p></div>}</div><form onSubmit={onSend} className="flex items-end gap-3 rounded-xl border border-white/10 bg-black/20 p-3"><textarea rows="1" value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Write a message..." className="max-h-32 min-w-0 flex-1 resize-none bg-transparent px-2 py-2 text-xs outline-none placeholder:text-white/25" /><button className="rounded-lg bg-white px-4 py-2.5 text-xs text-black">Send</button></form></div></div> : <div className="mt-7 grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px]"><form onSubmit={onBuild} className="rounded-2xl border border-white/10 bg-white/[0.02] p-6 sm:p-8"><p className="text-[10px] uppercase tracking-[0.2em] text-white/30">New engineering run</p><h2 className="mt-5 text-2xl tracking-[-0.06em]">Start with an idea.</h2><p className="mt-3 max-w-xl text-xs leading-6 text-white/40">Describe the product, feature, or system you want to create. Your agent team will turn it into a plan.</p><textarea required minLength={10} value={requirement} onChange={(event) => setRequirement(event.target.value)} placeholder="I want to build..." className="mt-8 h-64 w-full resize-none rounded-xl border border-white/15 bg-black/20 p-4 text-sm leading-7 outline-none transition focus:border-white/50" /><button className="mt-4 rounded-full bg-white px-6 py-3 text-xs text-black">Queue build →</button></form><aside className="rounded-2xl border border-white/10 bg-white/[0.02] p-6"><p className="text-[10px] uppercase tracking-[0.2em] text-white/30">Build history</p><div className="mt-6 space-y-5">{runs.map((run) => <div key={run.id} className="border-l border-white/20 pl-4"><p className="text-xs text-white/65">{run.current_stage ?? 'Queued run'}</p><p className="mt-1 text-[10px] text-white/30">{run.status}</p></div>)}{runs.length === 0 && <p className="text-xs leading-6 text-white/30">Your engineering runs will appear here.</p>}</div></aside></div>}</section>
}

export default Workspace
