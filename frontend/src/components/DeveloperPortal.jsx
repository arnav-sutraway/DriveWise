import { useEffect, useState } from 'react';

const API = '/api/v1/developer';

function csrfToken() {
  const match = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : '';
}

async function api(path, options = {}) {
  const method = options.method || 'GET';
  if (method !== 'GET') {
    await fetch(`${API}/csrf/`, { credentials: 'same-origin' }).catch(() => {});
  }
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData)) headers.set('Accept', 'application/json');
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  if (method !== 'GET') headers.set('X-CSRFToken', csrfToken());
  const response = await fetch(`${API}${path}`, {
    credentials: 'same-origin',
    ...options,
    method,
    headers,
  });
  const payload = await response.json().catch(() => ({ detail: 'Invalid server response.' }));
  if (!response.ok) {
    if (response.status === 404 && path.startsWith('/')) {
      throw new Error(
        'The Developer API is not available on the production backend yet. Deploy the latest backend code and run its database migrations.',
      );
    }
    throw new Error(payload.detail || 'Request failed');
  }
  return payload;
}

function Field({ label, children }) {
  return <label className="dev-field"><span>{label}</span>{children}</label>;
}

export default function DeveloperPortal() {
  const [session, setSession] = useState(null);
  const [section, setSection] = useState('Dashboard');
  const [dashboard, setDashboard] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [tests, setTests] = useState([]);
  const [runs, setRuns] = useState([]);
  const [config, setConfig] = useState(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api('/session/').then(setSession).catch(() => setSession({ authenticated: false }));
  }, []);

  useEffect(() => {
    if (session?.authenticated) refreshAll();
  }, [session?.authenticated]);

  async function refreshAll() {
    try {
      const [dash, docs, testData, runData, cfg] = await Promise.all([
        api('/dashboard/'), api('/documents/'), api('/tests/'),
        api('/evaluations/'), api('/config/'),
      ]);
      setDashboard(dash); setDocuments(docs.documents); setTests(testData.tests);
      setRuns(runData.runs); setConfig(cfg);
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function login(event) {
    event.preventDefault();
    setBusy(true);
    const form = new FormData(event.currentTarget);
    try {
      const next = await api('/session/', {
        method: 'POST',
        body: JSON.stringify({ username: form.get('username'), password: form.get('password') }),
      });
      setSession(next);
      setMessage('');
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    await api('/session/', { method: 'DELETE' }).catch(() => {});
    setSession({ authenticated: false });
  }

  if (!session) return <div className="dev-loading">Loading developer portal…</div>;
  if (!session.authenticated) return (
    <main className="dev-login">
      <form className="dev-login-card" onSubmit={login}>
        <span className="dev-logo">DW</span>
        <p className="dev-kicker">DRIVEWISE AI / INTERNAL</p>
        <h1>Developer Portal</h1>
        <p>Sign in with an authorized staff account.</p>
        <Field label="Username"><input name="username" required autoComplete="username" /></Field>
        <Field label="Password"><input name="password" type="password" required autoComplete="current-password" /></Field>
        {message && <div className="dev-alert error">{message}</div>}
        <button className="dev-primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
        <a className="dev-back" href="/">← Back to DriveWise AI</a>
      </form>
    </main>
  );

  const sections = ['Dashboard', 'Knowledge Base', 'Data Ingestion', 'Preprocessing', 'Response Evaluation', 'System Configuration'];

  return (
    <div className="dev-shell">
      <aside className="dev-sidebar">
        <div className="dev-brand"><span>DW</span><div>DriveWise <small>Developer</small></div></div>
        <nav>
          {sections.map(item => (
            <button key={item} className={section === item ? 'active' : ''} onClick={() => setSection(item)}>
              {item}
            </button>
          ))}
        </nav>
        <div className="dev-user"><div>{session.username?.[0]?.toUpperCase()}</div><span>{session.username}<small>Developer</small></span><button onClick={logout}>Logout</button></div>
      </aside>
      <main className="dev-main">
        <header className="dev-header"><div><p>Developer Portal</p><h1>{section}</h1></div><button className="dev-secondary" onClick={refreshAll}>Refresh</button></header>
        {message && <div className="dev-alert">{message}<button onClick={() => setMessage('')}>×</button></div>}
        {section === 'Dashboard' && <Dashboard data={dashboard} onNavigate={setSection} />}
        {section === 'Knowledge Base' && <KnowledgeBase documents={documents} refresh={refreshAll} notify={setMessage} />}
        {section === 'Data Ingestion' && <Ingestion refresh={refreshAll} notify={setMessage} />}
        {section === 'Preprocessing' && <Preprocessing notify={setMessage} />}
        {section === 'Response Evaluation' && <Evaluation tests={tests} runs={runs} refresh={refreshAll} notify={setMessage} />}
        {section === 'System Configuration' && <Configuration config={config} refresh={refreshAll} notify={setMessage} />}
      </main>
    </div>
  );
}

function Dashboard({ data, onNavigate }) {
  if (!data) return <div className="dev-loading">Loading metrics…</div>;
  const cards = [
    ['Ingested documents', data.document_count],
    ['Indexed chunks', data.chunk_count],
    ['Knowledge sources', data.source_count],
    ['Vector index', data.vector_index_status],
  ];
  return <>
    <section className="dev-cards">{cards.map(([label, value]) => <article key={label}><span>{label}</span><strong>{value}</strong></article>)}</section>
    <section className="dev-grid">
      <article className="dev-panel"><h2>System status</h2><dl><dt>Embedding model</dt><dd>{data.embedding_model}</dd><dt>Recent activity</dt><dd>{data.recent_ingestion?.title || 'No documents ingested'}</dd></dl></article>
      <article className="dev-panel"><h2>Quick actions</h2><div className="dev-actions"><button onClick={() => onNavigate('Data Ingestion')}>Ingest data</button><button onClick={() => onNavigate('Knowledge Base')}>Manage documents</button><button onClick={() => onNavigate('Response Evaluation')}>Run evaluation</button></div></article>
      <article className="dev-panel dev-span"><h2>Recent ingestion errors</h2>{data.recent_errors?.length ? data.recent_errors.map(error => <div className="dev-list-row" key={error.id}><strong>{error.title}</strong><span>{error.processing_error}</span></div>) : <p className="dev-empty">No recent ingestion errors.</p>}</article>
    </section>
  </>;
}

function KnowledgeBase({ documents, refresh, notify }) {
  const [search, setSearch] = useState('');
  async function removeDocument(id) {
    if (!window.confirm('Delete this document and all of its indexed chunks?')) return;
    try { await api(`/documents/${id}/`, { method: 'DELETE' }); notify('Document deleted.'); refresh(); }
    catch (error) { notify(error.message); }
  }
  async function reprocess(id) {
    try { await api(`/documents/${id}/reprocess/`, { method: 'POST', body: '{}' }); notify('Document reprocessed.'); refresh(); }
    catch (error) { notify(error.message); }
  }
  const visible = documents.filter(doc => `${doc.title} ${doc.category} ${doc.source_organization}`.toLowerCase().includes(search.toLowerCase()));
  return <section className="dev-panel">
    <div className="dev-table-tools"><h2>Documents</h2><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search documents…" /></div>
    <div className="dev-table-wrap"><table className="dev-table"><thead><tr><th>Name</th><th>Category</th><th>Status</th><th>Chunks</th><th>Uploaded</th><th></th></tr></thead>
      <tbody>{visible.map(doc => <tr key={doc.id}><td><strong>{doc.title}</strong><small>{doc.source_url || doc.source_path}</small></td><td>{doc.category || '—'}</td><td><span className={`dev-status ${doc.processing_status}`}>{doc.processing_status}</span></td><td>{doc.chunk_count}</td><td>{new Date(doc.created_at).toLocaleDateString()}</td><td className="dev-row-actions"><button onClick={() => reprocess(doc.id)}>Reprocess</button><button className="danger" onClick={() => removeDocument(doc.id)}>Delete</button></td></tr>)}</tbody>
    </table></div>
    {!visible.length && <p className="dev-empty">No matching documents.</p>}
  </section>;
}

function Ingestion({ refresh, notify }) {
  const [mode, setMode] = useState('files');
  const [url, setUrl] = useState('');
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  async function submitFiles(event) {
    event.preventDefault(); setBusy(true);
    const form = new FormData(event.currentTarget);
    try { const result = await api('/ingest/upload/', { method: 'POST', body: form }); notify(result.results.map(item => `${item.name}: ${item.status}`).join(' · ')); refresh(); }
    catch (error) { notify(error.message); } finally { setBusy(false); }
  }
  async function submitText(event) {
    event.preventDefault(); setBusy(true);
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries());
    try { await api('/ingest/text/', { method: 'POST', body: JSON.stringify(payload) }); notify('Text ingested successfully.'); refresh(); event.currentTarget.reset(); }
    catch (error) { notify(error.message); } finally { setBusy(false); }
  }
  async function previewUrl(event) {
    event.preventDefault(); setBusy(true);
    try { setPreview(await api('/ingest/url/preview/', { method: 'POST', body: JSON.stringify({ url }) })); }
    catch (error) { notify(error.message); } finally { setBusy(false); }
  }
  async function ingestUrl(event) {
    event.preventDefault(); setBusy(true);
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries()); payload.url = url;
    try { await api('/ingest/url/', { method: 'POST', body: JSON.stringify(payload) }); notify('URL ingested successfully.'); setPreview(null); refresh(); }
    catch (error) { notify(error.message); } finally { setBusy(false); }
  }
  return <section className="dev-panel">
    <div className="dev-tabs"><button className={mode === 'files' ? 'active' : ''} onClick={() => setMode('files')}>Files & text</button><button className={mode === 'url' ? 'active' : ''} onClick={() => setMode('url')}>URL/API</button></div>
    {mode === 'files' ? <div className="dev-form-grid">
      <form onSubmit={submitFiles}>
        <h2>Upload documents</h2><input type="file" name="files" multiple accept=".pdf,.txt,.md" required />
        <div className="dev-two"><Field label="Category"><input name="category" /></Field><Field label="Jurisdiction"><input name="jurisdiction" /></Field></div>
        <Field label="Source organization"><input name="source_organization" /></Field><Field label="Source URL"><input name="source_url" type="url" /></Field>
        <Field label="Description"><textarea name="description" /></Field><button className="dev-primary" disabled={busy}>{busy ? 'Ingesting…' : 'Upload & ingest'}</button>
      </form>
      <form onSubmit={submitText}>
        <h2>Add custom text</h2><Field label="Title"><input name="title" /></Field><Field label="Text"><textarea name="text" rows="8" required /></Field>
        <div className="dev-two"><Field label="Category"><input name="category" /></Field><Field label="Jurisdiction"><input name="jurisdiction" /></Field></div>
        <button className="dev-primary" disabled={busy}>{busy ? 'Ingesting…' : 'Add & ingest'}</button>
      </form>
    </div> : <div className="dev-url">
      {!preview ? <form onSubmit={previewUrl}><Field label="Public HTTPS URL"><input value={url} onChange={event => setUrl(event.target.value)} type="url" required placeholder="https://dds.georgia.gov/..." /></Field><button className="dev-primary" disabled={busy}>{busy ? 'Fetching…' : 'Fetch & preview'}</button></form> :
        <form onSubmit={ingestUrl}><h2>{preview.title}</h2><pre className="dev-preview">{preview.text.slice(0, 6000)}</pre>
          <div className="dev-two"><Field label="Document title"><input name="title" defaultValue={preview.title} /></Field><Field label="Category"><input name="category" /></Field></div>
          <Field label="Source organization"><input name="source_organization" /></Field><Field label="Description"><textarea name="description" /></Field>
          <div className="dev-actions"><button className="dev-primary" disabled={busy}>Confirm & ingest</button><button type="button" className="dev-secondary" onClick={() => setPreview(null)}>Fetch another URL</button></div>
        </form>}
    </div>}
  </section>;
}

function Preprocessing({ notify }) {
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault(); setBusy(true);
    const form = new FormData(event.currentTarget);
    try {
      const result = await api('/preprocess/preview/', { method: 'POST', body: JSON.stringify({
        text: form.get('text'), chunk_size: Number(form.get('chunk_size')), chunk_overlap: Number(form.get('chunk_overlap')),
      }) });
      setPreview(result);
    } catch (error) { notify(error.message); } finally { setBusy(false); }
  }
  return <section className="dev-grid">
    <form className="dev-panel" onSubmit={submit}><h2>Preprocessing settings</h2>
      <Field label="Source text"><textarea name="text" rows="12" required /></Field>
      <div className="dev-two"><Field label="Chunk size (words)"><input name="chunk_size" type="number" min="15" max="2000" defaultValue="220" /></Field><Field label="Overlap (words)"><input name="chunk_overlap" type="number" min="0" defaultValue="40" /></Field></div>
      <button className="dev-primary" disabled={busy}>{busy ? 'Processing…' : 'Preview chunks'}</button>
    </form>
    <div className="dev-panel"><h2>Processed preview</h2>
      {!preview ? <p className="dev-empty">Submit text to inspect cleaned content and chunks.</p> : <>
        <div className="dev-summary"><span>{preview.chunks.length} chunks</span><span>{preview.duplicate_line_count} duplicate lines</span></div>
        <pre className="dev-preview">{preview.cleaned_text.slice(0, 2500)}</pre>
        {preview.chunks.map(chunk => <details className="dev-chunk" key={chunk.position}><summary>Chunk {chunk.position + 1}{chunk.page ? ` · Page ${chunk.page}` : ''}</summary><p>{chunk.text}</p></details>)}
      </>}
    </div>
  </section>;
}

function Evaluation({ tests, runs, refresh, notify }) {
  async function submitTest(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try { await api('/tests/', { method: 'POST', body: JSON.stringify(Object.fromEntries(form.entries())) }); notify('Test case created.'); event.currentTarget.reset(); refresh(); }
    catch (error) { notify(error.message); }
  }
  async function removeTest(id) {
    if (!window.confirm('Delete this test case?')) return;
    try { await api(`/tests/${id}/`, { method: 'DELETE' }); refresh(); } catch (error) { notify(error.message); }
  }
  async function runTests(testId) {
    try {
      const body = testId ? { test_ids: [testId] } : {};
      await api('/evaluations/run/', { method: 'POST', body: JSON.stringify(body) });
      notify(testId ? 'Test rerun complete.' : 'Evaluation suite complete.'); refresh();
    } catch (error) { notify(error.message); }
  }
  return <section className="dev-evaluation">
    <div className="dev-panel"><div className="dev-table-tools"><h2>Test cases</h2><button className="dev-primary" onClick={() => runTests()}>Run full suite</button></div>
      <div className="dev-table-wrap"><table className="dev-table"><thead><tr><th>Question</th><th>Category</th><th>Concepts</th><th></th></tr></thead><tbody>{tests.map(test => <tr key={test.id}><td><strong>{test.question}</strong></td><td>{test.category || '—'}</td><td>{test.required_concepts || '—'}</td><td className="dev-row-actions"><button onClick={() => runTests(test.id)}>Run</button><button className="danger" onClick={() => removeTest(test.id)}>Delete</button></td></tr>)}</tbody></table></div>
      {!tests.length && <p className="dev-empty">No test cases yet.</p>}
    </div>
    <form className="dev-panel" onSubmit={submitTest}><h2>Create test case</h2>
      <Field label="Test question"><textarea name="question" required /></Field><Field label="Expected answer"><textarea name="expected_answer" required /></Field>
      <div className="dev-two"><Field label="Category"><input name="category" placeholder="parking, intersections, highway, emergencies" /></Field><Field label="Expected source documents"><input name="expected_sources" /></Field></div>
      <div className="dev-two"><Field label="Required concepts"><input name="required_concepts" placeholder="comma-separated" /></Field><Field label="Expected visualization scenario"><input name="expected_visualization" /></Field></div>
      <Field label="Description"><textarea name="description" /></Field><button className="dev-primary">Create test case</button>
    </form>
    <div className="dev-panel dev-span"><h2>Evaluation history</h2>{runs.length ? <div className="dev-table-wrap"><table className="dev-table"><thead><tr><th>Run</th><th>Total</th><th>Passed</th><th>Failed</th><th>Pass %</th><th>Date</th></tr></thead><tbody>{runs.map(run => <tr key={run.id}><td>{run.name}</td><td>{run.total_tests}</td><td>{run.passed_tests}</td><td>{run.failed_tests}</td><td>{run.pass_percentage}%</td><td>{new Date(run.started_at).toLocaleString()}</td></tr>)}</tbody></table></div> : <p className="dev-empty">No evaluation runs yet.</p>}</div>
  </section>;
}

function Configuration({ config, refresh, notify }) {
  if (!config) return <div className="dev-loading">Loading configuration…</div>;
  async function submit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries());
    payload.chunk_size = Number(payload.chunk_size); payload.chunk_overlap = Number(payload.chunk_overlap);
    payload.top_k = Number(payload.top_k); payload.similarity_threshold = Number(payload.similarity_threshold);
    try { await api('/config/', { method: 'POST', body: JSON.stringify(payload) }); notify('Configuration updated.'); refresh(); }
    catch (error) { notify(error.message); }
  }
  return <form className="dev-panel dev-config" onSubmit={submit}><h2>Active RAG configuration</h2>
    <div className="dev-form-grid">
      <Field label="Chunk size"><input name="chunk_size" type="number" min="15" max="2000" defaultValue={config.chunk_size} /></Field>
      <Field label="Chunk overlap"><input name="chunk_overlap" type="number" min="0" defaultValue={config.chunk_overlap} /></Field>
      <Field label="Retrieved chunks (top-k)"><input name="top_k" type="number" min="1" max="100" defaultValue={config.top_k} /></Field>
      <Field label="Similarity threshold"><input name="similarity_threshold" type="number" min="0" max="1" step="0.01" defaultValue={config.similarity_threshold} /></Field>
      <Field label="Embedding model"><input name="embedding_model" defaultValue={config.embedding_model} /></Field>
      <Field label="LLM model"><input name="llm_model" defaultValue={config.llm_model} /></Field>
    </div><div className="dev-provider">Active embedding provider: <strong>{config.provider}</strong></div><button className="dev-primary">Save configuration</button>
  </form>;
}
