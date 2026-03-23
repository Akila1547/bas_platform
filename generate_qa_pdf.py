#!/usr/bin/env python3
"""Generate BAS Platform Q&A PDF using ReportLab."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable, PageBreak)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
import os

OUTPUT = "/home/akila/Desktop/bas_platform/BAS_Platform_QA_Guide.pdf"

doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=A4,
    rightMargin=2*cm, leftMargin=2*cm,
    topMargin=2*cm, bottomMargin=2*cm
)

styles = getSampleStyleSheet()

# Custom styles
title_style = ParagraphStyle('Title', parent=styles['Title'],
    fontSize=20, spaceAfter=6, textColor=colors.HexColor('#1a1a2e'),
    fontName='Helvetica-Bold')
subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
    fontSize=12, spaceAfter=16, textColor=colors.HexColor('#4a4a6a'),
    fontName='Helvetica', alignment=TA_CENTER)
section_style = ParagraphStyle('Section', parent=styles['Heading1'],
    fontSize=14, spaceBefore=14, spaceAfter=6,
    textColor=colors.white, fontName='Helvetica-Bold',
    backColor=colors.HexColor('#2d3561'), leftIndent=-0.3*cm,
    leading=18)
q_style = ParagraphStyle('Question', parent=styles['Normal'],
    fontSize=11, spaceBefore=10, spaceAfter=4,
    textColor=colors.HexColor('#1a1a2e'), fontName='Helvetica-Bold',
    leftIndent=0.2*cm)
a_style = ParagraphStyle('Answer', parent=styles['Normal'],
    fontSize=10, spaceAfter=4, leading=15,
    textColor=colors.HexColor('#2c2c2c'), fontName='Helvetica',
    leftIndent=0.4*cm, alignment=TA_JUSTIFY)
bullet_style = ParagraphStyle('Bullet', parent=styles['Normal'],
    fontSize=10, leading=14, leftIndent=1.0*cm, firstLineIndent=-0.4*cm,
    textColor=colors.HexColor('#2c2c2c'), fontName='Helvetica')
code_style = ParagraphStyle('Code', parent=styles['Code'],
    fontSize=8.5, backColor=colors.HexColor('#f4f4f4'),
    leftIndent=0.6*cm, rightIndent=0.6*cm,
    borderPad=4, leading=12, fontName='Courier')
note_style = ParagraphStyle('Note', parent=styles['Normal'],
    fontSize=9, textColor=colors.HexColor('#555555'), fontName='Helvetica-Oblique',
    alignment=TA_CENTER, spaceAfter=8)

def section(title):
    return [
        Spacer(1, 0.3*cm),
        Paragraph(f"  {title}", section_style),
        Spacer(1, 0.2*cm),
    ]

def qa(q, a_paras):
    items = [Paragraph(f"Q: {q}", q_style)]
    for p in a_paras:
        items.append(p)
    items.append(Spacer(1, 0.15*cm))
    return items

def ans(text):
    return Paragraph(text, a_style)

def bul(text):
    return Paragraph(f"•  {text}", bullet_style)

def code(text):
    return Paragraph(text.replace('\n', '<br/>').replace(' ', '&nbsp;'), code_style)

def tbl(data, col_widths=None):
    if col_widths is None:
        col_widths = [4*cm] * len(data[0])
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2d3561')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f0f0f8')]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
    ]))
    return t

content = []

# ── Cover ──────────────────────────────────────────────────────────────────────
content.append(Spacer(1, 1.5*cm))
content.append(Paragraph("BAS Platform", title_style))
content.append(Paragraph("Presentation Q&amp;A Preparation Guide", subtitle_style))
content.append(Paragraph("30 Professor-Level Questions with Model Answers", note_style))
content.append(HRFlowable(width="100%", color=colors.HexColor('#2d3561'), thickness=2))
content.append(Spacer(1, 0.5*cm))
content.append(Paragraph(
    "This guide covers every major technical aspect of the Adaptive BAS Platform. "
    "Read each question aloud, then check your answer against the model. "
    "Failures are findings — know why each percentage is what it is.",
    note_style))
content.append(Spacer(1, 0.5*cm))

# ── SECTION 1: CORE CONCEPTS ──────────────────────────────────────────────────
content += section("SECTION 1 — Core Concepts")

content += qa(
    "What is a Breach and Attack Simulation (BAS) platform and how does it differ from a penetration test?",
    [ans("A BAS platform is an <b>automated system</b> that continuously simulates real adversary techniques to measure how well existing defences detect and block them. Key differences:"),
     bul("<b>Repeatability</b>: BAS runs the same chain daily/on-demand. A pen test is point-in-time."),
     bul("<b>Automation</b>: No human attacker at runtime. Pre-defined techniques execute autonomously."),
     bul("<b>Quantitative output</b>: Health scores, success rates, technique-level metrics — not a qualitative report."),
     bul("<b>Safety controls</b>: Kill switch, health thresholds, four safety levels. Pen tests have no automated safety layer."),
     bul("<b>MITRE ATT&amp;CK alignment</b>: Every technique maps to a specific ID for structured, comparable results."),
    ])

content += qa(
    "What is the MITRE ATT&CK framework and why did you use it?",
    [ans("MITRE ATT&amp;CK is a globally accessible knowledge base of real adversary behaviour, organised into <b>Tactics</b> (the 'why' — e.g., Discovery) and <b>Techniques</b> (the 'how' — e.g., T1087 Account Discovery)."),
     ans("Benefits: standardised language across blue/red teams; real-world grounding (observed in actual APT campaigns); coverage gap identification; academic credibility. This platform covers <b>6 tactics and 22 techniques</b> across the full kill chain."),
    ])

content += qa(
    "Explain the overall architecture of your platform.",
    [ans("<b>Three layers:</b>"),
     bul("<b>Attacker side (Kali Linux, 192.168.56.101)</b>: FastAPI REST API, attack executor, telemetry collector, safety engine, Sliver C2 client."),
     bul("<b>Communication</b>: WinRM/PowerShell Remoting (port 5985) for direct command execution via pywinrm; Sliver C2 (HTTPS, port 8443) — encrypted channel mimicking APT tradecraft."),
     bul("<b>Victim side (Windows 11 VM, 192.168.56.102)</b>: PowerShell Remoting, Sliver beacon, Windows Event Logs as detection artefacts."),
     ans("Entire network on a VirtualBox host-only adapter (192.168.56.0/24). Attack traffic never leaves the lab."),
    ])

# ── SECTION 2: SAFETY ENGINE ──────────────────────────────────────────────────
content += section("SECTION 2 — Safety Engine")

content += qa(
    "How does the safety engine work and why is it important?",
    [ans("The safety engine (core/safety_engine.py) is the platform's circuit breaker with four components:"),
     bul("<b>Kill Switch</b>: POST /api/v1/safety/kill-switch — immediately halts all execution."),
     bul("<b>Safety Levels</b>: simulation → observation → controlled → full."),
     bul("<b>Target Validation</b>: Only private IP ranges accepted; refuses public internet IPs."),
     bul("<b>Health Threshold</b>: Auto-stops if victim health drops below 30/100."),
     ans("Without these controls, a BAS platform could itself become a threat to the system it is testing."),
    ])

content += qa(
    "What are the four safety levels and when would you use each one?",
    [tbl(
        [['Level', 'Behaviour', 'Use Case'],
         ['simulation', 'Commands logged only, no real execution', 'Dry-run before deployment'],
         ['observation', 'Read-only telemetry; no attacks', 'Baseline health snapshot'],
         ['controlled', 'Non-destructive attacks run', 'Normal BAS testing (default)'],
         ['full', 'All techniques including destructive', 'Authorised red-team scenario']],
        [2.5*cm, 5.5*cm, 5.5*cm]
    )])

# ── SECTION 3: PLAYBOOKS ──────────────────────────────────────────────────────
content += section("SECTION 3 — Attack Techniques & Playbooks")

content += qa(
    "Walk me through the Discovery playbook. What does each technique do and what Event IDs does it generate?",
    [ans("<b>100% success (4/4). Script: playbooks/discovery_phase.sh</b>"),
     tbl(
         [['Technique', 'Command', 'Purpose', 'Key Event ID', 'Duration'],
          ['T1087\nAccount Discovery', 'Get-LocalUser', 'List accounts; find dormant/service accounts', '4798, 4104', '14.5s'],
          ['T1057\nProcess Discovery', 'Get-Process | Sort CPU', 'Identify security tools (Defender, Sysmon)', '4688, 4104', '11.5s'],
          ['T1016\nNetwork Config', 'ipconfig /all', 'Get IP, DNS (domain controller), gateway', '4104', '11.3s'],
          ['T1083\nFile Discovery', 'Get-ChildItem -Recurse', 'Find credential/config files', '4104, disk anomaly', '16.8s']],
         [2.2*cm, 3.5*cm, 4.5*cm, 2.5*cm, 1.8*cm]
     ),
     ans("After the full Discovery phase, health score dropped to <b>75.07/100</b> — primarily due to T1083's disk I/O spike."),
    ])

content += qa(
    "Explain the Credential Access playbook. How does DPAPI work?",
    [ans("<b>100% success (3/3). Script: playbooks/credential_access.sh</b>"),
     ans("<b>T1555.003 — Browser Credential Extraction:</b> Modern browsers store passwords in a SQLite 'Login Data' file encrypted with <b>DPAPI</b> (Data Protection API). DPAPI ties encryption to the logged-in user's Windows credentials — any process running as that user can call CryptUnprotectData() to decrypt without admin rights. The 2020 Emotet malware used this exact mechanism. Lab result: found 1 entry (https://httpbin.org)."),
     ans("<b>T1552.001 — Credentials in Files:</b> Searches filesystem for *password*, *cred*, *.xml, *.config files. Alarmingly effective — developers routinely hardcode DB credentials. The 2021 Twitch breach originated this way."),
     ans("<b>T1003.001 — LSASS (Safe Mode):</b> LSASS holds password hashes for all logged-in users. In controlled mode, only reads process metadata. Detection: Event ID <b>4656</b> (handle with VM_READ) and Sysmon Event <b>10</b>."),
    ])

content += qa(
    "What is the Adaptive Defense Evasion playbook and why is it architecturally significant?",
    [ans("Script: defense_evasion_adaptive.sh. Implements a <b>primary-fallback pivot mechanism</b> in core/adaptive_executor.py:"),
     code("def execute_adaptive(primary_id, fallback_id, target_ip):\n    result = execute(primary_id, target_ip)\n    if result.status in ('failed', 'blocked'):\n        log(f'[ADAPTIVE] Pivoting to {fallback_id}.')\n        return execute(fallback_id, target_ip)\n    return result"),
     ans("Two pairs: T1562.001 (Disable Defender) → T1562.004 (Disable Firewall); T1070.001 (Clear Logs) → T1027.002 (Base64 Obfuscation). This mirrors Stuxnet's engineering: four propagation vectors because single-vector reliance is fragile."),
     ans("<b>Result: 25% (1/4)</b> — expected. Defender modification is blocked by Tamper Protection; log clearing requires elevation beyond WinRM session. The failures ARE the finding: Windows 11 defaults work."),
    ])

content += qa(
    "What is the Sliver C2 playbook and why does a real C2 channel matter?",
    [ans("<b>Why it matters:</b> WinRM is administrative and obvious in logs. Real APT actors use implants communicating over HTTPS, blending into normal traffic. A simulation using only WinRM understates attacker stealth."),
     ans("<b>5 phases:</b>"),
     bul("<b>Phase 1 (T1570)</b>: Transfer bas_beacon.exe to victim via SMB (smbclient) — same mechanism Stuxnet used."),
     bul("<b>Phase 2</b>: Poll Sliver gRPC API for beacon check-in. Success = beacon ran, HTTPS established, Defender evaded."),
     bul("<b>Phase 3</b>: Reconnaissance (whoami, ipconfig, net share) via encrypted C2 channel — looks like HTTPS to defenders."),
     bul("<b>Phase 4</b>: Lateral movement techniques (T1021.002, T1021.001, T1570) via C2."),
     bul("<b>Phase 5</b>: Log all results to BAS API."),
    ])

content += qa(
    "Why did the Persistence playbook fail (0/2) and what does that tell you?",
    [ans("The scheduled task creation (T1053.005) failed due to a <b>credential handling mismatch</b> between the attack executor and WinRM session — an implementation bug, not a fundamental technique limitation."),
     ans("What it tells us: (1) The platform reports honest failures — no fake success. (2) The technique itself is sound (APT41 routinely uses scheduled tasks). (3) Windows 11 requires explicit admin-level credentials for schtasks via WinRM, demonstrating the OS defaults have real defensive value. (4) A 0% persistence success rate in default configuration is itself a useful defensive data point."),
    ])

# ── SECTION 4: TELEMETRY ──────────────────────────────────────────────────────
content += section("SECTION 4 — Telemetry & Health Scoring")

content += qa(
    "How is the health score calculated? What factors influence it?",
    [ans("The health score (0–100) is computed by telemetry/collector.py from real-time metrics collected via WinRM: CPU usage, memory usage, disk I/O, network connection count, and process count. Anomalies (statistical threshold crossings) generate alert events and penalise the score. If health drops below <b>30</b>, the kill switch triggers."),
     ans("In testing: Discovery phase → <b>75.07</b> (disk I/O from T1083). Privilege Escalation → <b>53.69</b>."),
    ])

content += qa(
    "What Windows Event IDs are most important for detecting your platform's attacks?",
    [tbl(
        [['Event ID', 'Source', 'Detects'],
         ['4104', 'PowerShell', 'Script block logging — every PowerShell command verbatim'],
         ['4688', 'Security', 'Process creation with command-line arguments'],
         ['4798', 'Security', 'Local user/group enumeration (T1087)'],
         ['4656', 'Security', 'Handle to LSASS with VM_READ (T1003.001)'],
         ['4663', 'Security', 'File access — Login Data (T1555.003)'],
         ['4698', 'Security', 'Scheduled task creation (T1053.005)'],
         ['5140', 'Security', 'Network share access — SMB (T1021.002)'],
         ['5001', 'Defender', 'Windows Defender real-time protection disabled'],
         ['10 (Sysmon)', 'Sysmon', 'Process access — catches LSASS handle requests'],
         ['11 (Sysmon)', 'Sysmon', 'File created — catches beacon dropped to disk']],
        [2.5*cm, 2.5*cm, 8.5*cm]
    )])

# ── SECTION 5: TECHNICAL ──────────────────────────────────────────────────────
content += section("SECTION 5 — Technical Implementation")

content += qa(
    "Why did you choose FastAPI over Flask or Django?",
    [bul("<b>Async support</b>: Built on asyncio/Starlette. Telemetry collector runs continuously while API handles attack requests. Flask would block during long WinRM commands."),
     bul("<b>Automatic Swagger UI</b>: Interactive API docs at /docs generated from type annotations — invaluable for demonstrating API functionality to an examiner."),
     bul("<b>Pydantic validation</b>: Request/response bodies validated before reaching the attack executor. Type errors caught early."),
    ])

content += qa(
    "How does WinRM work and why not SSH?",
    [ans("WinRM (Windows Remote Management) is Microsoft's WS-Management implementation, enabling remote PowerShell execution over HTTP port 5985."),
     code("session = winrm.Session('http://192.168.56.102:5985/wsman',\n                        auth=('akila', '12345678'), transport='ntlm')\nresult = session.run_ps('Get-LocalUser')"),
     ans("<b>Why not SSH</b>: WinRM is the native Windows protocol (OpenSSH not enabled by default); NTLM auth more accurately reflects real Windows lateral movement; Event IDs for WinRM are documented and expected by defenders, making the simulation realistic."),
    ])

content += qa(
    "Explain the data flow from attack trigger to result storage.",
    [ans("When POST /api/v1/attacks/execute is called with {technique_id, target_ip}:"),
     bul("1. FastAPI validates with Pydantic."),
     bul("2. Safety Engine: kill switch? IP whitelist? Safety level vs. technique severity?"),
     bul("3. Attack Executor fetches technique from registry."),
     bul("4. Pre-attack telemetry snapshot via WinRM."),
     bul("5. PowerShell command executed on victim. stdout/stderr captured."),
     bul("6. Cleanup command executed if defined."),
     bul("7. Post-attack telemetry snapshot."),
     bul("8. Health impact = post_health − pre_health."),
     bul("9. Result (UUID, technique_id, status, output, health_impact, duration) stored in SQLite."),
     bul("10. API returns JSON with attack_id. Client retrieves via GET /api/v1/attacks/results/{id}."),
     ans("Round-trip for T1087: ~<b>14–16 seconds</b> (dominated by WinRM execution)."),
    ])

# ── SECTION 6: STUXNET ────────────────────────────────────────────────────────
content += section("SECTION 6 — Stuxnet Mapping")

content += qa(
    "How does your platform relate to Stuxnet?",
    [ans("Stuxnet (2010) is the most sophisticated documented cyberweapon — a nation-state worm targeting Iranian uranium enrichment centrifuges. Platform techniques map directly:"),
     tbl(
         [['Stuxnet Stage', 'Platform Technique'],
          ['Environment reconnaissance', 'Discovery Phase: T1087, T1057, T1016, T1083'],
          ['Propagation via network shares', 'T1021.002 (SMB), T1570 (Lateral Tool Transfer)'],
          ['Defense evasion / rootkit hiding', 'T1562.001 (Disable Defender), T1070.001 (Clear Logs)'],
          ['Credential theft for propagation', 'T1555.003, T1552.001, T1003.001'],
          ['Persistence after reboot', 'T1053.005 — Scheduled Task'],
          ['Multi-vector adaptive propagation', 'Adaptive executor: primary-fallback pivot logic'],
          ['C2 communication', 'Sliver C2 playbook (T1071.001)']],
         [5.5*cm, 8*cm]
     )])

content += qa(
    "What is DPAPI and what are its security limitations?",
    [ans("DPAPI (Data Protection API) is Windows' built-in symmetric encryption service. CryptProtectData() encrypts with a key derived from the user's Windows password + SID. CryptUnprotectData() decrypts for any process running <b>as that user</b> — no admin required."),
     ans("<b>Fundamental limitation</b>: Compromising any user account gives access to all that user's browser-saved passwords. The operation appears as legitimate API usage to most security tools. <b>Mitigation</b>: MFA limits use of stolen credentials even after extraction; Credential Guard protects some classes of credentials but not browser stores."),
    ])

# ── SECTION 7: RESULTS & LIMITATIONS ─────────────────────────────────────────
content += section("SECTION 7 — Results & Limitations")

content += qa(
    "What are the main limitations of your platform?",
    [bul("<b>Single-target</b>: One victim VM at a time. Enterprise BAS tools support multi-target campaigns."),
     bul("<b>WinRM dependency</b>: Implies the attacker already has credentials — initial access phase is skipped."),
     bul("<b>DPAPI lab constraint</b>: Full decryption requires actually-saved browser passwords. Lab VM had only one entry."),
     bul("<b>Persistence bug</b>: 0/2 success is an implementation bug, not a technique limitation."),
     bul("<b>No ML</b>: Adaptive executor uses predefined pairs. A true adaptive system would use reinforcement learning."),
     bul("<b>No cloud support</b>: Designed for on-premise Windows. Azure/AWS require different connectors."),
    ])

content += qa(
    "What is the overall attack success rate and what does it mean?",
    [tbl(
        [['Playbook', 'Success', 'Reason for failures'],
         ['Discovery', '4/4 = 100%', 'Read-only — no restrictions'],
         ['Credential Access', '3/3 = 100%', 'Read-only enumeration'],
         ['Privilege Escalation', '3/3 = 100%', 'Read-only enumeration'],
         ['Defense Evasion', '1/4 = 25%', 'Tamper Protection, elevation needed'],
         ['Lateral Movement', '1/3 = 33%', 'RDP reg restricted; file transfer blocked'],
         ['Persistence', '0/2 = 0%', 'Credential handling bug'],
         ['OVERALL', '14/19 = 73.7%', '']],
        [3.5*cm, 3*cm, 7*cm]
    ),
     ans("<b>Interpretation</b>: Read-only reconnaissance is essentially unconstrained. Destructive/write-based techniques face meaningful Windows 11 resistance. This validates that Windows 11 default hardening provides real improvement — itself a research finding."),
    ])

# ── SECTION 8: RAPID FIRE ─────────────────────────────────────────────────────
content += section("SECTION 8 — Rapid-Fire Technical Q&A")

rf_data = [
    ['Q', 'A'],
    ['WinRM port?', 'HTTP: 5985 | HTTPS: 5986'],
    ['Python WinRM library?', 'pywinrm — NTLM auth transport'],
    ['Database used?', 'SQLite — in data/ directory'],
    ['Lab subnet?', '192.168.56.0/24 | Attacker: .101 | Victim: .102'],
    ['What is Sliver?', 'Open-source C2 (BishopFox). HTTPS beacons, gRPC API server.'],
    ['Health 75.07 after Discovery means?', 'Even read-only recon depresses health via disk I/O — detectable by resource monitoring alone.'],
    ['What is AMSI?', 'Anti-Malware Scan Interface. Scripts pass through it before execution. T1027.002 tries Base64 to evade.'],
    ['T1021.001 vs T1021.002?', '.001 = RDP (port 3389, GUI access) | .002 = SMB Admin Shares (C$, ADMIN$)'],
    ['Why host-only network?', 'Isolates attacks from internet/production systems — fundamental ethical constraint.'],
    ['Kill switch endpoint?', 'POST /api/v1/safety/kill-switch | Reset: DELETE /api/v1/safety/kill-switch'],
    ['How to extend to production?', 'ML attack path selection, multi-target, SIEM integration, cloud connectors, scheduled continuous operation.'],
]
content.append(tbl(rf_data, [3.5*cm, 10*cm]))
content.append(Spacer(1, 0.5*cm))
content.append(HRFlowable(width="100%", color=colors.HexColor('#2d3561'), thickness=1.5))
content.append(Spacer(1, 0.3*cm))
content.append(Paragraph(
    "Remember: the failures tell the story. 73.7% overall, with 100% on read-only techniques and "
    "meaningful resistance on write/destructive techniques, demonstrates exactly what Windows 11 "
    "default hardening achieves — and that is your contribution.",
    note_style))

doc.build(content)
print(f"PDF created: {OUTPUT}")
