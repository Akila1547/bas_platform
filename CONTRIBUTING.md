# Contributing to BAS Platform

Thank you for your interest in contributing! This project welcomes improvements from the security research community.

---

## 🚨 Ethical Requirement

By contributing, you confirm that your changes will only be used for:
- Authorized security testing in isolated lab environments
- Academic or professional cybersecurity research
- Improving defensive capabilities

---

## Ways to Contribute

| Type | Examples |
|------|---------|
| 🎭 New Playbooks | New attack scenarios mapped to MITRE ATT&CK |
| ⚔️ New Techniques | Add techniques to `core/attack_executor.py` |
| 📡 Telemetry | Improve metric collection or event parsing |
| 🖥️ Web UI | Dashboard improvements (React/Vite in `web-ui/`) |
| 🐛 Bug Fixes | Fix issues in any module |
| 📚 Documentation | Improve README, SETUP_GUIDE, or inline docs |

---

## Getting Started

1. **Fork** the repo on GitHub
2. **Clone** your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/bas_platform.git
   cd bas_platform
   sudo bash setup.sh
   cp .env.example .env
   # Edit .env with your lab settings
   ```
3. **Create a branch:**
   ```bash
   git checkout -b feature/my-new-playbook
   ```
4. **Make your changes**, then test:
   ```bash
   source venv/bin/activate
   pytest test_setup.py -v
   ```
5. **Commit with a clear message:**
   ```bash
   git commit -m "feat(playbooks): add T1055 process injection playbook"
   ```
6. **Open a Pull Request** against `main`

---

## Adding a New Attack Technique

Edit `core/attack_executor.py` → `_register_builtin_techniques()`:

```python
self.register_technique(AttackTechnique(
    technique_id="T1XXX",
    name="Your Technique Name",
    description="What it does and how",
    severity=AttackSeverity.LOW,       # LOW / MEDIUM / HIGH / CRITICAL
    tactic="Discovery",                 # MITRE tactic
    command_template="Get-Command ...", # PowerShell command
    requires_admin=False,
    expected_duration=10,
    is_destructive=False,
    cleanup_command="# cleanup here",
    expected_artifacts=["event_id_XXXX"],
    detection_rules=["rule_name"]
))
```

## Adding a New Playbook

Create `playbooks/your_scenario.sh` following the pattern from `discovery_phase.sh`:

```bash
#!/bin/bash
# Description: What this playbook tests
# MITRE Techniques: T1XXX, T1YYY
TARGET_IP="${1:-192.168.56.102}"
API_BASE="http://localhost:8000/api/v1"

# Start telemetry
curl -s -X POST "$API_BASE/telemetry/start/$TARGET_IP?interval=5"

# Execute technique
curl -s -X POST "$API_BASE/attacks/execute" \
  -H "Content-Type: application/json" \
  -d "{\"technique_id\": \"T1XXX\", \"target_ip\": \"$TARGET_IP\"}"
```

---

## Commit Message Convention

Use conventional commits for clarity:

```
feat(playbooks): add ransomware detection playbook
fix(api): handle WinRM timeout gracefully
docs(readme): update quick start steps
refactor(core): simplify safety engine validation
```

---

## Pull Request Checklist

- [ ] Tested in an isolated lab environment
- [ ] Added/updated docstrings where relevant
- [ ] No real credentials, IPs, or secrets in the code
- [ ] Playbooks follow existing structure and call the BAS API
- [ ] MITRE ATT&CK technique IDs are correct
