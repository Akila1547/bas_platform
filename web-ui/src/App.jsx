import React, { useState, useEffect, useRef } from 'react';
import {
  Shield, Activity, Server, AlertTriangle, Play, Terminal,
  FileText, CheckCircle, Moon, Sun, Clock, Database, Crosshair,
  Download, ChevronDown, ChevronUp, XCircle
} from 'lucide-react';
import './index.css';

const API_BASE = 'http://localhost:8000/api/v1';

function StatusBadge({ status }) {
  const colorMap = {
    completed: 'var(--success-color)',
    active: 'var(--success-color)',
    blocked: 'var(--warning-color)',
    beacon: 'var(--accent-color)',
  };
  const color = colorMap[status] || 'var(--danger-color)';
  const icon = (status === 'completed' || status === 'active' || status === 'beacon')
    ? <CheckCircle size={13} />
    : <XCircle size={13} />;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color, fontWeight: 600, fontSize: '0.82rem', textTransform: 'uppercase' }}>
      {icon} {status}
    </span>
  );
}

function App() {
  const [theme, setTheme] = useState('dark');
  const [activeTab, setActiveTab] = useState('dashboard');

  // Data States
  const [dashboardData, setDashboardData] = useState(null);
  const [attackTable, setAttackTable] = useState([]);
  const [showAttackTable, setShowAttackTable] = useState(false);
  const [evaluationData, setEvaluationData] = useState(null);
  const [liveEvents, setLiveEvents] = useState(null);
  const [c2Data, setC2Data] = useState(null);
  const [c2Agents, setC2Agents] = useState([]);
  const [expandedRow, setExpandedRow] = useState(null);

  // Terminal State
  const [terminalOutput, setTerminalOutput] = useState([]);
  const terminalContainerRef = useRef(null);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // Fetch data per active tab
  useEffect(() => {
    const fetchData = async () => {
      if (activeTab === 'dashboard') {
        try {
          const [sumRes, tableRes] = await Promise.all([
            fetch(`${API_BASE}/dashboard/summary`),
            fetch(`${API_BASE}/reports/attack-table`)
          ]);
          setDashboardData(await sumRes.json());
          setAttackTable(await tableRes.json());
        } catch (e) { console.error('Dashboard fetch error', e); }
      } else if (activeTab === 'evaluation') {
        try {
          const [evalRes, eventsRes] = await Promise.all([
            fetch(`${API_BASE}/evaluation/metrics`),
            fetch(`${API_BASE}/evaluation/live-events`),
          ]);
          setEvaluationData(await evalRes.json());
          setLiveEvents(await eventsRes.json());
        } catch (e) { console.error('Evaluation fetch error', e); }
      } else if (activeTab === 'c2') {
        try {
          const res = await fetch(`${API_BASE}/c2/status`);
          const data = await res.json();
          setC2Data(data);
          if (data.connected) {
            const agRes = await fetch(`${API_BASE}/c2/agents`);
            setC2Agents(await agRes.json());
          }
        } catch (e) { console.error('C2 fetch error', e); }
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [activeTab]);

  // Poll Playbook Logs when on playbooks tab
  useEffect(() => {
    let logInterval;
    if (activeTab === 'playbooks') {
      const fetchLogs = async () => {
        try {
          const res = await fetch(`${API_BASE}/playbooks/logs`);
          const data = await res.json();
          if (data.logs) setTerminalOutput(data.logs);
        } catch (e) { /* ignore */ }
      };
      fetchLogs();
      logInterval = setInterval(fetchLogs, 2000);
    }
    return () => clearInterval(logInterval);
  }, [activeTab]);

  const runPlaybook = async (name) => {
    setTerminalOutput([`> Initializing playbook: ${name}...`]);
    try {
      const res = await fetch(`${API_BASE}/playbooks/execute/${name}`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) setTerminalOutput([`[ERROR] ${data.detail || 'Failed to start playbook'}`]);
    } catch (e) {
      setTerminalOutput([`[ERROR] Failed to connect: ${e.message}`]);
    }
  };

  const recheckLogs = async () => {
    setEvaluationData(null);
    setLiveEvents(null);
    try {
      const [evalRes, eventsRes] = await Promise.all([
        fetch(`${API_BASE}/evaluation/metrics`),
        fetch(`${API_BASE}/evaluation/live-events`),
      ]);
      setEvaluationData(await evalRes.json());
      setLiveEvents(await eventsRes.json());
    } catch (e) { console.error('Recheck error', e); }
  };

  const downloadReport = (playbookKey) => {
    window.open(`${API_BASE}/reports/download/${playbookKey}`, '_blank');
  };

  // Smart auto-scroll: only scroll to bottom if user is already near the bottom
  useEffect(() => {
    const el = terminalContainerRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
    if (nearBottom) el.scrollTop = el.scrollHeight;
  }, [terminalOutput]);

  const scrollTerminalToBottom = () => {
    const el = terminalContainerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  };

  // ─────────────────── DASHBOARD ───────────────────
  const renderDashboard = () => {
    if (!dashboardData) return <div className="loading">Loading System Telemetry...</div>;
    const { victim_health, attacks, safety_status } = dashboardData;

    return (
      <div className="view-container">
        <h2 className="view-title"><Activity className="icon" /> System Overview</h2>

        <div className="grid-3">
          <div className="card">
            <h3>Target Health</h3>
            <div className="metric-large" style={{ color: victim_health.score > 70 ? 'var(--success-color)' : 'var(--danger-color)' }}>
              {victim_health.score.toFixed(1)}%
            </div>
            <p className="detailText">CPU: {victim_health.cpu}% | RAM: {victim_health.memory}%</p>
          </div>

          <div className="card">
            <h3>Safety Controls</h3>
            <div className="metric-row">
              <Shield className="icon" />
              <span style={{ textTransform: 'uppercase', fontWeight: 'bold' }}>{safety_status.level}</span>
            </div>
            <p className="detailText">Kill Switch: {safety_status.kill_switch ? '🔴 TRIGGERED' : '🟢 ARMED'}</p>
          </div>

          {/* Clickable Attack Telemetry Card */}
          <div className="card clickable-card" onClick={() => setShowAttackTable(!showAttackTable)}>
            <h3>Attack Telemetry <span style={{ float: 'right', color: 'var(--accent-color)' }}>{showAttackTable ? <ChevronUp size={18} /> : <ChevronDown size={18} />}</span></h3>
            <div className="metric-row">
              <Crosshair className="icon" />
              <span>{attacks.total} Techniques Executed</span>
            </div>
            <p className="detailText">✅ {attacks.completed} Completed &nbsp; ❌ {attacks.failed} Failed</p>
            <p className="detailText" style={{ color: 'var(--accent-color)', marginTop: 8 }}>Click to expand details</p>
          </div>
        </div>

        {/* Expandable Attack Table */}
        {showAttackTable && (
          <div className="card" style={{ marginTop: '24px' }}>
            <h3 style={{ marginBottom: '16px' }}><FileText size={16} style={{ display: 'inline', marginRight: 8 }} />Detailed Attack Results</h3>
            {attackTable.length === 0 ? (
              <p className="detailText">No attacks recorded yet. Launch a playbook to populate this table.</p>
            ) : (
              <div className="table-wrapper">
                <table className="attack-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Technique</th>
                      <th>Tactic</th>
                      <th>Target</th>
                      <th>Status</th>
                      <th>Duration</th>
                      <th>Health Impact</th>
                      <th>Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attackTable.map((row, i) => (
                      <React.Fragment key={i}>
                        <tr className={expandedRow === i ? 'row-expanded' : ''} onClick={() => setExpandedRow(expandedRow === i ? null : i)}>
                          <td><code>{row.attack_id}</code></td>
                          <td><strong>{row.technique_id}</strong><br /><span className="detailText">{row.technique_name}</span></td>
                          <td><span className="tactic-badge">{row.tactic}</span></td>
                          <td>{row.target_ip}</td>
                          <td><StatusBadge status={row.status} /></td>
                          <td>{row.duration_seconds}s</td>
                          <td>{row.health_impact > 0 ? `-${row.health_impact}` : '0'}</td>
                          <td style={{ color: 'var(--accent-color)', cursor: 'pointer' }}>
                            {expandedRow === i ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                          </td>
                        </tr>
                        {expandedRow === i && (
                          <tr>
                            <td colSpan="8" style={{ backgroundColor: 'rgba(0,0,0,0.2)', padding: '12px 16px' }}>
                              {row.command_output ? (
                                <pre className="output-preview">{row.command_output}</pre>
                              ) : row.error_message ? (
                                <span style={{ color: 'var(--danger-color)' }}>{row.error_message}</span>
                              ) : (
                                <span className="detailText">No output captured</span>
                              )}
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Reports Download Section */}
        <div className="card" style={{ marginTop: '24px' }}>
          <h3 style={{ marginBottom: '16px' }}><Download size={16} style={{ display: 'inline', marginRight: 8 }} />Download Playbook Reports (JSON)</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
            {[
              { key: 'discovery', label: 'Discovery Report' },
              { key: 'credential_access', label: 'Credential Access Report' },
              { key: 'privilege_escalation', label: 'Privilege Escalation Report' },
              { key: 'defense_evasion', label: 'Defense Evasion Report' },
              { key: 'lateral_movement', label: 'Lateral Movement Report' },
              { key: 'ransomware', label: 'Ransomware Simulation Report' },
            ].map(r => (
              <button key={r.key} className="btn" style={{ fontSize: '0.85rem' }} onClick={() => downloadReport(r.key)}>
                <Download size={14} /> {r.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  };

  // ─────────────────── PLAYBOOKS ───────────────────
  const renderPlaybooks = () => (
    <div className="view-container">
      <h2 className="view-title"><Play className="icon" /> Execution Playbooks</h2>
      <div className="grid-2">
        <div className="card">
          <h3>Available Playbooks</h3>
          <div className="playbook-list">
            {[
              { num: 1, name: 'Discovery Playbook', desc: 'Reconnaissance and network mapping (T1087, T1057...)', key: 'discovery_phase', cls: 'btn' },
              { num: 2, name: 'Credential Access', desc: 'OS Credential Dumping and SAM extraction (T1003.001...)', key: 'credential_access', cls: 'btn btn-warning' },
              { num: 3, name: 'Privilege Escalation', desc: 'Scheduled Task creation & execution (T1053.005...)', key: 'privilege_escalation', cls: 'btn btn-warning' },
              { num: 4, name: 'Defense Evasion (Adaptive)', desc: 'Tests A/V disable & log clearing with adaptive fallbacks', key: 'defense_evasion_adaptive', cls: 'btn btn-warning' },
              { num: 5, name: 'Lateral Movement', desc: 'Sliver C2 SMB movement & file transfer simulation (T1021.002...)', key: 'lateral_movement_sliver', cls: 'btn' },
              { num: 6, name: 'Ransomware Simulation', desc: 'Sandbox encryption and ransom note drop (T1486)', key: 'ransomware_simulation', cls: 'btn btn-danger', icon: <AlertTriangle size={16} />, label: 'Launch (Requires Full Safety)' },
            ].map(p => (
              <div key={p.key} className="playbook-item">
                <div>
                  <h4>{p.num}. {p.name}</h4>
                  <p className="detailText">{p.desc}</p>
                </div>
                <button className={p.cls} onClick={() => { setActiveTab('playbooks'); setTimeout(() => runPlaybook(p.key), 100); }}>
                  {p.icon || <Play size={16} />} {p.label || 'Launch'}
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="card terminal-card" style={{ position: 'sticky', top: '24px' }}>
          <div className="terminal-header">
            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}><Terminal size={16} /> Live Terminal Output</span>
            <span style={{ display: 'flex', gap: 8 }}>
              <button className="term-btn" onClick={scrollTerminalToBottom}>⬇ Bottom</button>
              <button className="term-btn" onClick={() => setTerminalOutput([])}>✕ Clear</button>
            </span>
          </div>
          <div className="terminal-window" style={{ minHeight: '500px', overflowY: 'auto' }} ref={terminalContainerRef}>
            {terminalOutput.length === 0 ? (
              <span style={{ color: '#555' }}>Waiting for playbook execution...</span>
            ) : (
              terminalOutput.map((line, i) => <div key={i}>{line}</div>)
            )}
          </div>
        </div>
      </div>
    </div>
  );

  // ─────────────────── EVALUATION ───────────────────
  // ─────────────────── EVALUATION ───────────────────
  const renderEvaluation = () => {
    if (!evaluationData) {
      return <div className="loading">Querying Windows Event Viewer via WinRM… Please wait.</div>;
    }

    const tpr = evaluationData.tpr ?? 0;
    const mttd = evaluationData.mttd ?? null;
    const total_executed = evaluationData.total_executed ?? 0;
    const detected_tech = evaluationData.detected_techniques ?? 0;
    const details = evaluationData.details ?? {};
    const records = (liveEvents && Array.isArray(liveEvents.records)) ? liveEvents.records : [];
    const totalRecs = liveEvents?.total_records ?? 0;
    const queriedCount = liveEvents?.queried_techniques?.length ?? 0;
    const detailEntries = Object.entries(details).filter(([, evts]) => Array.isArray(evts) && evts.length > 0);

    return (
      <div className="view-container">
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
          <h2 className="view-title" style={{ marginBottom: 0 }}>
            <Database className="icon" /> Purple Team Evaluation
          </h2>
          <button className="btn" onClick={recheckLogs} style={{ fontSize: '0.85rem' }}>
            🔄 Re-check Live Logs
          </button>
        </div>

        {/* 2 Provable Metrics */}
        <div className="grid-2-metrics">
          <div className="metric-box metric-tpr">
            <div className="metric-label">True Positive Rate (TPR)</div>
            <div
              className="metric-value"
              style={{ color: tpr >= 70 ? 'var(--success-color)' : tpr >= 40 ? 'var(--warning-color)' : 'var(--danger-color)' }}
            >
              {tpr}%
            </div>
            <div className="metric-sub">
              {detected_tech} of {total_executed} techniques generated a matching Windows Event ID
            </div>
          </div>

          <div className="metric-box metric-mttd">
            <div className="metric-label">Mean Time to Detect (MTTD)</div>
            <div className="metric-value" style={{ color: 'var(--warning-color)' }}>
              {mttd !== null
                ? `${mttd}s`
                : <span style={{ fontSize: '1.4rem', color: '#8b949e' }}>Awaiting data</span>}
            </div>
            <div className="metric-sub">
              {mttd !== null
                ? 'Avg. seconds from attack trigger to event log appearance'
                : 'Run a playbook first — trigger time is logged to /tmp/bas_attack_log.json'}
            </div>
          </div>
        </div>

        {/* Methodology */}
        <div className="methodology-card">
          <h3 style={{ marginBottom: '14px', fontSize: '1rem', color: '#8b949e', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            How Metrics Are Calculated
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            <div>
              <strong style={{ display: 'block', marginBottom: 6 }}>True Positive Rate</strong>
              <p className="detailText">
                After each playbook runs, the backend queries the Windows Security &amp; PowerShell Operational
                event logs on the victim VM via WinRM. If the expected Event ID (e.g., <code>4688</code> for
                process creation, <code>4698</code> for scheduled task) is found in the last 10 minutes,
                that technique counts as detected. TPR = detected / total x 100.
              </p>
            </div>
            <div>
              <strong style={{ display: 'block', marginBottom: 6 }}>Mean Time to Detect</strong>
              <p className="detailText">
                When you click "Launch" on a playbook, the exact trigger timestamp is written to
                <code> /tmp/bas_attack_log.json</code>. The backend compares that time against
                the TimeCreated field of the matching Windows event.
                MTTD = avg(log_timestamp - trigger_time) in seconds.
              </p>
            </div>
          </div>
        </div>

        {/* Live Evidence */}
        <div style={{ marginTop: '28px' }}>
          <h3 style={{ marginBottom: '4px', display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ color: 'var(--success-color)' }}>&#9679;</span> Live Evidence - Raw Windows Event Logs
          </h3>
          <p className="detailText" style={{ marginBottom: '16px' }}>
            Records fetched directly from the victim VM via WinRM.
            {liveEvents ? ` ${totalRecs} record(s) found across ${queriedCount} technique(s).` : ''}
          </p>

          {records.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', color: '#8b949e', padding: '40px' }}>
              <p style={{ fontSize: '1.1rem', marginBottom: 8 }}>No event records found yet.</p>
              <p className="detailText">
                Run a playbook from the Playbooks tab, then click "Re-check Live Logs" above.
              </p>
            </div>
          ) : (
            <div className="table-wrapper">
              <table className="attack-table log-evidence-table">
                <thead>
                  <tr>
                    <th>Technique</th>
                    <th>Event ID</th>
                    <th>Log Source</th>
                    <th>Timestamp (UTC)</th>
                    <th>Event Name</th>
                    <th>Message Snippet</th>
                    <th>MITRE</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((rec, i) => (
                    <tr key={i}>
                      <td><strong>{rec.technique_id}</strong></td>
                      <td><span className="event-badge" style={{ display: 'inline-block' }}>ID: {rec.event_id}</span></td>
                      <td><span className="detailText" style={{ fontSize: '0.78rem' }}>{rec.log_source}</span></td>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.82rem', whiteSpace: 'nowrap' }}>{rec.timestamp}</td>
                      <td>{rec.event_name}</td>
                      <td>
                        <pre className="output-preview" style={{ maxHeight: '80px', fontSize: '0.75rem' }}>
                          {rec.message}
                        </pre>
                      </td>
                      <td>
                        <a href={rec.mitre_link || '#'} target="_blank" rel="noreferrer" className="mitre-link">
                          ATT&amp;CK
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Per-Technique Detection Summary */}
        {detailEntries.length > 0 && (
          <div style={{ marginTop: '28px' }}>
            <h3 style={{ marginBottom: '16px' }}>Technique Detection Summary</h3>
            <div className="event-list">
              {detailEntries.map(([tech, events]) => (
                <div key={tech} className="event-card">
                  <div className="event-header">
                    <h4>Technique: {tech}</h4>
                    <a
                      href={events[0]?.mitre_link || '#'}
                      target="_blank"
                      rel="noreferrer"
                      className="mitre-link"
                    >
                      View in MITRE ATT&amp;CK
                    </a>
                  </div>
                  {events.map((evt, idx) => (
                    <div key={idx} className="event-detail">
                      <div className="event-badge">Event ID: {evt.event_id}</div>
                      <div className="event-info">
                        <strong>{evt.name}</strong>
                        <p className="detailText">{evt.description}</p>
                        <p className="detailText">
                          <Clock size={12} style={{ display: 'inline' }} /> Last seen: {evt.latest_timestamp}
                        </p>
                        <p className="detailText">Matches found: <strong>{evt.count}</strong></p>
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  // ─────────────────── SLIVER C2 ───────────────────
  const renderC2 = () => {
    if (!c2Data) return <div className="loading">Querying Sliver API...</div>;
    return (
      <div className="view-container">
        <h2 className="view-title"><Server className="icon" /> Sliver C2 Status</h2>
        <div className="grid-2">
          <div className="card">
            <h3>Server Information</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <tbody>
                {[
                  ['Status', c2Data.connected ? <span style={{ color: 'var(--success-color)' }}>● Online</span> : <span style={{ color: 'var(--danger-color)' }}>● Offline</span>],
                  ['Host', `${c2Data.server_host}:${c2Data.server_port}`],
                  ['Total Implants', c2Data.agent_count],
                  ['Active Sessions', c2Data.active_sessions],
                  ['Beacons', c2Data.beacon_sessions],
                ].map(([k, v], i) => (
                  <tr key={i} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '10px 0', color: '#8b949e', width: '40%' }}>{k}</td>
                    <td style={{ padding: '10px 0', fontWeight: 600 }}>{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="card">
            <h3>Active Implants</h3>
            {c2Agents.length === 0 ? (
              <p className="detailText">No active implants detected.</p>
            ) : (
              <div className="table-wrapper">
                <table className="attack-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Hostname</th>
                      <th>OS</th>
                      <th>User</th>
                      <th>Status</th>
                      <th>Last Checkin</th>
                    </tr>
                  </thead>
                  <tbody>
                    {c2Agents.map(ag => (
                      <tr key={ag.id}>
                        <td><strong>{ag.name}</strong></td>
                        <td>{ag.hostname}</td>
                        <td>{ag.os}</td>
                        <td>{ag.username}</td>
                        <td><StatusBadge status={ag.status} /></td>
                        <td className="detailText">{ag.last_checkin}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <Shield size={28} className="brand-icon" />
          <h1>BAS Platform</h1>
        </div>
        <nav className="nav-menu">
          {[
            { id: 'dashboard', icon: <Activity />, label: 'System Overview' },
            { id: 'playbooks', icon: <Play />, label: 'Playbooks' },
            { id: 'evaluation', icon: <Database />, label: 'Purple Team Metrics' },
            { id: 'c2', icon: <Server />, label: 'Sliver C2' },
          ].map(t => (
            <button key={t.id} className={`nav-btn ${activeTab === t.id ? 'active' : ''}`} onClick={() => setActiveTab(t.id)}>
              {t.icon} {t.label}
            </button>
          ))}
        </nav>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="topbar-left">
            <span className="target-badge">Target: 192.168.56.102</span>
          </div>
          <div className="topbar-right">
            <button className="theme-toggle" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
              {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
            </button>
          </div>
        </header>

        <div className="content-area">
          {activeTab === 'dashboard' && renderDashboard()}
          {activeTab === 'playbooks' && renderPlaybooks()}
          {activeTab === 'evaluation' && renderEvaluation()}
          {activeTab === 'c2' && renderC2()}
        </div>
      </main>
    </div>
  );
}

export default App;
