# Unity MCP 多实例支持指南

## 📖 概述

Unity MCP 现在支持同时控制多个 Unity Editor 实例，使您可以在不同项目之间执行跨项目操作。

### 核心功能

- ✅ 同时连接多个 Unity Editor 实例
- ✅ 通过项目名称、哈希值或组合标识符选择目标实例
- ✅ 自动端口分配和冲突解决
- ✅ 跨项目操作（如从项目 A 读取，写入项目 B）
- ✅ 连接池缓存以提高性能
- ✅ 状态文件自动清理

## 🚀 快速开始

### 1. 启动多个 Unity 项目

每个 Unity Editor 实例会自动：
- 分配唯一的端口（6400, 6401, 6402...）
- 创建状态文件：`~/.unity-mcp/unity-mcp-status-{hash}.json`
- 开始心跳更新（包含项目名称、路径、端口等信息）

### 2. 列出所有运行的实例

```python
# 使用 list_unity_instances 工具
result = list_unity_instances()

# 输出示例：
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

### 3. 指定目标实例

所有工具都支持可选的 `unity_instance` 参数：

```python
# 方式 1: 使用项目名称（如果名称唯一）
manage_scene(action="get_active", unity_instance="MyGame")

# 方式 2: 使用完整标识符（项目名称@哈希）
manage_scene(action="get_active", unity_instance="MyGame@a1b2c3d4")

# 方式 3: 使用哈希值
manage_scene(action="get_active", unity_instance="a1b2c3d4")

# 方式 4: 使用端口号
manage_scene(action="get_active", unity_instance="6401")

# 方式 5: 不指定（使用默认实例）
manage_scene(action="get_active")
```

## 🎯 跨项目操作示例

### 场景 1: 从项目 A 复制资源到项目 B

```python
# 1. 从 ProjectA 读取资源
asset_info = manage_asset(
    action="get_info",
    path="Assets/Prefabs/Character.prefab",
    unity_instance="ProjectA"
)

# 2. 读取资源内容
asset_content = read_resource(
    path="Assets/Prefabs/Character.prefab",
    unity_instance="ProjectA"
)

# 3. 在 ProjectB 中创建资源
manage_asset(
    action="create",
    path="Assets/ImportedPrefabs/Character.prefab",
    content=asset_content,
    unity_instance="ProjectB"
)
```

### 场景 2: 对比两个项目的场景配置

```python
# 获取 ProjectA 的活动场景
scene_a = manage_scene(
    action="get_active",
    unity_instance="ProjectA"
)

# 获取 ProjectB 的活动场景
scene_b = manage_scene(
    action="get_active",
    unity_instance="ProjectB"
)

# 对比配置...
```

### 场景 3: 批量操作多个项目

```python
# 获取所有实例
instances = list_unity_instances()

# 对每个项目执行相同操作
for instance in instances["instances"]:
    instance_id = instance["id"]

    # 读取控制台日志
    logs = read_console(
        log_type="all",
        unity_instance=instance_id
    )

    # 运行测试
    run_tests(
        test_mode="EditMode",
        unity_instance=instance_id
    )
```

## ⚙️ 配置默认实例

### 方法 1: 环境变量（推荐）

```bash
# 设置默认实例
export UNITY_MCP_DEFAULT_INSTANCE="MyGame"

# 或使用完整标识符
export UNITY_MCP_DEFAULT_INSTANCE="MyGame@a1b2c3d4"

# 启动服务器
python -m src.server
```

### 方法 2: 命令行参数

```bash
# 直接指定默认实例
python -m src.server --default-instance "MyGame"

# 命令行参数优先级高于环境变量
UNITY_MCP_DEFAULT_INSTANCE="ProjectA" python -m src.server --default-instance "ProjectB"
# 结果：使用 ProjectB
```

### 默认实例行为

- 如果未指定 `unity_instance` 参数，将使用默认实例
- 如果未配置默认实例，将使用最近启动的 Unity Editor
- 如果指定的默认实例不存在，将回退到最近的实例

## 🔍 实例标识符匹配规则

UnityConnectionPool 按以下优先级匹配实例：

1. **完整 ID 匹配**: `"MyGame@a1b2c3d4"` → 精确匹配
2. **项目名称匹配**: `"MyGame"` → 如果唯一则匹配，否则报错
3. **哈希值匹配**: `"a1b2c3d4"` → 匹配哈希前缀
4. **端口号匹配**: `"6401"` → 匹配端口
5. **路径匹配**: `"/path/to/project/Assets"` → 精确路径

### 处理重名项目

如果有多个项目名称相同：

```python
# ❌ 会失败：多个项目名为 "MyGame"
manage_scene(action="get_active", unity_instance="MyGame")
# 错误: Multiple Unity instances found with name 'MyGame': ['MyGame@a1b2c3d4', 'MyGame@e5f6g7h8']

# ✅ 使用完整标识符
manage_scene(action="get_active", unity_instance="MyGame@a1b2c3d4")
```

`list_unity_instances` 工具会自动警告重名情况。

## 📁 状态文件格式

每个 Unity 实例的状态文件位于：
```
~/.unity-mcp/unity-mcp-status-{hash}.json
```

内容示例：
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

### 状态文件生命周期

- **创建**: Unity Editor 启动时
- **更新**: 每次心跳（通常每秒一次）
- **删除**: Unity Editor 关闭时自动删除

## 🛠️ 工具参考

### 支持 `unity_instance` 参数的所有工具

所有以下工具都支持可选的 `unity_instance` 参数：

**场景管理**:
- `manage_scene` - 场景操作（加载、保存、创建等）

**资源管理**:
- `manage_asset` - 资源 CRUD 操作
- `list_resources` - 列出资源
- `read_resource` - 读取资源内容
- `find_in_file` - 在文件中搜索

**游戏对象管理**:
- `manage_gameobject` - GameObject 操作

**脚本管理**:
- `manage_script` - 脚本操作
- `script_apply_edits` - 应用脚本编辑

**预制体管理**:
- `manage_prefabs` - 预制体操作

**编辑器控制**:
- `manage_editor` - 编辑器控制（播放、暂停、停止）
- `execute_menu_item` - 执行菜单命令

**着色器管理**:
- `manage_shader` - 着色器操作

**测试**:
- `run_tests` - 运行 Unity 测试

**日志**:
- `read_console` - 读取控制台日志

**新工具**:
- `list_unity_instances` - 列出所有运行的实例

## 🔧 故障排除

### 问题 1: 多个实例显示相同端口

**症状**: 两个 Unity 实例都显示端口 6400

**原因**: 早期版本的端口冲突问题

**解决方案**:
1. 确保使用最新版本（已修复 SO_REUSEADDR 问题）
2. 清理旧的状态文件：
   ```bash
   python3 cleanup_stale_instances.py
   ```
3. 重启所有 Unity Editor

### 问题 2: 实例不响应

**症状**: `diagnose_instances.py` 显示 "Port Responding: ❌ NO"

**检查步骤**:
1. 确认 Unity Editor 确实在运行
2. 检查 Unity Console 是否有 MCP Bridge 错误
3. 验证端口未被其他程序占用：
   ```bash
   lsof -i :6400
   lsof -i :6401
   ```

**解决方案**:
```bash
# 清理过期实例
python3 cleanup_stale_instances.py

# 运行诊断
python3 diagnose_instances.py
```

### 问题 3: 找不到指定的实例

**症状**: 错误消息 "Unity instance 'MyProject' not found"

**检查步骤**:
1. 列出所有实例：
   ```python
   list_unity_instances()
   ```
2. 验证实例 ID 拼写正确
3. 确认 Unity Editor 正在运行

**解决方案**:
- 使用 `list_unity_instances()` 获取准确的实例 ID
- 如果项目重名，使用完整标识符（`Name@hash`）

### 问题 4: 连接池缓存过期

**症状**: 新启动的 Unity 实例未被识别

**解决方案**:
```python
# 强制刷新实例列表
list_unity_instances(force_refresh=True)
```

连接池每 5 秒自动刷新，通常不需要手动强制刷新。

## 📊 诊断工具

### diagnose_instances.py

诊断所有运行的 Unity 实例：

```bash
cd ~/work/unity-mcp
python3 diagnose_instances.py
```

输出示例：
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

清理过期的状态文件：

```bash
cd ~/work/unity-mcp
python3 cleanup_stale_instances.py
```

会删除：
- 端口不响应的实例
- 心跳超时的实例（> 10 秒）

## 🏗️ 架构说明

### 连接池设计

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

### 端口分配策略

1. **第一个实例**: 尝试默认端口 6400
2. **后续实例**: 如果默认端口被占用，自动递增（6401, 6402...）
3. **域重载**: 尝试重用之前的端口（通过 SO_REUSEADDR）
4. **冲突检测**: 如果端口真的被其他实例占用，查找新端口

### 帧格式协议

Unity 使用严格的帧格式协议：

```
1. 握手: "WELCOME UNITY-MCP 1 FRAMING=1\n"
2. 命令: [8字节大端序长度] + [UTF-8 负载]
3. 响应: [8字节大端序长度] + [UTF-8 负载]
```

Python 实现：
```python
# 发送
payload = json.dumps(command).encode("utf-8")
header = struct.pack('>Q', len(payload))
socket.sendall(header + payload)

# 接收
header = socket.recv(8)
length = struct.unpack('>Q', header)[0]
response = socket.recv(length)
```

## 📝 更新历史

### v1.0 - 多实例支持
- ✅ 实现 UnityConnectionPool 连接池
- ✅ 添加所有工具的 `unity_instance` 参数
- ✅ 实现实例发现和状态文件扫描
- ✅ 修复帧格式协议的端口探测
- ✅ 修复 SO_REUSEADDR 端口冲突问题
- ✅ 添加 Unity 端项目名称和版本信息
- ✅ 实现状态文件自动清理
- ✅ 添加环境变量和命令行参数支持

## 🤝 贡献

如果您发现问题或有改进建议，请提交 Issue 或 Pull Request。

## 📄 许可证

与 Unity MCP 主项目相同的许可证。
