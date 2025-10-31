#!/usr/bin/env python3
"""
Cleanup stale Unity instance files
"""
import json
import socket
import struct
from pathlib import Path
from datetime import datetime

def check_port(port):
    """Check if a port is actually listening using Unity's framed protocol"""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.0) as s:
            # 1. Receive handshake from Unity
            handshake = s.recv(512)
            if b"FRAMING=1" not in handshake:
                return False

            # 2. Send framed ping command
            payload = b"ping"
            header = struct.pack('>Q', len(payload))
            s.sendall(header + payload)

            # 3. Receive framed response
            response_header = s.recv(8)
            if len(response_header) != 8:
                return False

            response_length = struct.unpack('>Q', response_header)[0]
            if response_length > 10000:
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

    print("🧹 Cleaning up stale Unity instance files...\n")

    status_files = list(unity_mcp_dir.glob("unity-mcp-status-*.json"))
    port_files = list(unity_mcp_dir.glob("unity-mcp-port-*.json"))

    removed_count = 0

    # Check each status file
    for status_file in status_files:
        try:
            with open(status_file) as f:
                data = json.load(f)

            port = data.get('unity_port')
            if not isinstance(port, int):
                print(f"⚠️  Skipping {status_file.name}: invalid port")
                continue

            # Check if port is responding
            if not check_port(port):
                print(f"🗑️  Removing {status_file.name}: port {port} not responding")
                status_file.unlink()

                # Also remove corresponding port file
                hash_value = status_file.stem.replace('unity-mcp-status-', '')
                port_file = unity_mcp_dir / f"unity-mcp-port-{hash_value}.json"
                if port_file.exists():
                    print(f"🗑️  Removing {port_file.name}")
                    port_file.unlink()

                removed_count += 1
            else:
                project_path = data.get('project_path', 'Unknown')
                project_name = Path(project_path).parent.name if 'Assets' in project_path else 'Unknown'
                print(f"✅ Keeping {status_file.name}: {project_name} on port {port}")

        except Exception as e:
            print(f"❌ Error processing {status_file.name}: {e}")

    print(f"\n📊 Summary:")
    print(f"   Removed {removed_count} stale file(s)")
    print(f"   Kept {len(status_files) - removed_count} active instance(s)")

    if removed_count > 0:
        print("\n✅ Cleanup complete! The status files now reflect only running Unity instances.")
    else:
        print("\n✅ No stale files found. All status files are for active Unity instances.")

if __name__ == "__main__":
    main()
