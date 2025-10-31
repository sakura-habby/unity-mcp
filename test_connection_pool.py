#!/usr/bin/env python3
"""
Test script to verify connection pool behavior
"""
import sys
import os

# Add Server directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Server'))

from unity_connection import get_unity_connection_pool
from port_discovery import PortDiscovery

def main():
    print("🔍 Testing Unity Connection Pool\n")
    print("=" * 80)

    # Initialize pool
    pool = get_unity_connection_pool()

    # Discover all instances
    print("\n1️⃣ Discovering all Unity instances...")
    instances = pool.discover_all_instances(force_refresh=True)

    if not instances:
        print("❌ No Unity instances found!")
        print("Make sure Unity Editor(s) are running with MCP for Unity bridge.")
        return

    print(f"✅ Found {len(instances)} instance(s):\n")
    for i, inst in enumerate(instances, 1):
        print(f"[{i}] ID:     {inst.id}")
        print(f"    Name:   {inst.name}")
        print(f"    Port:   {inst.port}")
        print(f"    Hash:   {inst.hash}")
        print(f"    Path:   {inst.path}")
        print(f"    Status: {inst.status}")
        print()

    # Check for duplicate ports
    ports = [inst.port for inst in instances]
    if len(ports) != len(set(ports)):
        print("⚠️  WARNING: Multiple instances have the same port!")
        print(f"   Ports: {ports}")
        print("   This means only one Unity Editor is actually running,")
        print("   and the others are stale status files.\n")

    # Test connection to each instance
    print("\n2️⃣ Testing connections to each instance...")
    print("-" * 80)

    for inst in instances:
        print(f"\nTesting: {inst.id} (port {inst.port})")
        try:
            conn = pool.get_connection(inst.id)
            print(f"  ✅ Connection created: {conn}")
            print(f"     - Host: {conn.host}")
            print(f"     - Port: {conn.port}")
            print(f"     - Socket: {conn.sock}")

            # Try to send a simple command
            response = conn.send_command("manage_editor", {"action": "get_project_root"})
            if isinstance(response, dict) and response.get("success"):
                project_root = response.get("data", {}).get("projectRoot", "Unknown")
                print(f"  ✅ Command succeeded!")
                print(f"     - Project Root: {project_root}")
            else:
                print(f"  ⚠️  Command failed: {response}")

        except Exception as e:
            print(f"  ❌ Connection failed: {e}")

    # Check connections in pool
    print("\n" + "=" * 80)
    print(f"\n3️⃣ Connections in pool: {len(pool._connections)}")
    for instance_id, conn in pool._connections.items():
        print(f"  - {instance_id}: port {conn.port}")

    # Test if different instance IDs route to different ports
    if len(instances) >= 2:
        print("\n" + "=" * 80)
        print("\n4️⃣ Testing if different instances route to different connections...")

        inst1 = instances[0]
        inst2 = instances[1]

        conn1 = pool.get_connection(inst1.id)
        conn2 = pool.get_connection(inst2.id)

        print(f"\nInstance 1: {inst1.id}")
        print(f"  - Expected port: {inst1.port}")
        print(f"  - Connection port: {conn1.port}")
        print(f"  - Socket object: {id(conn1.sock)}")

        print(f"\nInstance 2: {inst2.id}")
        print(f"  - Expected port: {inst2.port}")
        print(f"  - Connection port: {conn2.port}")
        print(f"  - Socket object: {id(conn2.sock)}")

        if conn1.port == conn2.port:
            print("\n⚠️  PROBLEM IDENTIFIED:")
            print("   Both instances are using the same port!")
            print("   This means the status files have the same port value,")
            print("   which suggests only one Unity Editor is running.")
        elif conn1 is conn2:
            print("\n⚠️  PROBLEM IDENTIFIED:")
            print("   Both instance IDs are returning the SAME connection object!")
            print("   This is a bug in the connection pool logic.")
        else:
            print("\n✅ Routing is working correctly!")
            print("   Different instances use different connections.")

if __name__ == "__main__":
    main()
