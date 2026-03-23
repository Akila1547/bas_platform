"""
Purple Team Telemetry — Native Windows Event Log Parser
=======================================================
Agentlessly queries the Windows Victim VM via WinRM to pull real
Security / PowerShell Operational event logs that correspond to the
MITRE ATT&CK techniques executed by our playbooks.

Metrics produced (ONLY what we can prove):
  - True Positive Rate (TPR): techniques that generated any matching
    Event ID on the victim / total techniques executed × 100
  - Mean Time to Detect (MTTD): average of (log_timestamp − attack_trigger_time)
    across detected techniques, in seconds.

Metrics deliberately NOT included:
  - False Positive Rate (FPR): requires an active SIEM monitoring benign
    traffic and raising alerts — impossible without one.
  - Forensic Completeness (FC): requires correlating ALL expected artifact
    sources (registry, prefetch, memory dumps, SIEM) — not just Event IDs.
    Using only WinRM+Event IDs it would be identical to TPR and thus fake.
"""

import logging
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# File path where attack trigger times are written by main.py
# ---------------------------------------------------------------------------
ATTACK_LOG_PATH = "/tmp/bas_attack_log.json"


class EventLogParser:
    """
    Agentless Purple Team Telemetry Parser.
    Connects to the Windows VM via WinRM and queries the native Event Logs
    (Security, PowerShell Operational) to pull technique-specific Event IDs.
    """

    def __init__(self):
        # Pull connection settings from environment (same pattern as collector.py)
        import os
        self.host = os.getenv("VICTIM_IP", os.getenv("ALLOWED_TARGETS", "192.168.56.102").split(",")[0].strip())
        self.username = os.getenv("VICTIM_USERNAME", "Administrator")
        self.password = os.getenv("VICTIM_PASSWORD", "Password123!")

        # ------------------------------------------------------------------
        # Mapping: MITRE Technique ID → Windows Event IDs it is expected to generate
        # Source: MITRE ATT&CK data sources, Windows Security log reference.
        # ------------------------------------------------------------------
        self.technique_to_events = {
            "T1087":   [{"id": 4798, "name": "User Account Enumerated",         "log": "Security"}],
            "T1057":   [{"id": 4688, "name": "Process Creation",                "log": "Security"}],
            "T1016":   [{"id": 4688, "name": "Process Creation",                "log": "Security"}],
            "T1083":   [{"id": 4688, "name": "Process Creation",                "log": "Security"}],
            "T1003.001": [
                {"id": 4656, "name": "Handle to Object Requested",             "log": "Security"},
                {"id": 4663, "name": "Attempt to Access Object",               "log": "Security"},
            ],
            "T1053.005": [{"id": 4698, "name": "Scheduled Task Created",       "log": "Security"}],
            "T1059.001": [{"id": 4104, "name": "PowerShell Script Block Logging", "log": "Microsoft-Windows-PowerShell/Operational"}],
            "T1071.001": [{"id": 4104, "name": "PowerShell Script Block Logging", "log": "Microsoft-Windows-PowerShell/Operational"}],
            "T1562.001": [
                {"id": 4104, "name": "PowerShell Script Block Logging",        "log": "Microsoft-Windows-PowerShell/Operational"},
                {"id": 5007, "name": "Defender Configuration Changed",         "log": "Microsoft-Windows-Windows Defender/Operational"},
            ],
            "T1070.001": [
                {"id": 1102, "name": "Audit Log Cleared",                      "log": "Security"},
                {"id": 104,  "name": "System Log File Cleared",                "log": "System"},
            ],
            "T1562.004": [{"id": 4688, "name": "Process Creation",             "log": "Security"}],
            "T1496":   [{"id": 4104, "name": "PowerShell Script Block Logging", "log": "Microsoft-Windows-PowerShell/Operational"}],
            "T1486":   [
                {"id": 4104, "name": "PowerShell Script Block Logging",        "log": "Microsoft-Windows-PowerShell/Operational"},
                {"id": 4663, "name": "File System Object Access",              "log": "Security"},
            ],
            "T1555.003": [{"id": 4688, "name": "Process Creation",             "log": "Security"}],
            # ── Lateral Movement techniques (lateral_movement_sliver playbook) ──
            "T1021.002": [
                {"id": 5140, "name": "Network Share Object Accessed",          "log": "Security"},
                {"id": 5145, "name": "Network Share Object Access Checked",    "log": "Security"},
                {"id": 4624, "name": "Logon Success (Network/SMB)",            "log": "Security"},
                {"id": 4625, "name": "Logon Failure (SMB)",                   "log": "Security"},
            ],
            "T1570": [
                {"id": 4663, "name": "File System Object Access (Tool Drop)", "log": "Security"},
                {"id": 4688, "name": "Process Creation (Tool Execution)",     "log": "Security"},
            ],
            "T1021.001": [
                {"id": 4778, "name": "RDP Session Reconnected",               "log": "Security"},
                {"id": 4624, "name": "Logon Success (RemoteInteractive)",     "log": "Security"},
            ],
        }

        # MITRE ATT&CK reference links
        self.mitre_links = {
            "T1087":     "https://attack.mitre.org/techniques/T1087/",
            "T1057":     "https://attack.mitre.org/techniques/T1057/",
            "T1016":     "https://attack.mitre.org/techniques/T1016/",
            "T1083":     "https://attack.mitre.org/techniques/T1083/",
            "T1003.001": "https://attack.mitre.org/techniques/T1003/001/",
            "T1053.005": "https://attack.mitre.org/techniques/T1053/005/",
            "T1059.001": "https://attack.mitre.org/techniques/T1059/001/",
            "T1071.001": "https://attack.mitre.org/techniques/T1071/001/",
            "T1562.001": "https://attack.mitre.org/techniques/T1562/001/",
            "T1070.001": "https://attack.mitre.org/techniques/T1070/001/",
            "T1562.004": "https://attack.mitre.org/techniques/T1562/004/",
            "T1496":     "https://attack.mitre.org/techniques/T1496/",
            "T1486":     "https://attack.mitre.org/techniques/T1486/",
            "T1555.003": "https://attack.mitre.org/techniques/T1555/003/",
            "T1021.002": "https://attack.mitre.org/techniques/T1021/002/",
            "T1570":     "https://attack.mitre.org/techniques/T1570/",
            "T1021.001": "https://attack.mitre.org/techniques/T1021/001/",
        }

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _get_session(self):
        """Return a WinRM session to the victim VM."""
        import winrm
        return winrm.Session(
            f"http://{self.host}:5985/wsman",
            auth=(self.username, self.password),
            transport="ntlm",
            server_cert_validation="ignore",
        )

    def _read_attack_log(self) -> List[Dict]:
        """
        Read the JSON sidecar written by api/main.py.
        Returns a list of {playbook_name, technique_ids, trigger_time} dicts.
        """
        try:
            if os.path.exists(ATTACK_LOG_PATH):
                with open(ATTACK_LOG_PATH, "r") as f:
                    data = json.load(f)
                    # File can be a single dict or a list of dicts
                    if isinstance(data, dict):
                        return [data]
                    return data
        except Exception as e:
            logger.warning(f"Could not read attack log: {e}")
        return []

    def _get_trigger_time_for_technique(self, technique_id: str) -> Optional[datetime]:
        """
        Look up the most recent attack trigger time for a given technique ID.
        Returns a timezone-aware UTC datetime or None.
        """
        records = self._read_attack_log()
        # Find the latest record that lists this technique
        matched_times = []
        for rec in records:
            tech_ids = rec.get("technique_ids", [])
            if technique_id in tech_ids or not tech_ids:
                t = rec.get("trigger_time")
                if t:
                    try:
                        dt = datetime.fromisoformat(t)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        matched_times.append(dt)
                    except ValueError:
                        pass
        if matched_times:
            return max(matched_times)  # most recent
        return None

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def query_events_for_technique(self, technique_id: str, minutes_back: int = 10) -> List[Dict]:
        """
        Query Windows Event Logs on the victim VM for the given technique.
        Returns a list of matched event descriptors (summary, not full messages).
        """
        if technique_id not in self.technique_to_events:
            return []

        expected_events = self.technique_to_events[technique_id]
        found_events = []

        try:
            session = self._get_session()

            for event_info in expected_events:
                eid = event_info["id"]
                log_name = event_info["log"]

                ps_script = f"""
$StartTime = (Get-Date).AddMinutes(-{minutes_back})
try {{
    $events = Get-WinEvent -FilterHashtable @{{LogName='{log_name}'; ID={eid}; StartTime=$StartTime}} -MaxEvents 10 -ErrorAction Stop
    $results = @()
    foreach ($e in $events) {{
        $results += [PSCustomObject]@{{
            "Time"    = $e.TimeCreated.ToString("s");
            "EventId" = $e.Id;
            "LogName" = $e.LogName;
            "Message" = $e.Message.Substring(0, [Math]::Min($e.Message.Length, 300))
        }}
    }}
    $results | ConvertTo-Json -Compress
}} catch {{
    Write-Output "[]"
}}
"""
                result = session.run_ps(ps_script)

                if result.status_code == 0:
                    output = result.std_out.decode("utf-8").strip()
                    if output and output != "[]":
                        try:
                            records = json.loads(output)
                            if not isinstance(records, list):
                                records = [records]

                            found_events.append({
                                "event_id":        eid,
                                "name":            event_info["name"],
                                "log_source":      log_name,
                                "description":     (
                                    f"Windows Event ID {eid} ({event_info['name']}) detected. "
                                    f"This Event ID is generated when MITRE technique {technique_id} executes on the victim."
                                ),
                                "mitre_link":      self.mitre_links.get(technique_id, "https://attack.mitre.org/"),
                                "count":           len(records),
                                "latest_timestamp": records[0].get("Time", ""),
                            })
                        except json.JSONDecodeError:
                            pass

        except Exception as e:
            logger.error(f"WinRM query failed for {technique_id}: {e}")

        return found_events

    def get_raw_events_for_technique(self, technique_id: str, minutes_back: int = 10) -> List[Dict]:
        """
        Returns raw event records (with message snippets) for a technique.
        Used to populate the "Live Evidence" panel in the UI.
        """
        if technique_id not in self.technique_to_events:
            return []

        expected_events = self.technique_to_events[technique_id]
        raw_records = []

        try:
            session = self._get_session()

            for event_info in expected_events:
                eid = event_info["id"]
                log_name = event_info["log"]

                ps_script = f"""
$StartTime = (Get-Date).AddMinutes(-{minutes_back})
try {{
    $events = Get-WinEvent -FilterHashtable @{{LogName='{log_name}'; ID={eid}; StartTime=$StartTime}} -MaxEvents 5 -ErrorAction Stop
    $results = @()
    foreach ($e in $events) {{
        $results += [PSCustomObject]@{{
            "Time"    = $e.TimeCreated.ToString("s");
            "EventId" = $e.Id;
            "LogName" = $e.LogName;
            "Message" = $e.Message.Substring(0, [Math]::Min($e.Message.Length, 400))
        }}
    }}
    $results | ConvertTo-Json -Compress
}} catch {{
    Write-Output "[]"
}}
"""
                result = session.run_ps(ps_script)

                if result.status_code == 0:
                    output = result.std_out.decode("utf-8").strip()
                    if output and output != "[]":
                        try:
                            records = json.loads(output)
                            if not isinstance(records, list):
                                records = [records]
                            for rec in records:
                                raw_records.append({
                                    "technique_id": technique_id,
                                    "event_id":     eid,
                                    "event_name":   event_info["name"],
                                    "log_source":   log_name,
                                    "timestamp":    rec.get("Time", ""),
                                    "message":      rec.get("Message", ""),
                                    "mitre_link":   self.mitre_links.get(technique_id, ""),
                                })
                        except json.JSONDecodeError:
                            pass

        except Exception as e:
            logger.error(f"Raw event fetch failed for {technique_id}: {e}")

        return raw_records

    def get_all_raw_events(self, executed_techniques: List[str], minutes_back: int = 15) -> List[Dict]:
        """
        Fetches raw event records for ALL provided techniques.
        Returns a flat list of event records sorted by timestamp descending.
        """
        all_records = []
        for tech in executed_techniques:
            all_records.extend(self.get_raw_events_for_technique(tech, minutes_back))

        # Sort by timestamp descending (most recent first)
        all_records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return all_records

    def generate_evaluation_metrics(self, executed_techniques: List[str]) -> Dict:
        """
        Calculates Purple Team metrics based on actual Windows Event Log queries
        via WinRM against the victim VM.

        Returns ONLY metrics we can genuinely prove:
          - tpr:  True Positive Rate (real WinRM query result)
          - mttd: Mean Time to Detect in seconds (attack trigger time vs log timestamp)

        FC and FPR are intentionally absent — they require a SIEM to calculate
        accurately. Showing fake numbers would violate the professor's rule:
        "Don't put things you cannot implement."
        """
        metrics = {
            "tpr":                0.0,
            "mttd":               None,   # None = not yet calculable (no trigger times)
            "mttd_unit":          "seconds",
            "total_executed":     len(executed_techniques),
            "detected_techniques": 0,
            "details":            {},
            "methodology": {
                "tpr":  "techniques_with_matching_EventID_on_victim / total_executed × 100. Verified by direct WinRM query to Windows Event Viewer.",
                "mttd": "Average of (log_timestamp - attack_trigger_time) across all detected techniques, in seconds. attack_trigger_time is recorded in /tmp/bas_attack_log.json when a playbook fires.",
            },
        }

        if not executed_techniques:
            return metrics

        detected = 0
        mttd_samples = []

        for tech in executed_techniques:
            events = self.query_events_for_technique(tech)
            metrics["details"][tech] = events

            if len(events) > 0:
                detected += 1

                # Try to calculate MTTD for this technique
                trigger_dt = self._get_trigger_time_for_technique(tech)
                if trigger_dt and events[0].get("latest_timestamp"):
                    try:
                        log_dt = datetime.fromisoformat(events[0]["latest_timestamp"])
                        if log_dt.tzinfo is None:
                            log_dt = log_dt.replace(tzinfo=timezone.utc)
                        diff_seconds = (log_dt - trigger_dt).total_seconds()
                        # Only include positive diffs (log after trigger)
                        if diff_seconds >= 0:
                            mttd_samples.append(diff_seconds)
                    except Exception as e:
                        logger.warning(f"MTTD calc failed for {tech}: {e}")

        metrics["detected_techniques"] = detected

        # TPR
        metrics["tpr"] = round((detected / len(executed_techniques)) * 100, 2)

        # MTTD — only set if we have real samples
        if mttd_samples:
            metrics["mttd"] = round(sum(mttd_samples) / len(mttd_samples), 2)

        return metrics


# Singleton instance
event_parser = EventLogParser()
