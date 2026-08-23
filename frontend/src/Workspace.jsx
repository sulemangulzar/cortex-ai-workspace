import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL ?? `http://${window.location.hostname}:8000`
const WS_URL = API_URL.replace(/^http/, 'ws')
const RUNNING_STATUSES = new Set(['pending', 'running'])

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

function Workspace({ token, onLogout, onTokenChange }) {
  const [tab, setTab] = useState('activity')
  const [projects, setProjects] = useState([])
  const [activity, setActivity] = useState([])
  const [selected, setSelected] = useState(null)
  const [runs, setRuns] = useState([])
  const [chat, setChat] = useState({ messages: [], uploads: [] })
  const [newProjectName, setNewProjectName] = useState('')
  const [message, setMessage] = useState('')
  const [selectedFilePath, setSelectedFilePath] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(true)
  const [activityLoading, setActivityLoading] = useState(false)
  const [projectLoading, setProjectLoading] = useState(false)
  const [creatingProject, setCreatingProject] = useState(false)
  const [sendingMessage, setSendingMessage] = useState(false)
  const [uploading, setUploading] = useState(false)
  const projectSubmitLock = useRef(false)
  const messageSubmitLock = useRef(false)

  const sendWithAuth = useCallback(async (path, options = {}) => {
    const isFormData = options.body instanceof FormData
    const headers = {
      Authorization: `Bearer ${token}`,
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...options.headers,
    }
    const send = (accessToken) => fetchApi(`${API_URL}${path}`, {
      ...options,
      credentials: 'include',
      headers: { ...headers, Authorization: `Bearer ${accessToken}` },
    })
    let response = await send(token)
    if (response.status === 401 && !path.startsWith('/auth/v1/')) {
      const refreshResponse = await fetchApi(`${API_URL}/auth/v1/refresh`, { method: 'POST', credentials: 'include' })
      if (!refreshResponse.ok) {
        onLogout()
        throw new Error('Your session expired. Please sign in again.')
      }
      const refreshed = await refreshResponse.json()
      localStorage.setItem('access_token', refreshed.access_token)
      onTokenChange(refreshed.access_token)
      response = await send(refreshed.access_token)
    }
    return response
  }, [onLogout, onTokenChange, token])

  const request = useCallback(async (path, options = {}) => {
    const response = await sendWithAuth(path, options)
    const data = response.status === 204 ? null : await response.json()
    if (!response.ok) throw new Error(data?.detail?.[0]?.msg ?? data?.detail ?? 'Request failed')
    return data
  }, [sendWithAuth])

  const downloadZip = useCallback(async (path) => {
    const response = await sendWithAuth(path, { headers: { Accept: 'application/zip' } })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data?.detail ?? 'Download failed')
    }
    const blob = await response.blob()
    const disposition = response.headers.get('content-disposition') ?? ''
    const encodedFilename = disposition.match(/filename\*=UTF-8''([^;]+)/)?.[1]
    const plainFilename = disposition.match(/filename="?([^";]+)"?/)?.[1]
    const filename = encodedFilename ? decodeURIComponent(encodedFilename) : plainFilename ?? 'project-cortex-workspace.zip'
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  }, [sendWithAuth])

  const loadProjects = useCallback(() => request('/projects').then(setProjects), [request])
  const loadActivity = useCallback(async () => {
    setActivityLoading(true)
    try {
      await request('/activity').then(setActivity)
    } finally {
      setActivityLoading(false)
    }
  }, [request])
  const loadProjectData = useCallback(async (projectId) => {
    setProjectLoading(true)
    try {
      await Promise.allSettled([
        request(`/projects/${projectId}/runs`).then(setRuns),
        request(`/projects/${projectId}/chat`).then((data) => setChat({ messages: data.messages ?? [], uploads: data.uploads ?? [] })),
      ])
    } finally {
      setProjectLoading(false)
    }
  }, [request])

  useEffect(() => {
    let active = true
    loadProjects().catch((error) => setNotice(error.message)).finally(() => {
      if (active) setLoading(false)
    })
    const activityTimer = window.setTimeout(() => loadActivity().catch(() => undefined), 0)
    return () => { active = false; window.clearTimeout(activityTimer) }
  }, [loadActivity, loadProjects])

  useEffect(() => {
    let socket
    let reconnectTimer
    let refreshTimer
    let pollTimer
    let closedByEffect = false

    const poll = () => {
      loadActivity().catch(() => undefined)
      if (selected) loadProjectData(selected.id).catch(() => undefined)
      const interval = runs.some((run) => RUNNING_STATUSES.has(run.status)) ? 3000 : 10000
      pollTimer = window.setTimeout(poll, interval)
    }

    const refreshFromEvent = (payload = {}) => {
      window.clearTimeout(refreshTimer)
      refreshTimer = window.setTimeout(() => {
        loadActivity().catch(() => undefined)
        const projectId = payload.project_id ?? selected?.id
        if (selected && projectId === selected.id) loadProjectData(selected.id).catch(() => undefined)
      }, 150)
    }

    const connect = () => {
      socket = new WebSocket(`${WS_URL}/ws?token=${encodeURIComponent(token)}`)
      socket.onopen = () => undefined
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.event !== 'connected') {
            if (String(data.event).startsWith('project.')) loadProjects().catch(() => undefined)
            refreshFromEvent(data.payload)
          }
        } catch {
          refreshFromEvent()
        }
      }
      socket.onerror = () => undefined
      socket.onclose = () => {
        if (closedByEffect) return
        reconnectTimer = window.setTimeout(connect, 2000)
      }
    }

    connect()
    pollTimer = window.setTimeout(poll, 10000)
    return () => {
      closedByEffect = true
      window.clearTimeout(reconnectTimer)
      window.clearTimeout(refreshTimer)
      window.clearTimeout(pollTimer)
      socket?.close()
    }
  }, [loadActivity, loadProjectData, loadProjects, runs, selected, token])

  const latestRun = useMemo(() => runs[0] ?? null, [runs])
  const selectedCodeFile = useMemo(() => {
    const files = latestRun?.code_files ?? []
    return files.find((file) => file.path === selectedFilePath) ?? files[0] ?? null
  }, [latestRun, selectedFilePath])

  async function createProject(event) {
    event.preventDefault()
    if (projectSubmitLock.current || creatingProject) return
    const name = newProjectName.trim()
    if (!name) return
    projectSubmitLock.current = true
    setCreatingProject(true)
    try {
      const project = await request('/projects', { method: 'POST', body: JSON.stringify({ name }) })
      setProjects((current) => [project, ...current.filter((item) => item.id !== project.id)])
      setNewProjectName('')
      openProject(project)
      setNotice('Project created.')
    } catch (error) {
      setNotice(error.message)
    } finally {
      projectSubmitLock.current = false
      setCreatingProject(false)
    }
  }

  async function renameProject(project = selected) {
    if (!project) return
    const name = window.prompt('Rename project', project.name)?.trim()
    if (!name || name === project.name) return
    try {
      const updated = await request(`/projects/${project.id}`, { method: 'PATCH', body: JSON.stringify({ name }) })
      setProjects((current) => current.map((item) => item.id === updated.id ? updated : item))
      setSelected((current) => current?.id === updated.id ? updated : current)
      setNotice('Project renamed.')
    } catch (error) {
      setNotice(error.message)
    }
  }

  async function deleteProject(project = selected) {
    if (!project) return
    if (!window.confirm(`Delete "${project.name}" and all its runs, chat, code, and uploads?`)) return
    try {
      await request(`/projects/${project.id}`, { method: 'DELETE' })
      setProjects((current) => current.filter((item) => item.id !== project.id))
      if (selected?.id === project.id) {
        setSelected(null)
        setRuns([])
        setChat({ messages: [], uploads: [] })
        setTab('projects')
      }
      setNotice('Project deleted.')
    } catch (error) {
      setNotice(error.message)
    }
  }

  function openProject(project) {
    setSelected(project)
    setRuns([])
    setChat({ messages: [], uploads: [] })
    setSelectedFilePath('')
    setTab('studio')
    setNotice('')
    loadProjectData(project.id).catch((error) => setNotice(error.message))
  }

  async function sendMessage(event) {
    event.preventDefault()
    if (!selected || messageSubmitLock.current || sendingMessage) return
    const content = message.trim()
    if (!content) return
    messageSubmitLock.current = true
    setSendingMessage(true)
    try {
      const saved = await request(`/projects/${selected.id}/chat/message`, { method: 'POST', body: JSON.stringify({ content }) })
      setChat((current) => ({ ...current, messages: [...current.messages, saved] }))
      setMessage('')
      setNotice('Agent run started. Activity will update below.')
      await Promise.all([loadProjectData(selected.id), loadActivity()])
    } catch (error) {
      setNotice(error.message)
    } finally {
      messageSubmitLock.current = false
      setSendingMessage(false)
    }
  }

  async function cancelRun() {
    if (!selected || !latestRun || !RUNNING_STATUSES.has(latestRun.status)) return
    try {
      await request(`/projects/${selected.id}/runs/${latestRun.id}/cancel`, { method: 'POST' })
      setNotice('Run cancellation requested. Current agent may finish, but the next agent will not start.')
      await Promise.all([loadProjectData(selected.id), loadActivity()])
    } catch (error) {
      setNotice(error.message)
    }
  }

  async function downloadProject(runId = null, projectId = null) {
    const targetProjectId = projectId ?? selected?.id
    if (!targetProjectId) return
    try {
      const path = runId ? `/projects/${targetProjectId}/runs/${runId}/download` : `/projects/${targetProjectId}/download`
      await downloadZip(path)
    } catch (error) {
      setNotice(error.message)
    }
  }

  async function uploadRequirement(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || !selected) return
    const formData = new FormData()
    formData.append('file', file)
    setUploading(true)
    try {
      await request(`/projects/${selected.id}/chat/upload`, { method: 'POST', body: formData })
      setNotice('Upload saved. Text extraction is running in the background.')
      await loadProjectData(selected.id)
    } catch (error) {
      setNotice(error.message)
    } finally {
      setUploading(false)
    }
  }

  if (loading) return <main className="grid min-h-screen place-items-center bg-[#080808] font-mono text-xs text-white/45">Loading workspace...</main>

  return <main className="min-h-screen bg-[#080808] font-mono text-white selection:bg-white selection:text-black">
    <div className="flex min-h-screen">
      <aside className="hidden w-72 shrink-0 flex-col border-r border-white/10 bg-[#0b0b0b] px-5 py-6 lg:flex">
        <Brand />
        <nav className="mt-14 space-y-2">
          <TabButton active={tab === 'activity'} onClick={() => setTab('activity')} icon="◌" label="Activity" meta={activity.length} />
          <TabButton active={tab === 'projects'} onClick={() => setTab('projects')} icon="▦" label="Projects" meta={projects.length} />
          <TabButton active={tab === 'studio'} onClick={() => selected && setTab('studio')} icon="⌘" label="Project studio" meta={selected ? 'open' : 'none'} disabled={!selected} />
        </nav>
        <div className="mt-8 border-t border-white/10 pt-5">
          <p className="mb-3 px-3 text-[10px] uppercase tracking-[0.2em] text-white/25">Projects</p>
          <div className="max-h-[38vh] space-y-1 overflow-y-auto pr-1">
            {projects.map((project) => <button type="button" key={project.id} onClick={() => openProject(project)} className={`w-full truncate rounded-xl px-3 py-3 text-left text-xs transition ${selected?.id === project.id ? 'bg-white/10 text-white' : 'text-white/40 hover:bg-white/5 hover:text-white'}`}>{project.name}</button>)}
            {projects.length === 0 && <p className="px-3 text-[10px] leading-5 text-white/25">No projects yet.</p>}
          </div>
        </div>
        <div className="mt-auto rounded-2xl border border-white/10 bg-white/[0.03] p-4"><div className="text-xs text-white/65">Workspace ready</div><p className="mt-3 text-[10px] leading-5 text-white/30">Projects, code, logs, and reviews stay updated automatically.</p></div>
      </aside>
      <section className="min-w-0 flex-1">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-5 py-5 sm:px-8">
          <div className="lg:hidden"><Brand /></div>
          <div className="hidden text-xs text-white/35 lg:block">CORTEX / {tab === 'studio' ? selected?.name ?? 'studio' : tab}</div>
          <div className="flex items-center gap-2 lg:hidden"><MobileTab active={tab === 'activity'} onClick={() => setTab('activity')}>Activity</MobileTab><MobileTab active={tab === 'projects'} onClick={() => setTab('projects')}>Projects</MobileTab><MobileTab active={tab === 'studio'} disabled={!selected} onClick={() => selected && setTab('studio')}>Studio</MobileTab></div>
          <button type="button" onClick={onLogout} className="rounded-lg border border-white/15 px-3 py-2 text-xs text-white/55 transition hover:border-white/40 hover:text-white">Log out</button>
        </header>
        <div className="mx-auto max-w-[1700px] px-5 py-7 sm:px-8 lg:px-10">
          {notice && <div className="mb-6 flex items-center justify-between rounded-xl border border-white/15 bg-white/[0.03] px-4 py-3 text-xs text-white/65"><span>{notice}</span><button type="button" onClick={() => setNotice('')} className="text-white/35 hover:text-white">×</button></div>}
          {tab === 'activity' && <ActivityView activity={activity} projects={projects} loading={activityLoading} onOpen={openProject} onDownload={downloadProject} />}
          {tab === 'projects' && <ProjectsView projects={projects} newProjectName={newProjectName} setNewProjectName={setNewProjectName} creating={creatingProject} onCreate={createProject} onOpen={openProject} onRename={renameProject} onDelete={deleteProject} />}
          {tab === 'studio' && selected && <ProjectStudio project={selected} chat={chat} runs={runs} loading={projectLoading} latestRun={latestRun} selectedCodeFile={selectedCodeFile} selectedFilePath={selectedFilePath} setSelectedFilePath={setSelectedFilePath} message={message} setMessage={setMessage} sending={sendingMessage} uploading={uploading} onSend={sendMessage} onUpload={uploadRequirement} onDownload={() => downloadProject(latestRun?.id)} onRename={() => renameProject(selected)} onDelete={() => deleteProject(selected)} onCancel={cancelRun} />}
          {tab === 'studio' && !selected && <EmptyState title="No project open" body="Open a project from the Projects tab to see chat, generated code, and terminal activity." />}
        </div>
      </section>
    </div>
  </main>
}

function TabButton({ active, onClick, icon, label, meta, disabled = false }) {
  return <button type="button" disabled={disabled} onClick={onClick} className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-xs transition disabled:cursor-not-allowed disabled:opacity-35 ${active ? 'bg-white text-black' : 'text-white/45 hover:bg-white/5 hover:text-white'}`}><span className="w-4 text-center">{icon}</span><span>{label}</span><span className="ml-auto text-[10px] opacity-50">{meta}</span></button>
}

function MobileTab({ active, disabled, onClick, children }) {
  return <button type="button" disabled={disabled} onClick={onClick} className={`rounded-full border px-3 py-2 text-[10px] ${active ? 'border-white bg-white text-black' : 'border-white/15 text-white/50'}`}>{children}</button>
}

function ActivityView({ activity, projects, loading, onOpen, onDownload }) {
  return <section><Hero eyebrow="Activity" title="Everything happening now." body="Agent runs, reviewer output, generated files, and terminal logs are read from the database." /><div className="mt-8 grid gap-4 sm:grid-cols-3"><Metric label="Projects" value={projects.length} /><Metric label="Runs" value={activity.length} /><Metric label="Active" value={activity.filter((run) => RUNNING_STATUSES.has(run.status)).length} /></div>{loading && activity.length === 0 && <div className="mt-8 rounded-2xl border border-white/10 bg-white/[0.02] p-6 text-xs text-white/35">Loading activity in the background...</div>}<div className="mt-8 space-y-4">{activity.map((run) => <RunCard key={run.id} run={run} onOpen={onOpen} onDownload={onDownload} />)}{!loading && activity.length === 0 && <EmptyState title="No activity yet" body="Create a project and send a chat message to start the CrewAI pipeline." />}</div></section>
}

function ProjectsView({ projects, newProjectName, setNewProjectName, creating, onCreate, onOpen, onRename, onDelete }) {
  return <section><Hero eyebrow="Projects" title="Your engineering spaces." body="Create or open a project. Opening a project shows chat, generated code, and terminal logs together." /><div className="mt-10 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{projects.map((project, index) => <article key={project.id} className="group min-h-52 rounded-2xl border border-white/10 bg-white/[0.025] p-6 text-left transition hover:-translate-y-1 hover:border-white/35 hover:bg-white/[0.05]"><div className="flex items-center justify-between text-[10px] text-white/30"><span>{String(index + 1).padStart(2, '0')}</span><span className="transition group-hover:text-white">Project</span></div><h2 className="mt-16 truncate text-lg tracking-[-0.04em]">{project.name}</h2><p className="mt-3 text-[10px] text-white/30">Created {formatDate(project.created_at)}</p><div className="mt-6 flex flex-wrap gap-2"><button type="button" onClick={() => onOpen(project)} className="rounded-full bg-white px-4 py-2 text-xs text-black transition hover:bg-white/85">Open ↗</button><button type="button" onClick={() => onRename(project)} className="rounded-full border border-white/15 px-4 py-2 text-xs text-white/55 transition hover:border-white/40 hover:text-white">Rename</button><button type="button" onClick={() => onDelete(project)} className="rounded-full border border-red-300/20 px-4 py-2 text-xs text-red-200/70 transition hover:border-red-300/50 hover:text-red-100">Delete</button></div></article>)}<form onSubmit={onCreate} className="min-h-52 rounded-2xl border border-dashed border-white/20 p-6"><p className="text-[10px] uppercase tracking-[0.2em] text-white/35">New project</p><input required value={newProjectName} onChange={(event) => setNewProjectName(event.target.value)} placeholder="Project name" className="mt-12 w-full border-b border-white/15 bg-transparent pb-3 text-sm outline-none placeholder:text-white/25 focus:border-white/60" /><button type="submit" disabled={creating} className="mt-6 rounded-full bg-white px-4 py-2 text-xs text-black disabled:cursor-wait disabled:opacity-50">{creating ? 'Creating...' : 'Create →'}</button></form></div></section>
}

function ProjectStudio({ project, chat, runs, loading, latestRun, selectedCodeFile, selectedFilePath, setSelectedFilePath, message, setMessage, sending, uploading, onSend, onUpload, onDownload, onRename, onDelete, onCancel }) {
  const files = latestRun?.code_files ?? []
  const terminalLines = terminalLinesForRun(latestRun)
  const canCancel = latestRun && RUNNING_STATUSES.has(latestRun.status)
  return <section className="min-h-[calc(100vh-9rem)]"><div className="mb-5 flex flex-wrap items-end justify-between gap-4"><div><p className="text-[10px] uppercase tracking-[0.25em] text-white/30">Project studio</p><h1 className="mt-3 text-3xl tracking-[-0.07em] sm:text-5xl">{project.name}</h1>{loading && <p className="mt-3 text-xs text-white/35">Loading project data in the background...</p>}</div><div className="flex flex-wrap items-center gap-3"><button type="button" onClick={onRename} className="rounded-full border border-white/15 px-4 py-2 text-xs text-white/60 transition hover:border-white/40 hover:text-white">Rename</button><button type="button" onClick={onDelete} className="rounded-full border border-red-300/20 px-4 py-2 text-xs text-red-200/70 transition hover:border-red-300/50 hover:text-red-100">Delete</button><button type="button" disabled={!canCancel} onClick={onCancel} className="rounded-full border border-amber-300/25 px-4 py-2 text-xs text-amber-100/75 transition hover:border-amber-300/60 hover:text-amber-100 disabled:cursor-not-allowed disabled:opacity-35">Stop run</button><button type="button" disabled={!latestRun?.code_files?.length} onClick={onDownload} className="rounded-full border border-white/15 px-4 py-2 text-xs text-white/60 transition hover:border-white/40 hover:text-white disabled:cursor-not-allowed disabled:opacity-35">Download zip ↓</button><StatusPill status={latestRun?.status ?? 'idle'} /></div></div><div className="grid min-h-[720px] gap-5 xl:grid-cols-[380px_minmax(0,1fr)]"><ChatPanel chat={chat} message={message} setMessage={setMessage} sending={sending} uploading={uploading} onSend={onSend} onUpload={onUpload} /><div className="grid min-h-0 gap-5 xl:grid-rows-[minmax(0,1fr)_260px]"><CodePanel files={files} selectedFilePath={selectedFilePath} selectedCodeFile={selectedCodeFile} setSelectedFilePath={setSelectedFilePath} /><TerminalPanel lines={terminalLines} runs={runs} /></div></div></section>
}

function ChatPanel({ chat, message, setMessage, sending, uploading, onSend, onUpload }) {
  return <aside className="flex min-h-[720px] flex-col rounded-2xl border border-white/10 bg-[#0d0d0d]"><div className="border-b border-white/10 p-5"><div className="flex items-center justify-between"><p className="text-[10px] uppercase tracking-[0.2em] text-white/35">Chat</p><label className="cursor-pointer rounded-full border border-white/15 px-3 py-2 text-[10px] text-white/55 transition hover:border-white/40 hover:text-white">{uploading ? 'Uploading...' : 'Upload doc'}<input type="file" accept=".pdf,.txt,.docx" disabled={uploading} onChange={onUpload} className="hidden" /></label></div>{chat.uploads.length > 0 && <div className="mt-4 flex flex-wrap gap-2">{chat.uploads.map((upload) => <span key={upload.id} className="max-w-full truncate rounded-full border border-white/10 px-2.5 py-1 text-[10px] text-white/35">{upload.file_path.split('/').pop()}</span>)}</div>}</div><div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-5">{chat.messages.map((item) => <div key={item.id} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4"><div className="mb-2 flex items-center justify-between text-[10px] uppercase tracking-[0.16em] text-white/30"><span>{item.role}</span><span>{formatTime(item.created_at)}</span></div><p className="whitespace-pre-wrap text-xs leading-6 text-white/70">{item.content}</p></div>)}{chat.messages.length === 0 && <p className="rounded-2xl border border-dashed border-white/10 p-5 text-xs leading-6 text-white/30">Upload requirements or send a message. The message starts the 8-agent CrewAI pipeline.</p>}</div><form onSubmit={onSend} className="border-t border-white/10 p-4"><textarea value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Tell the agents what to build or fix..." className="h-28 w-full resize-none rounded-xl border border-white/10 bg-black/30 p-3 text-xs leading-5 outline-none placeholder:text-white/25 focus:border-white/45" /><button disabled={sending || !message.trim()} className="mt-3 w-full rounded-full bg-white px-4 py-3 text-xs text-black disabled:cursor-not-allowed disabled:opacity-50">{sending ? 'Sending...' : 'Send & run agents →'}</button></form></aside>
}

function CodePanel({ files, selectedFilePath, selectedCodeFile, setSelectedFilePath }) {
  return <section className="min-h-0 rounded-2xl border border-white/10 bg-[#0d0d0d]"><div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-5 py-4"><div><p className="text-[10px] uppercase tracking-[0.2em] text-white/35">Generated code</p><p className="mt-1 max-w-xl truncate text-xs text-white/60">{selectedCodeFile?.path ?? 'No code files yet'}</p></div>{files.length > 0 && <select value={selectedFilePath || selectedCodeFile?.path || ''} onChange={(event) => setSelectedFilePath(event.target.value)} className="rounded-lg border border-white/10 bg-black px-3 py-2 text-xs text-white/70 outline-none">{files.map((file) => <option key={file.id} value={file.path}>{file.path}</option>)}</select>}</div><div className="h-[520px] overflow-auto p-5">{selectedCodeFile ? <CodeBlock code={selectedCodeFile.content} path={selectedCodeFile.path} /> : <EmptyState title="Waiting for generated files" body="After Agent 3 finishes, real syntax-colored code will appear here from the code_files table." />}</div></section>
}

function TerminalPanel({ lines, runs }) {
  return <section className="min-h-0 rounded-2xl border border-white/10 bg-black"><div className="flex items-center justify-between border-b border-white/10 px-5 py-3"><p className="text-[10px] uppercase tracking-[0.2em] text-white/35">Terminal</p><span className="text-[10px] text-white/30">{runs.length} runs</span></div><div className="h-[205px] overflow-auto p-4 text-[11px] leading-5">{lines.map((line, index) => <div key={`${line}-${index}`} className="grid grid-cols-[52px_minmax(0,1fr)] gap-3"><span className="select-none text-white/25">{String(index + 1).padStart(3, '0')}</span><span className={line.includes('failed') || line.includes('critical') ? 'text-red-300/80' : line.includes('completed') || line.includes('success') ? 'text-emerald-300/75' : 'text-white/55'}>{line}</span></div>)}{lines.length === 0 && <p className="text-white/30">$ waiting for agent activity...</p>}</div></section>
}

function CodeBlock({ code, path }) {
  return <pre className="min-w-full text-[12px] leading-6"><code>{code.split('\n').map((line, index) => <div key={index} className="grid grid-cols-[44px_minmax(0,1fr)] gap-4 hover:bg-white/[0.025]"><span className="select-none text-right text-white/20">{index + 1}</span><span className="whitespace-pre text-white/75">{highlightLine(line, path)}</span></div>)}</code></pre>
}

function highlightLine(line, path) {
  const ext = path.split('.').pop()?.toLowerCase()
  const keywords = ext === 'py' ? ['from', 'import', 'class', 'def', 'return', 'async', 'await', 'if', 'else', 'elif', 'for', 'while', 'try', 'except', 'with', 'as', 'None', 'True', 'False'] : ['const', 'let', 'var', 'function', 'return', 'import', 'from', 'export', 'if', 'else', 'for', 'while', 'async', 'await', 'class', 'new', 'try', 'catch']
  const tokens = line.split(/(\s+|[(){}[\].,;:+\-/*=<>!]+|"[^"]*"|'[^']*'|`[^`]*`)/g).filter(Boolean)
  return tokens.map((token, index) => {
    if (/^\s+$/.test(token)) return token
    if (/^("[^"]*"|'[^']*'|`[^`]*`)$/.test(token)) return <span key={index} className="text-emerald-300/85">{token}</span>
    if (/^\d+(\.\d+)?$/.test(token)) return <span key={index} className="text-cyan-300/80">{token}</span>
    if (keywords.includes(token)) return <span key={index} className="text-fuchsia-300/85">{token}</span>
    if (/^[(){}[\].,;:+\-/*=<>!]+$/.test(token)) return <span key={index} className="text-white/35">{token}</span>
    return <span key={index}>{token}</span>
  })
}

function RunCard({ run, onOpen, onDownload }) {
  const completedTasks = run.agent_tasks?.filter((task) => task.status === 'success').length ?? 0
  const totalTasks = run.agent_tasks?.length ?? 0
  const codeFileCount = run.code_file_count ?? run.code_files?.length ?? 0
  const findingCount = run.review_finding_count ?? run.review_findings?.length ?? 0
  const project = { id: run.project_id, name: run.project_name }
  return <article className="rounded-2xl border border-white/10 bg-white/[0.025] p-5"><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-[10px] uppercase tracking-[0.2em] text-white/30">{run.project_name}</p><h3 className="mt-3 text-lg tracking-[-0.04em]">Run {shortId(run.id)}</h3><p className="mt-2 text-xs text-white/35">{completedTasks}/{totalTasks} agents completed · {codeFileCount} files · {findingCount} findings</p></div><div className="flex items-center gap-3"><StatusPill status={run.status} /><button type="button" disabled={!codeFileCount} onClick={() => onDownload(run.id, run.project_id)} className="rounded-full border border-white/15 px-4 py-2 text-xs text-white/55 hover:border-white/40 hover:text-white disabled:cursor-not-allowed disabled:opacity-35">Download ↓</button><button type="button" onClick={() => onOpen(project)} className="rounded-full border border-white/15 px-4 py-2 text-xs text-white/55 hover:border-white/40 hover:text-white">Open ↗</button></div></div><div className="mt-5 grid gap-2 md:grid-cols-4">{(run.agent_tasks ?? []).slice(0, 8).map((task) => <div key={task.id} className="rounded-xl border border-white/10 px-3 py-2"><p className="truncate text-[10px] text-white/50">{task.agent_name}</p><p className="mt-1 text-[10px] text-white/25">{task.status}</p></div>)}</div></article>
}

function Hero({ eyebrow, title, body }) {
  return <div className="flex flex-wrap items-end justify-between gap-6"><div><p className="text-[10px] uppercase tracking-[0.25em] text-white/30">{eyebrow}</p><h1 className="mt-4 max-w-3xl text-4xl tracking-[-0.09em] sm:text-6xl">{title}</h1><p className="mt-4 max-w-xl text-xs leading-6 text-white/40">{body}</p></div></div>
}

function Metric({ label, value }) {
  return <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-5"><p className="text-[10px] uppercase tracking-[0.2em] text-white/35">{label}</p><p className="mt-6 text-3xl tracking-[-0.08em]">{value}</p></div>
}

function EmptyState({ title, body }) {
  return <div className="rounded-2xl border border-dashed border-white/10 bg-white/[0.015] p-8 text-center"><h3 className="text-sm text-white/70">{title}</h3><p className="mx-auto mt-3 max-w-md text-xs leading-6 text-white/35">{body}</p></div>
}

function StatusPill({ status }) {
  const color = status === 'success' ? 'border-emerald-300/30 text-emerald-200' : status === 'failed' ? 'border-red-300/30 text-red-200' : status === 'needs_revision' ? 'border-amber-300/30 text-amber-200' : RUNNING_STATUSES.has(status) ? 'border-cyan-300/30 text-cyan-200' : 'border-white/15 text-white/45'
  return <span className={`rounded-full border px-3 py-1.5 text-[10px] uppercase tracking-[0.18em] ${color}`}>{String(status).replace('_', ' ')}</span>
}

function terminalLinesForRun(run) {
  if (!run) return []
  const taskLines = (run.agent_tasks ?? []).map((task) => `$ ${task.agent_name}: ${task.status}`)
  const logLines = (run.execution_logs ?? []).map((log) => `[${formatTime(log.timestamp)}] ${log.source}: ${log.content}`)
  const findingLines = (run.review_findings ?? []).slice(0, 20).map((finding) => `! ${finding.severity} ${finding.reviewer_agent}: ${finding.message.split('\n')[0]}`)
  return [...taskLines, ...logLines, ...findingLines]
}

function shortId(id) {
  return String(id).slice(0, 8)
}

function formatDate(value) {
  return value ? new Date(value).toLocaleDateString() : 'unknown'
}

function formatTime(value) {
  return value ? new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '--:--'
}

export default Workspace
