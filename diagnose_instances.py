#!/usr/bin/env python3
"""
Diagnostic script to check Unity instance status files
"""
import json
import os
from pathlib import Path
from datetime import datetime
import socket
import struct

def check_port(port):
    """Check if a port is actually listening using Unity's framed protocol"""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.0) as s:
            # 1. Receive handshake from Unity
            handshake = s.recv(512)
            if b"FRAMING=1" not in handshake:
                return False

            # 2. Send framed ping command
            # Frame format: 8-byte length header (big-endian uint64) + payload
            payload = b"ping"
            header = struct.pack('>Q', len(payload))  # >Q = big-endian unsigned long long
            s.sendall(header + payload)

            # 3. Receive framed response
            response_header = s.recv(8)
            if len(response_header) != 8:
                return False

            response_length = struct.unpack('>Q', response_header)[0]
            if response_length > 10000:  # Sanity check
                return False

            response = s.recv(response_length)
            return b'"message":"pong"' in response
    except:
        return False

def main():
    unity_mcp_dir = Path.home() / ".unity-mcp"

    if not unity_mcp_dir.exists():
        print(f"❌ Directory not found: {unity_mcp_dir}")
        return

    print(f"📁 Checking directory: {unity_mcp_dir}\n")

    # Find all status files
    status_files = sorted(unity_mcp_dir.glob("unity-mcp-status-*.json"))
    port_files = sorted(unity_mcp_dir.glob("unity-mcp-port-*.json"))

    print(f"Found {len(status_files)} status files and {len(port_files)} port files\n")
    print("=" * 80)

    # Check each status file
    for i, status_file in enumerate(status_files, 1):
        print(f"\n[{i}] {status_file.name}")
        print("-" * 80)

        try:
            with open(status_file) as f:
                data = json.load(f)

            # Extract info
            project_path = data.get('project_path', 'Unknown')
            port = data.get('unity_port', 'Unknown')
            reloading = data.get('reloading', False)
            last_heartbeat = data.get('last_heartbeat', 'Unknown')

            # Extract project name
            if project_path and project_path != 'Unknown':
                project_name = Path(project_path).parent.name if 'Assets' in project_path else 'Unknown'
            else:
                project_name = 'Unknown'

            # Extract hash from filename
            hash_value = status_file.stem.replace('unity-mcp-status-', '')

            print(f"  Project Name:    {project_name}")
            print(f"  Project Path:    {project_path}")
            print(f"  Hash:            {hash_value}")
            print(f"  Port:            {port}")
            print(f"  Reloading:       {reloading}")
            print(f"  Last Heartbeat:  {last_heartbeat}")

            # Check file modification time
            mtime = datetime.fromtimestamp(status_file.stat().st_mtime)
            age_seconds = (datetime.now() - mtime).total_seconds()
            print(f"  File Modified:   {mtime} ({age_seconds:.1f}s ago)")

            # Check if port is actually responding
            if isinstance(port, int):
                is_alive = check_port(port)
                print(f"  Port Responding: {'✅ YES' if is_alive else '❌ NO'}")
            else:
                print(f"  Port Responding: ⚠️  Invalid port")

            # Check corresponding port file
            port_file = unity_mcp_dir / f"unity-mcp-port-{hash_value}.json"
            if port_file.exists():
                with open(port_file) as f:
                    port_data = json.load(f)
                    port_from_file = port_data.get('port', 'Unknown')
                    print(f"  Port File Says:  {port_from_file}")
            else:
                print(f"  Port File:       ⚠️  Not found")

        except Exception as e:
            print(f"  ❌ Error reading file: {e}")

    print("\n" + "=" * 80)
    print("\n🔍 Summary:")

    # Count unique ports
    ports = set()
    alive_ports = set()
    for status_file in status_files:
        try:
            with open(status_file) as f:
                data = json.load(f)
                port = data.get('unity_port')
                if isinstance(port, int):
                    ports.add(port)
                    if check_port(port):
                        alive_ports.add(port)
        except:
            pass

    print(f"  Total status files:        {len(status_files)}")
    print(f"  Unique ports in files:     {len(ports)} - {sorted(ports)}")
    print(f"  Ports actually responding: {len(alive_ports)} - {sorted(alive_ports)}")

    if len(ports) == 1 and len(status_files) > 1:
        print("\n⚠️  WARNING: Multiple status files but all have the same port!")
        print("   This suggests old files from closed Unity instances.")
        print("   Consider cleaning up old files.")

    if len(alive_ports) < len(status_files):
        print(f"\n⚠️  WARNING: {len(status_files) - len(alive_ports)} status file(s) have dead ports!")
        print("   These are likely from closed Unity instances.")

if __name__ == "__main__":
    main()
