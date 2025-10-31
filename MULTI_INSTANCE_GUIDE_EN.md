# Unity MCP Multi-Instance Support Guide

## 📖 Overview

Unity MCP now supports controlling multiple Unity Editor instances simultaneously, enabling cross-project operations.

### Key Features

- ✅ Connect to multiple Unity Editor instances at once
- ✅ Select target instance by project name, hash, or combined identifier
- ✅ Automatic port allocation and conflict resolution
- ✅ Cross-project operations (e.g., read from Project A, write to Project B)
- ✅ Connection pool caching for performance
- ✅ Automatic status file cleanup

## 🚀 Quick Start

### 1. Start Multiple Unity Projects

Each Unity Editor instance will automatically:
- Assign a unique port (6400, 6401, 6402...)
- Create a status file: `~/.unity-mcp/unity-mcp-status-{hash}.json`
- Start heartbeat updates (includes project name, path, port, etc.)

### 2. List All Running Instances

```python
# Use the list_unity_instances tool
result = list_unity_instances()

# Example output:
{
  "instances": [
    {
      "id": "MyGame@a1b2c3d4",
      "name": "MyGame",
      "path": "/Users/you/Projects/MyGame/Assets",
      "port": 6400,
      "status": "running",
      "unity_version": "2022.3.10f1"
    },
    {
      "id": "AnotherProject@e5f6g7h8",
      "name": "AnotherProject",
      "path": "/Users/you/Projects/AnotherProject/Assets",
      "port": 6401,
      "status": "running",
      "unity_version": "2021.3.25f1"
    }
  ]
}
```

### 3. Specify Target Instance

All tools support an optional `unity_instance` parameter:

```python
# Method 1: Use project name (if unique)
manage_scene(action="get_active", unity_instance="MyGame")

# Method 2: Use full identifier (project name@hash)
manage_scene(action="get_active", unity_instance="MyGame@a1b2c3d4")

# Method 3: Use hash
manage_scene(action="get_active", unity_instance="a1b2c3d4")

# Method 4: Use port number
manage_scene(action="get_active", unity_instance="6401")

# Method 5: Omit (use default instance)
manage_scene(action="get_active")
```

## 🎯 Cross-Project Operation Examples

### Scenario 1: Copy Asset from Project A to Project B

```python
# 1. Read asset from ProjectA
asset_info = manage_asset(
    action="get_info",
    path="Assets/Prefabs/Character.prefab",
    unity_instance="ProjectA"
)

# 2. Read asset content
asset_content = read_resource(
    path="Assets/Prefabs/Character.prefab",
    unity_instance="ProjectA"
)

# 3. Create asset in ProjectB
manage_asset(
    action="create",
    path="Assets/ImportedPrefabs/Character.prefab",
    content=asset_content,
    unity_instance="ProjectB"
)
```

### Scenario 2: Compare Scene Configurations

```python
# Get active scene from ProjectA
scene_a = manage_scene(
    action="get_active",
    unity_instance="ProjectA"
)

# Get active scene from ProjectB
scene_b = manage_scene(
    action="get_active",
    unity_instance="ProjectB"
)

# Compare configurations...
```

### Scenario 3: Batch Operations Across Projects

```python
# Get all instances
instances = list_unity_instances()

# Execute same operation on each project
for instance in instances["instances"]:
    instance_id = instance["id"]

    # Read console logs
    logs = read_console(
        log_type="all",
        unity_instance=instance_id
    )

    # Run tests
    run_tests(
        test_mode="EditMode",
        unity_instance=instance_id
    )
```

## ⚙️ Configure Default Instance

### Method 1: Environment Variable (Recommended)

```bash
# Set default instance
export UNITY_MCP_DEFAULT_INSTANCE="MyGame"

# Or use full identifier
export UNITY_MCP_DEFAULT_INSTANCE="MyGame@a1b2c3d4"

# Start server
python -m src.server
```

### Method 2: Command-Line Argument

```bash
# Specify default instance directly
python -m src.server --default-instance "MyGame"

# Command-line takes precedence over environment variable
UNITY_MCP_DEFAULT_INSTANCE="ProjectA" python -m src.server --default-instance "ProjectB"
# Result: Uses ProjectB
```

### Default Instance Behavior

- If `unity_instance` is not specified, the default instance will be used
- If no default instance is configured, the most recently started Unity Editor will be used
- If the specified default instance doesn't exist, it falls back to the most recent instance

## 🔍 Instance Identifier Matching Rules

UnityConnectionPool matches instances with the following priority:

1. **Full ID Match**: `"MyGame@a1b2c3d4"` → Exact match
2. **Project Name Match**: `"MyGame"` → Matches if unique, error otherwise
3. **Hash Match**: `"a1b2c3d4"` → Matches hash prefix
4. **Port Match**: `"6401"` → Matches port
5. **Path Match**: `"/path/to/project/Assets"` → Exact path

### Handling Duplicate Project Names

If multiple projects have the same name:

```python
# ❌ Will fail: Multiple projects named "MyGame"
manage_scene(action="get_active", unity_instance="MyGame")
# Error: Multiple Unity instances found with name 'MyGame': ['MyGame@a1b2c3d4', 'MyGame@e5f6g7h8']

# ✅ Use full identifier
manage_scene(action="get_active", unity_instance="MyGame@a1b2c3d4")
```

The `list_unity_instances` tool will automatically warn about duplicate names.

## 📁 Status File Format

Each Unity instance's status file is located at:
```
~/.unity-mcp/unity-mcp-status-{hash}.json
```

Example content:
```json
{
  "unity_port": 6400,
  "project_path": "/Users/you/Projects/MyGame/Assets",
  "project_name": "MyGame",
  "unity_version": "2022.3.10f1",
  "last_heartbeat": "2025-10-31T12:34:56.789Z",
  "reloading": false,
  "reason": "ready",
  "seq": 42
}
```

### Status File Lifecycle

- **Created**: When Unity Editor starts
- **Updated**: On each heartbeat (typically every second)
- **Deleted**: Automatically deleted when Unity Editor closes

## 🛠️ Tool Reference

### All Tools Supporting `unity_instance` Parameter

All the following tools support an optional `unity_instance` parameter:

**Scene Management**:
- `manage_scene` - Scene operations (load, save, create, etc.)

**Asset Management**:
- `manage_asset` - Asset CRUD operations
- `list_resources` - List assets
- `read_resource` - Read asset content
- `find_in_file` - Search in files

**GameObject Management**:
- `manage_gameobject` - GameObject operations

**Script Management**:
- `manage_script` - Script operations
- `script_apply_edits` - Apply script edits

**Prefab Management**:
- `manage_prefabs` - Prefab operations

**Editor Control**:
- `manage_editor` - Editor control (play, pause, stop)
- `execute_menu_item` - Execute menu commands

**Shader Management**:
- `manage_shader` - Shader operations

**Testing**:
- `run_tests` - Run Unity tests

**Logging**:
- `read_console` - Read console logs

**New Tools**:
- `list_unity_instances` - List all running instances

## 🔧 Troubleshooting

### Issue 1: Multiple Instances Show Same Port

**Symptom**: Two Unity instances both show port 6400

**Cause**: Port conflict issue in early versions

**Solution**:
1. Ensure you're using the latest version (SO_REUSEADDR issue fixed)
2. Clean up old status files:
   ```bash
   python3 cleanup_stale_instances.py
   ```
3. Restart all Unity Editors

### Issue 2: Instance Not Responding

**Symptom**: `diagnose_instances.py` shows "Port Responding: ❌ NO"

**Checks**:
1. Confirm Unity Editor is actually running
2. Check Unity Console for MCP Bridge errors
3. Verify port is not used by other programs:
   ```bash
   lsof -i :6400
   lsof -i :6401
   ```

**Solution**:
```bash
# Clean up stale instances
python3 cleanup_stale_instances.py

# Run diagnostics
python3 diagnose_instances.py
```

### Issue 3: Specified Instance Not Found

**Symptom**: Error message "Unity instance 'MyProject' not found"

**Checks**:
1. List all instances:
   ```python
   list_unity_instances()
   ```
2. Verify instance ID spelling
3. Confirm Unity Editor is running

**Solution**:
- Use `list_unity_instances()` to get accurate instance IDs
- If project names are duplicated, use full identifier (`Name@hash`)

### Issue 4: Connection Pool Cache Expired

**Symptom**: Newly started Unity instance not recognized

**Solution**:
```python
# Force refresh instance list
list_unity_instances(force_refresh=True)
```

The connection pool automatically refreshes every 5 seconds, so manual refresh is rarely needed.

## 📊 Diagnostic Tools

### diagnose_instances.py

Diagnose all running Unity instances:

```bash
cd ~/work/unity-mcp
python3 diagnose_instances.py
```

Example output:
```
Found 2 Unity instance status files in /Users/you/.unity-mcp:

[1] unity-mcp-status-a1b2c3d4.json
  Project Name:    MyGame
  Project Path:    /Users/you/Projects/MyGame/Assets
  Port:            6400
  Unity Version:   2022.3.10f1
  Last Heartbeat:  2025-10-31T12:34:56.789Z
  Status:          running
  Port Responding: ✅ YES

[2] unity-mcp-status-e5f6g7h8.json
  Project Name:    AnotherProject
  Project Path:    /Users/you/Projects/AnotherProject/Assets
  Port:            6401
  Unity Version:   2021.3.25f1
  Last Heartbeat:  2025-10-31T12:35:12.456Z
  Status:          running
  Port Responding: ✅ YES

Summary:
  Total status files:        2
  Unique ports in files:     2 - [6400, 6401]
  Ports actually responding: 2 - [6400, 6401]
  Stale instances:           0
```

### cleanup_stale_instances.py

Clean up expired status files:

```bash
cd ~/work/unity-mcp
python3 cleanup_stale_instances.py
```

Will delete:
- Instances with non-responding ports
- Instances with timed-out heartbeats (> 10 seconds)

## 🏗️ Architecture Overview

### Connection Pool Design

```
MCP Server (Python)
    │
    ├─ UnityConnectionPool
    │   ├─ Cache (5s TTL)
    │   ├─ Connection Management
    │   └─ Instance Discovery
    │
    ├─ UnityConnection (per instance)
    │   ├─ TCP Socket
    │   ├─ Framed Protocol
    │   └─ Command Queue
    │
    └─ Unity Editor Instances
        ├─ Instance 1 (Port 6400)
        ├─ Instance 2 (Port 6401)
        └─ Instance 3 (Port 6402)
```

### Port Allocation Strategy

1. **First Instance**: Try default port 6400
2. **Subsequent Instances**: Auto-increment if default is taken (6401, 6402...)
3. **Domain Reload**: Try to reuse previous port (via SO_REUSEADDR)
4. **Conflict Detection**: If port truly occupied by another instance, find new port

### Framed Protocol

Unity uses a strict framed protocol:

```
1. Handshake: "WELCOME UNITY-MCP 1 FRAMING=1\n"
2. Command: [8-byte big-endian length] + [UTF-8 payload]
3. Response: [8-byte big-endian length] + [UTF-8 payload]
```

Python implementation:
```python
# Send
payload = json.dumps(command).encode("utf-8")
header = struct.pack('>Q', len(payload))
socket.sendall(header + payload)

# Receive
header = socket.recv(8)
length = struct.unpack('>Q', header)[0]
response = socket.recv(length)
```

## 📝 Change Log

### v1.0 - Multi-Instance Support
- ✅ Implemented UnityConnectionPool connection pool
- ✅ Added `unity_instance` parameter to all tools
- ✅ Implemented instance discovery and status file scanning
- ✅ Fixed framed protocol port probing
- ✅ Fixed SO_REUSEADDR port conflict issue
- ✅ Added Unity-side project name and version info
- ✅ Implemented automatic status file cleanup
- ✅ Added environment variable and command-line argument support

## 🤝 Contributing

If you find issues or have suggestions for improvement, please submit an Issue or Pull Request.

## 📄 License

Same license as the main Unity MCP project.
