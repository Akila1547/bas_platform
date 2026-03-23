# Contributing to BAS Platform

Thank you for your interest in contributing! This is an open-source security research tool and contributions are welcome.

## What You Can Contribute

- 🆕 **New attack techniques** — add MITRE ATT&CK techniques to `core/attack_executor.py`
- 📋 **New playbooks** — add scenario-based attack chains to `playbooks/`
- 🐛 **Bug fixes** — fix issues in the API, telemetry, or C2 integration
- 📖 **Documentation** — improve `README.md`, `SETUP_GUIDE.md`, or add examples
- 🖥️ **Web UI improvements** — enhance the React dashboard in `web-ui/src/`
- 🔒 **Safety improvements** — strengthen the safety engine

## How to Contribute

1. **Fork** the repository on GitHub
2. **Clone** your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/bas_platform.git
   ```
3. **Create a branch** for your change:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Make your changes** and test them in a lab environment
5. **Commit** with a clear message:
   ```bash
   git commit -m "Add T1XXX: Technique Name playbook"
   ```
6. **Push** and open a **Pull Request** against `main`

## Code Style

- Python: follow PEP 8, use type hints where practical
- Shell scripts: use `set -e`, add comments for each phase
- New techniques must be mapped to a valid MITRE ATT&CK ID

## Lab Environment Required

All contributions involving attack techniques **must be tested in an isolated lab** (VirtualBox Host-Only network). See [SETUP_GUIDE.md](SETUP_GUIDE.md).

## Ethical Guidelines

By contributing, you confirm that your contributions comply with the [ethical use notice in the LICENSE](LICENSE) and will only be used on systems with explicit authorization.

## Opening Issues

- Use GitHub Issues for bug reports and feature requests
- For security vulnerabilities, see [SECURITY.md](SECURITY.md) — **do not open a public issue**
