# BAS Platform — Presentation Q&A Guide
## Professor-Level Technical Questions & Model Answers

---

## SECTION 1: Core Concepts

**Q1. What is a Breach and Attack Simulation (BAS) platform and how does it differ from a standard penetration test?**

A BAS platform is an automated system that continuously simulates real adversary techniques against a target environment to measure how well existing defences detect and prevent those attacks. The key differences from a penetration test are:

- **Repeatability**: A BAS platform can run the exact same attack chain daily, weekly, or on-demand. A pen test is a point-in-time assessment.
- **Automation**: No human attacker drives the simulation at runtime; the platform executes pre-defined techniques autonomously.
- **Measurement focus**: BAS produces quantitative metrics — health scores, detection rates, technique success rates — rather than a qualitative writeup.
- **Safety controls**: The platform has a built-in kill switch, health thresholds, and safety levels to prevent accidental damage. A pen test typically has no such automated safety layer.
- **MITRE ATT&CK alignment**: Every technique in this platform is mapped to a specific MITRE ATT&CK technique ID, giving structured, comparable results.

---

**Q2. What is the MITRE ATT&CK framework and why did you use it as the foundation?**

MITRE ATT&CK (Adversarial Tactics, Techniques, and Common Knowledge) is a globally accessible knowledge base of adversary behaviour based on real-world observations. It organises attacks into **Tactics** (the "why" — e.g., Discovery, Lateral Movement) and **Techniques** (the "how" — e.g., T1087 Account Discovery).

Using it provides:

- **Standardised language**: Everyone from blue teams to auditors speaks the same vocabulary.
- **Real-world grounding**: Techniques in ATT&CK are observed in actual APT campaigns, not theoretical scenarios.
- **Coverage measurement**: You can map your detections against the full ATT&CK matrix and identify gaps.
- **Academic credibility**: Published literature on detection engineering universally references ATT&CK.

This platform covers 6 MITRE tactics and 22 techniques, spanning the cyber kill chain from initial Discovery through to Impact.

---

**Q3. Explain the overall architecture of your platform.**

The platform has three layers:

1. **Attacker side (Kali Linux, 192.168.56.101)**: Runs the BAS platform itself — a FastAPI REST API server, the attack executor, telemetry collector, safety engine, and Sliver C2 client.

2. **Communication channels**: Two channels connect attacker to victim:
   - **WinRM/PowerShell Remoting** (port 5985): Used for direct command execution via the `pywinrm` library. Commands are sent as PowerShell scripts and results returned as text.
   - **Sliver C2 channel** (HTTPS, port 8443): A real C2 implant (`bas_beacon.exe`) runs on the victim and communicates back over encrypted HTTPS, mimicking actual APT tradecraft.

3. **Victim side (Windows 11 VM, 192.168.56.102)**: The target machine. It runs PowerShell Remoting, hosts the Sliver beacon, and generates Windows Event Logs as detection artefacts.

The network is isolated on a VirtualBox host-only adapter (192.168.56.0/24) so attacks never leave the lab.

---

## SECTION 2: Safety Engine

**Q4. How does the safety engine work? Why is it important?**

The safety engine (`core/safety_engine.py`) is the platform's circuit breaker. It prevents the simulation from causing real damage. It has four components:

- **Kill Switch**: A software flag that, when triggered, immediately halts all attack execution. Accessible via `POST /api/v1/safety/kill-switch`. Think of it as a physical emergency stop button.
- **Safety Levels**: Four escalating levels — `simulation`, `observation`, `controlled`, `full`.
- **Target Validation**: Only private IP ranges are accepted. The platform refuses to execute against public internet IPs.
- **Health Threshold**: If the victim's health score drops below 30/100, the platform automatically stops all execution.

The importance is ethical and practical: without these controls, a BAS platform could itself become a threat to the system it is testing.

---

**Q5. What are the four safety levels and when would you use each one?**

| Level | Behaviour | Use Case |
|-------|-----------|----------|
| `simulation` | Commands are logged but never executed on the target | Dry-run testing of a new playbook before deployment |
| `observation` | Only telemetry is collected; no attacks run | Establishing a baseline health snapshot |
| `controlled` | Non-destructive, read-only attacks run | Normal BAS testing — used for all reported results |
| `full` | All techniques including destructive ones | Advanced red-team scenarios with explicit authorisation |

The platform defaults to `controlled` in all playbooks.

---

## SECTION 3: Attack Techniques & Playbooks

**Q6. Walk me through the Discovery playbook. What does each technique do and what event logs does it generate?**

The Discovery playbook (`playbooks/discovery_phase.sh`) achieved 100% success (4/4 techniques):

**T1087 — Account Discovery**
Command: `Get-LocalUser | Select-Object Name,Enabled,LastLogon,PasswordLastSet`
Purpose: Lists local user accounts to identify dormant accounts or service accounts to target.
Detection: Windows Event ID **4798** (local group membership enumerated), **4104** (PowerShell script block).
Result: 14.5 seconds. Returned accounts including `Administrator` and `akila`.

**T1057 — Process Discovery**
Command: `Get-Process | Sort-Object CPU -Descending | Select -First 20`
Purpose: Reveals running security tools (Defender = `MsMpEng.exe`, Sysmon = `Sysmon64.exe`).
Detection: Event ID **4688** (process creation), **4104**.
Result: 11.5 seconds. Top process was `MsMpEng` (Windows Defender).

**T1016 — Network Configuration Discovery**
Command: `ipconfig /all`
Purpose: Gets IP, subnet, DNS (often the domain controller), gateway — maps pivot targets.
Detection: Event ID **4104** for the PowerShell session.
Result: 11.3 seconds. Retrieved full adapter info including gateway `192.168.56.1`.

**T1083 — File and Directory Discovery**
Command: `Get-ChildItem -Path 'C:\Users' -Recurse -Depth 2 | Select-Object FullName,Length,LastWriteTime -First 50`
Purpose: Prospects for credential files, configuration files, database dumps.
Detection: High disk I/O is an anomaly signal. Event 4104 captures the command.
Result: 16.8 seconds. Caused health score to drop to **75.07/100** due to disk I/O spike.

---

**Q7. Explain the Credential Access playbook. How does DPAPI work and why is browser credential extraction significant?**

Three techniques, 100% success (3/3):

**T1555.003 — Browser Credential Extraction**
Modern browsers store passwords in a SQLite database (`Login Data` file) encrypted with Windows DPAPI (Data Protection API). DPAPI ties encryption to the logged-in user's Windows credentials — meaning any process running as that user can decrypt it by calling `CryptUnprotectData()`. The significance: an attacker who compromises a standard user account immediately gains access to all that user's saved browser passwords — no privilege escalation required. This was used extensively in the 2020 Emotet campaigns.

**T1552.001 — Credentials in Files**
Searches the filesystem for files with names containing `*password*`, `*cred*`, `*.xml`, `*.config`. Remarkably effective — developers hardcode database credentials into configuration files routinely. The 2021 Twitch breach originated from a hardcoded credential in an internal Git repo.

**T1003.001 — LSASS Memory Enumeration (Safe Mode)**
LSASS holds authentication data — password hashes — for all currently logged-in users. In `controlled` mode, only process metadata is read (PID, memory size) — no memory dump. Detection for real dumping: Event ID **4656** and Sysmon Event ID **10** (process access with VM_READ).

---

**Q8. What is the Adaptive Defense Evasion playbook and what makes it architecturally significant?**

The Defense Evasion playbook (`playbooks/defense_evasion_adaptive.sh`) implements a **primary-fallback pivot mechanism** via `core/adaptive_executor.py`:

```python
def execute_adaptive(primary_id, fallback_id, target_ip):
    result = execute(primary_id, target_ip)
    if result.status in ("failed", "blocked"):
        log(f"[ADAPTIVE] Pivoting to {fallback_id}.")
        return execute(fallback_id, target_ip)
    return result
```

Two technique pairs:

- **T1562.001** (Disable Windows Defender) → if blocked → **T1562.004** (Disable Firewall)
- **T1070.001** (Clear Event Logs) → if blocked → **T1027.002** (Base64 Script Obfuscation)

This mirrors Stuxnet's engineering philosophy: the worm tried four separate propagation vectors because single-vector reliance is fragile. The adaptive executor embodies the same design.

Success was 25% (1/4) — expected and itself a finding: Windows 11 default configuration blocks Defender modification via Tamper Protection and log clearing requires elevation not available to the WinRM session.

---

**Q9. What is the Sliver C2 playbook and why does a real C2 channel matter?**

The Sliver C2 playbook (`playbooks/lateral_movement_sliver.sh`) uses the open-source Sliver C2 framework (BishopFox) to deploy a real implant and issue commands through an encrypted channel.

**Why it matters**: WinRM is an administrative protocol — it is obvious in logs, uses port 5985, and many organisations block it on workstations. Real APT actors use custom implants communicating over HTTPS that blend into normal web traffic.

**Five phases**:

1. **Deploy** (T1570): Transfer `bas_beacon.exe` via SMB (`smbclient`). Same technique Stuxnet used to propagate across network shares.
2. **Detect beacon**: Poll Sliver's gRPC API for up to 60 seconds. Successful check-in confirms the beacon ran and established an HTTPS connection.
3. **C2 commands**: Reconnaissance issued through the encrypted C2 channel, not plaintext WinRM.
4. **Lateral movement**: SMB share access (T1021.002), RDP status (T1021.001), file transfer (T1570).
5. **API logging**: All results logged to the BAS API.

From a defender's perspective, phases 3-4 look like HTTPS traffic to an IP address — fundamentally harder to detect.

---

**Q10. Why did the Persistence playbook fail (0/2), and what does that tell you?**

The Persistence playbook failed due to a credential authentication mismatch when the WinRM session attempted to create a scheduled task (T1053.005).

What it tells us:

1. **Honest results**: The platform reports real failures accurately — no fake success.
2. **The technique is sound**: Creating scheduled tasks with admin credentials absolutely works; this is documented in every APT41 report. The failure was an implementation bug.
3. **Windows 11 hardening works**: Even in a lab, creating scheduled tasks via WinRM requires explicit admin-level credentials — the OS default hardening has real defensive value.
4. **Failure modes are findings**: 0% persistence success in the default configuration is a useful data point for defenders — Windows 11 defaults provide meaningful resistance.

---

## SECTION 4: Telemetry & Health Scoring

**Q11. How is the health score calculated?**

The health score (0–100) is computed by `telemetry/collector.py` from real-time metrics via WinRM:

- **CPU usage**: High consumption from resource-heavy attacks reduces the score.
- **Memory usage**: Elevated memory pressure decreases the score.
- **Disk I/O**: Abnormally high activity (e.g., recursive file scans) contributes negatively.
- **Network connections**: Unexpected outbound connections trigger anomalies.
- **Process count**: Sudden spikes indicate possible payload execution.

In testing, the Discovery playbook brought health from ~100 to **75.07** (disk I/O from T1083). Privilege Escalation drove it to **53.69**. If health drops below **30**, the kill switch triggers automatically.

---

**Q12. What Windows Event IDs are most important for detecting your platform's attacks?**

| Event ID | Source | Detects |
|----------|--------|---------|
| 4104 | PowerShell | Script block logging — captures every PowerShell command verbatim |
| 4688 | Security | Process creation with command-line arguments |
| 4798 | Security | Local user/group enumeration (T1087) |
| 4656 | Security | Handle to LSASS with VM_READ (T1003.001) |
| 4663 | Security | File access — Login Data (T1555.003) |
| 4698 | Security | Scheduled task creation (T1053.005) |
| 5140 | Security | Network share access (T1021.002 — SMB) |
| 5001 | Defender | Windows Defender real-time protection disabled |
| 10 (Sysmon) | Sysmon | Process access — catches LSASS handle requests |
| 11 (Sysmon) | Sysmon | File created — catches beacon binary written to disk |

---

## SECTION 5: Technical Implementation

**Q13. Why did you choose FastAPI over Flask or Django?**

Three reasons:

1. **Async support**: FastAPI is built on `asyncio`. The telemetry collector runs continuously in the background while the API handles attack requests simultaneously. Flask is synchronous and would block during long-running WinRM commands.
2. **Automatic Swagger UI**: FastAPI generates interactive API documentation at `/docs` from Python type annotations alone — invaluable for demonstrating API functionality.
3. **Pydantic validation**: All request/response bodies are validated before reaching the attack executor, preventing malformed inputs from causing undefined behaviour.

---

**Q14. How does WinRM work and why did you use it instead of SSH?**

WinRM (Windows Remote Management) is Microsoft's implementation of WS-Management. It allows remote PowerShell command execution over HTTP (port 5985).

```python
session = winrm.Session('http://192.168.56.102:5985/wsman',
                        auth=('akila', '12345678'), transport='ntlm')
result = session.run_ps('Get-LocalUser')
```

SSH was not used because:

- WinRM is the native Windows remote management protocol — OpenSSH is not enabled by default.
- Most enterprise Windows environments use WinRM for management.
- NTLM authentication more accurately reflects how lateral movement happens in Windows environments.
- Detection artefacts (Event IDs) for WinRM are documented and expected by defenders.

---

**Q15. Explain the data flow from attack trigger to result storage.**

When `POST /api/v1/attacks/execute` is called:

1. FastAPI validates the request with Pydantic.
2. Safety Engine checks: kill switch, target IP whitelist, safety level vs. technique severity.
3. Attack Executor retrieves the technique from the registry.
4. **Pre-attack telemetry snapshot** taken.
5. **PowerShell command executed** on victim via WinRM. stdout/stderr captured.
6. **Cleanup command** executed if defined.
7. **Post-attack telemetry snapshot** taken.
8. **Health impact calculated**: post_health − pre_health.
9. **Result stored in SQLite**: attack_id (UUID), technique_id, status, output, health_impact, duration.
10. API returns JSON with attack_id for retrieval via `GET /api/v1/attacks/results/{id}`.

Round-trip for T1087: approximately **14–16 seconds** (dominated by WinRM execution time).

---

## SECTION 6: Stuxnet Mapping

**Q16. How does your platform relate to Stuxnet?**

Stuxnet (2010) is the most sophisticated documented cyberweapon — a nation-state worm targeting Iranian uranium enrichment centrifuges. Several playbook techniques map directly:

| Stuxnet Stage | Platform Technique |
|---------------|-------------------|
| Environment reconnaissance | Discovery Phase (T1087, T1057, T1016, T1083) |
| Propagation via network shares | T1021.002 — SMB; T1570 — Lateral Tool Transfer |
| Defense evasion: hiding files | T1562.001 — Disable Defender; T1070.001 — Clear Logs |
| Credential theft for propagation | T1555.003, T1552.001, T1003.001 |
| Persistence after reboot | T1053.005 — Scheduled Task |
| Adaptive multi-vector propagation | The adaptive executor (primary-fallback pivot logic) |
| C2 command-and-control | Sliver C2 playbook (T1071.001) |

The adaptive executor specifically mirrors Stuxnet's engineering philosophy: the worm tried four propagation vectors because single-vector reliance is fragile.

---

**Q17. What is DPAPI and what are its security limitations?**

DPAPI (Data Protection API) is a Windows built-in symmetric encryption service that ties keys to a user's login credentials. `CryptProtectData()` encrypts with a key derived from the user's Windows password and SID. `CryptUnprotectData()` decrypts — for any process running **as that user**.

The fundamental limitation: *no special privileges are required*. An attacker who compromises a standard user account can decrypt all of that user's browser-saved passwords. The operation appears as legitimate API usage to most security tools.

Mitigations: Windows Credential Guard can protect some credentials, but browser credentials remain vulnerable. MFA limits the *use* of stolen credentials even after extraction.

---

## SECTION 7: Limitations & Results

**Q18. What are the main limitations of your platform?**

1. **Single-target architecture**: One victim VM at a time. Enterprise BAS tools support multi-target campaigns.
2. **WinRM dependency**: Implies the attacker already has credentials — the initial access phase is skipped.
3. **DPAPI limitation**: Full decryption requires actually saved passwords in the browser. Lab VM had only one entry.
4. **Persistence failures**: Implementation bug in credential handling, not a fundamental technique limitation.
5. **No machine learning**: The adaptive executor uses predefined pairs. A true adaptive system would use reinforcement learning.
6. **No cloud support**: Designed for on-premise Windows. Cloud workloads require different attack connectors.

---

**Q19. What is the overall attack success rate and what does it mean?**

Overall: **14/19 techniques = 73.7% success rate**

| Playbook | Success |
|----------|---------|
| Discovery | 4/4 = **100%** |
| Credential Access | 3/3 = **100%** |
| Privilege Escalation | 3/3 = **100%** |
| Defense Evasion | 1/4 = **25%** — blocked by Tamper Protection |
| Lateral Movement | 1/3 = **33%** — SMB succeeded; RDP/file transfer failed |
| Persistence | 0/2 = **0%** — credential handling bug |

**Interpretation**: Read-only reconnaissance is essentially unconstrained; destructive/write-based techniques face meaningful Windows 11 resistance. This directly validates that Windows 11 default hardening provides real improvement — itself a research finding.

---

## SECTION 8: Rapid-Fire Q&A

**Q20. What port does WinRM use?** HTTP: **5985**. HTTPS: **5986**.

**Q21. What Python library is used for WinRM?** `pywinrm` — with NTLM authentication transport.

**Q22. What database does the platform use?** **SQLite** — in `data/` directory. No server required; sufficient for lab scale.

**Q23. What is the lab network subnet?** `192.168.56.0/24` — VirtualBox host-only. Attacker: `.101`, Victim: `.102`.

**Q24. What is Sliver?** An open-source C2 framework by BishopFox. Generates implants (beacons) communicating over HTTPS with a gRPC API server.

**Q25. What does a health score of 75.07 after Discovery tell you?** The Discovery phase — despite being read-only — reduced victim health by ~25 points, primarily due to T1083's disk I/O spike. This demonstrates that even reconnaissance is measurably detectable through resource impact, not just log analysis.

**Q26. What is AMSI?** Anti-Malware Scan Interface — a Windows API letting antivirus engines intercept and scan script content before execution. T1027.002 (Base64 obfuscation) attempts to evade AMSI signature matching.

**Q27. Difference between T1021.001 and T1021.002?** T1021.001 = **RDP** (Remote Desktop, port 3389 — full GUI access). T1021.002 = **SMB/Admin Shares** (accessing `C$`, `ADMIN$` for file operations and remote execution).

**Q28. Why host-only network?** Ensures attack traffic never reaches the real internet or production systems — fundamental ethical constraint for lab BAS.

**Q29. Kill switch endpoint?** `POST /api/v1/safety/kill-switch`. Reset: `DELETE /api/v1/safety/kill-switch`.

**Q30. How would you extend this to production-grade?** Add ML-based attack path selection, multi-target support, SIEM integration for real detection-rate measurement, cloud connectors (Azure/AWS), and continuous scheduled operation mode.

---

*Remember: the failures are as important as the successes — they show that Windows 11 default hardening works.*
