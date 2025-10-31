# Unity MCP 多实例支持 - 实现总结

## 📋 项目概述

成功为 Unity MCP 插件实现了多实例支持功能，现在可以同时控制多个 Unity Editor 实例，并执行跨项目操作。

## ✅ 完成的工作

### Phase 1: 核心基础设施 ✅

**1.1 创建 UnityInstanceInfo 数据类** (`Server/models.py`)
- 定义了统一的实例信息数据结构
- 包含 id、name、path、hash、port、status、last_heartbeat、unity_version 字段

**1.2 实现 discover_all_unity_instances()** (`Server/port_discovery.py`)
- 扫描 `~/.unity-mcp/` 目录下的所有状态文件
- 从项目路径提取项目名称
- 探测端口响应状态
- 修复了帧格式协议的实现（关键修复）

**1.3 实现 UnityConnectionPool 类** (`Server/unity_connection.py`)
- 管理多个 Unity 实例的连接
- 5秒缓存机制避免频繁扫描
- 智能实例匹配算法（名称 → 名称@哈希 → 哈希 → 路径 → 端口）
- 支持从环境变量读取默认实例配置
- 处理重名项目的情况

**1.4 更新 server.py 使用连接池**
- 替换单一连接为连接池
- 启动时自动发现所有实例
- 记录发现的实例数量

### Phase 2: 工具层适配 ✅

**2.1 创建 list_unity_instances 工具** (`Server/tools/list_unity_instances.py`)
- 列出所有运行的 Unity Editor 实例
- 返回详细的实例信息（名称、路径、端口、版本等）
- 支持 force_refresh 参数强制刷新
- 检测并警告重名项目

**2.2-2.6 更新所有工具添加 unity_instance 参数**

为以下 13 个工具添加了 `unity_instance` 可选参数：
- ✅ manage_scene.py
- ✅ manage_asset.py
- ✅ manage_gameobject.py
- ✅ manage_script.py
- ✅ manage_editor.py
- ✅ manage_shader.py
- ✅ read_console.py
- ✅ execute_menu_item.py
- ✅ manage_prefabs.py
- ✅ script_apply_edits.py（6个调用点）
- ✅ run_tests.py
- ✅ resource_tools.py (list_resources, read_resource, find_in_file)

### Phase 3: Unity端改进 ✅

**3.1 在心跳文件中添加项目名称和Unity版本** (`MCPForUnity/Editor/MCPForUnityBridge.cs`)
- 从 Application.dataPath 提取项目名称
- 添加 project_name 字段到心跳负载
- 添加 unity_version 字段（Application.unityVersion）
- 位置：MCPForUnityBridge.cs:1203-1236

**3.2 Stop() 时删除状态文件** (`MCPForUnity/Editor/MCPForUnityBridge.cs`)
- Unity Editor 关闭时自动清理状态文件
- 避免遗留过期的状态文件
- 包含错误处理和调试日志
- 位置：MCPForUnityBridge.cs:492-506

### Phase 4: 配置和文档 ✅

**4.1 添加环境变量支持**
- 支持 `UNITY_MCP_DEFAULT_INSTANCE` 环境变量
- 在 UnityConnectionPool 初始化时读取
- 可以指定项目名称、哈希值或完整标识符

**4.2 添加命令行参数支持** (`Server/server.py`)
- 实现 `--default-instance` 命令行参数
- 优先级高于环境变量
- 包含完整的帮助文档和示例
- 位置：server.py:203-235

**4.3 更新文档**
- ✅ MULTI_INSTANCE_GUIDE.md（中文完整指南）
- ✅ MULTI_INSTANCE_GUIDE_EN.md（英文完整指南）
- 包含快速开始、使用示例、故障排除、架构说明等

### 修复和优化 ✅

**修复1: 帧格式协议的端口探测**
- **问题**: 诊断工具直接发送 `b"ping"` 而不是帧格式
- **修复**: 实现完整的帧格式协议
  1. 接收握手 (检查 FRAMING=1)
  2. 发送帧格式命令 ([8字节长度] + 负载)
  3. 接收帧格式响应 ([8字节长度] + 负载)
- **影响文件**:
  - diagnose_instances.py
  - cleanup_stale_instances.py
  - Server/port_discovery.py

**修复2: Unity 端口冲突问题 (SO_REUSEADDR)**
- **问题**: macOS/Linux 上 SO_REUSEADDR 允许多个进程绑定同一端口
- **修复1**: PortManager.GetPortWithFallback() 主动查找新端口
  - 位置：PortManager.cs:63-67
  - 当存储的端口被占用时，查找并保存新端口
- **修复2**: MCPForUnityBridge 重试逻辑增强
  - 位置：MCPForUnityBridge.cs:365-403
  - 添加安全检查确保获取不同端口
  - 防止死循环

**更新诊断和清理脚本**
- diagnose_instances.py - 诊断所有实例状态
- cleanup_stale_instances.py - 清理过期状态文件

## 📊 技术实现细节

### 实例识别策略

优先级顺序：
1. 完整 ID (`"ProjectName@a1b2c3d4"`)
2. 项目名称（唯一时）
3. 哈希值（前8位）
4. 端口号
5. 完整项目路径

### 端口分配逻辑

| Unity 实例 | 端口分配 |
|-----------|---------|
| 第一个 | 6400（默认端口） |
| 第二个 | 6401（如果6400被占用） |
| 第三个 | 6402（如果6401被占用） |

### 连接池缓存机制

- **缓存时间**: 5秒
- **刷新触发**:
  - 缓存过期后自动刷新
  - 调用 list_unity_instances(force_refresh=True)
- **连接复用**: 每个实例保持一个持久连接

### 状态文件格式

```json
{
  "unity_port": 6400,
  "project_path": "/path/to/project/Assets",
  "project_name": "MyProject",
  "unity_version": "2022.3.10f1",
  "last_heartbeat": "2025-10-31T12:34:56.789Z",
  "reloading": false,
  "reason": "ready",
  "seq": 42
}
```

## 🎯 使用示例

### 1. 列出所有实例
```python
list_unity_instances()
```

### 2. 指定实例执行操作
```python
# 使用项目名称
manage_scene(action="get_active", unity_instance="MyGame")

# 使用完整标识符
manage_scene(action="get_active", unity_instance="MyGame@a1b2c3d4")
```

### 3. 跨项目操作
```python
# 从 ProjectA 读取
asset = read_resource(path="Assets/Prefabs/Player.prefab", unity_instance="ProjectA")

# 写入 ProjectB
manage_asset(action="create", path="Assets/Player.prefab", content=asset, unity_instance="ProjectB")
```

### 4. 配置默认实例
```bash
# 环境变量
export UNITY_MCP_DEFAULT_INSTANCE="MyGame"
python -m src.server

# 命令行参数
python -m src.server --default-instance "MyGame"
```

## 🔍 测试验证

### 测试场景
1. ✅ 单实例启动和发现
2. ✅ 多实例同时运行
3. ✅ 端口自动分配（6400, 6401, 6402）
4. ✅ 端口冲突检测和解决
5. ✅ 跨项目操作
6. ✅ 重名项目处理
7. ✅ 状态文件清理

### 诊断工具
```bash
# 检查所有实例状态
python3 diagnose_instances.py

# 清理过期实例
python3 cleanup_stale_instances.py
```

## 📦 修改的文件列表

### Python 服务器端（13个文件）
- Server/models.py
- Server/port_discovery.py
- Server/unity_connection.py
- Server/server.py
- Server/tools/list_unity_instances.py（新增）
- Server/tools/manage_scene.py
- Server/tools/manage_asset.py
- Server/tools/manage_gameobject.py
- Server/tools/manage_script.py
- Server/tools/manage_editor.py
- Server/tools/manage_shader.py
- Server/tools/read_console.py
- Server/tools/execute_menu_item.py
- Server/tools/manage_prefabs.py
- Server/tools/script_apply_edits.py
- Server/tools/run_tests.py
- Server/tools/resource_tools.py

### Unity C# 端（2个文件）
- MCPForUnity/Editor/Helpers/PortManager.cs
- MCPForUnity/Editor/MCPForUnityBridge.cs

### 诊断工具（2个文件）
- diagnose_instances.py
- cleanup_stale_instances.py

### 文档（5个文件）
- MULTI_INSTANCE_GUIDE.md（新增）
- MULTI_INSTANCE_GUIDE_EN.md（新增）
- MULTI_INSTANCE_FIX.md（已存在）
- PORT_CONFLICT_FIX.md（已存在）
- MULTI_INSTANCE_IMPLEMENTATION_SUMMARY.md（本文件）

## 💡 关键技术决策

### 1. 连接池 vs 即时连接
- **选择**: 连接池 + 5秒缓存
- **理由**:
  - 避免频繁扫描状态文件
  - 保持连接复用提高性能
  - 5秒足够快速适应新实例

### 2. 实例标识符设计
- **选择**: 支持多种标识符格式
- **理由**:
  - 项目名称最直观（适合唯一名称场景）
  - 完整标识符避免歧义（适合重名场景）
  - 哈希/端口提供备选方案

### 3. 默认实例策略
- **选择**: 环境变量 + 命令行参数（不用配置文件）
- **理由**:
  - 环境变量易于设置
  - 命令行参数灵活覆盖
  - 配置文件增加复杂度，用处不大

### 4. 状态文件清理时机
- **选择**: Unity Stop() 时删除
- **理由**:
  - 及时清理避免混淆
  - 失败时仍可通过清理脚本处理
  - 不影响域重载场景

## 🚀 性能优化

### 实例发现优化
- 缓存机制避免频繁文件扫描
- 并发端口探测（如需要）
- 快速失败策略（超时1秒）

### 连接管理优化
- 持久连接减少握手开销
- 连接复用提高响应速度
- 延迟清理避免抖动

## 🔐 安全考虑

### 端口冲突防护
- 主动检测端口占用
- 自动递增查找可用端口
- 防止端口重复绑定

### 文件系统安全
- 状态文件在用户主目录
- 哈希文件名避免冲突
- 清理时验证文件所有权

## 📈 后续改进空间

### 可选增强功能
1. 实例分组管理（如按Unity版本分组）
2. 实例优先级配置
3. 连接池连接数限制
4. 更细粒度的缓存控制
5. WebSocket 支持（实时状态推送）
6. 图形化实例管理界面

### 已知限制
1. 依赖文件系统状态文件（不适合分布式场景）
2. 端口范围有限（6400-6499）
3. 项目名称重复需要额外处理

## ✨ 总结

成功实现了 Unity MCP 的多实例支持功能，包括：
- ✅ 完整的连接池架构
- ✅ 所有工具的多实例支持
- ✅ 端口冲突自动解决
- ✅ 智能实例识别
- ✅ 灵活的配置选项
- ✅ 完善的文档和诊断工具

该实现使 Unity MCP 能够同时管理多个 Unity 项目，为 AI 辅助开发工作流提供了更强大的跨项目操作能力。

---

**实现日期**: 2025-10-31
**版本**: v1.0
**状态**: ✅ 全部完成
