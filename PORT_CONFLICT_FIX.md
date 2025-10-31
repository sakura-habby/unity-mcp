# Unity 端口冲突问题修复

## 🐛 问题描述

### 用户报告的现象
当同时启动两个 Unity Editor 实例时：
- 两个实例的状态文件都显示端口 6400
- 但只有一个实例实际在响应
- MCP 工具无法正确路由到不同的实例

### 根本原因

1. **SO_REUSEADDR 的副作用**
   ```csharp
   listener.Server.SetSocketOption(
       SocketOptionLevel.Socket,
       SocketOptionName.ReuseAddress,
       true  // 在 macOS/Linux 上允许多个进程绑定同一端口！
   );
   ```

   在 macOS 和 Linux 上，`SO_REUSEADDR` 允许多个进程"成功"绑定到同一个端口，但实际上只有第一个进程真正监听。

2. **端口分配逻辑的缺陷**

   **PortManager.cs:64** (修复前):
   ```csharp
   // Prefer sticking to the same port; let the caller handle bind retries/fallbacks
   return storedConfig.unity_port;  // ❌ 即使端口被占用也返回！
   ```

   问题：当第二个 Unity 启动时，即使检测到 6400 被占用，也会返回 6400，期望调用者处理冲突。

3. **重试逻辑的问题**

   **MCPForUnityBridge.cs:365** (修复前):
   ```csharp
   catch (SocketException se) when (se.SocketErrorCode == SocketError.AddressAlreadyInUse)
   {
       currentUnityPort = PortManager.GetPortWithFallback();  // 又返回6400！
       listener = new TcpListener(IPAddress.Loopback, currentUnityPort);
       listener.Start();  // 再次失败
   }
   ```

## ✅ 修复方案

### 修复 1: PortManager.GetPortWithFallback()

**文件**: `MCPForUnity/Editor/Helpers/PortManager.cs:63-67`

**修改前**:
```csharp
// Prefer sticking to the same port; let the caller handle bind retries/fallbacks
return storedConfig.unity_port;
```

**修改后**:
```csharp
// Port is still busy after waiting - find a new available port instead
if (IsDebugEnabled()) Debug.Log($"Stored port {storedConfig.unity_port} is occupied by another instance, finding alternative...");
int newPort = FindAvailablePort();
SavePort(newPort);
return newPort;
```

**效果**: 当检测到存储的端口被占用时，主动查找并返回新的可用端口。

### 修复 2: MCPForUnityBridge 重试逻辑

**文件**: `MCPForUnity/Editor/MCPForUnityBridge.cs:365-403`

**修改前**:
```csharp
catch (SocketException se) when (se.SocketErrorCode == SocketError.AddressAlreadyInUse && attempt >= maxImmediateRetries)
{
    currentUnityPort = PortManager.GetPortWithFallback();
    listener = new TcpListener(IPAddress.Loopback, currentUnityPort);
    listener.Start();  // 可能再次失败
    break;
}
```

**修改后**:
```csharp
catch (SocketException se) when (se.SocketErrorCode == SocketError.AddressAlreadyInUse && attempt >= maxImmediateRetries)
{
    // Port is occupied by another instance, get a new available port
    int oldPort = currentUnityPort;
    currentUnityPort = PortManager.GetPortWithFallback();

    // Safety check: ensure we got a different port
    if (currentUnityPort == oldPort)
    {
        McpLog.Error($"Port {oldPort} is occupied and no alternative port available");
        throw;
    }

    if (IsDebugEnabled())
    {
        McpLog.Info($"Port {oldPort} occupied, switching to port {currentUnityPort}");
    }

    listener = new TcpListener(IPAddress.Loopback, currentUnityPort);
    // ... 重新绑定
}
```

**效果**:
- 确保获取到不同的端口
- 添加安全检查防止死循环
- 记录端口切换日志

## 🧪 测试步骤

### 1. 清理旧的状态文件
```bash
cd ~/work/unity-mcp
python3 cleanup_stale_instances.py
```

### 2. 关闭所有 Unity Editor
确保没有 Unity 进程在运行。

### 3. 打开第一个 Unity 项目
等待完全启动，检查 Unity Console 的 MCP 日志，应该显示：
```
MCPForUnityBridge started on port 6400.
```

### 4. 运行诊断
```bash
python3 diagnose_instances.py
```

应该显示：
```
[1] unity-mcp-status-xxxxx.json
  Project Name:    ProjectA
  Port:            6400
  Port Responding: ✅ YES

Summary:
  Unique ports in files:     1 - [6400]
  Ports actually responding: 1 - [6400]
```

### 5. 打开第二个 Unity 项目
等待完全启动，检查 Unity Console，应该显示：
```
Stored port 6400 is occupied by another instance, finding alternative...
Found available port 6401
MCPForUnityBridge started on port 6401.
```

或类似消息表明检测到端口冲突并自动切换。

### 6. 再次运行诊断
```bash
python3 diagnose_instances.py
```

应该显示：
```
[1] unity-mcp-status-xxxxx.json
  Project Name:    ProjectA
  Port:            6400
  Port Responding: ✅ YES

[2] unity-mcp-status-yyyyy.json
  Project Name:    ProjectB
  Port:            6401  # ← 不同的端口！
  Port Responding: ✅ YES

Summary:
  Unique ports in files:     2 - [6400, 6401]
  Ports actually responding: 2 - [6400, 6401]
```

### 7. 测试 MCP 工具路由
```python
# 应该能正确路由到不同实例
list_unity_instances()
# 返回: [
#   {"id": "ProjectA@hash1", "port": 6400, ...},
#   {"id": "ProjectB@hash2", "port": 6401, ...}
# ]

# 操作 ProjectA
manage_scene(action="get_active", unity_instance="ProjectA")  # → 6400

# 操作 ProjectB
manage_scene(action="get_active", unity_instance="ProjectB")  # → 6401
```

## 📊 预期结果

修复后，多个 Unity Editor 实例的端口分配应该是：

| Unity 实例 | 端口分配逻辑 |
|-----------|------------|
| 第一个 | 使用默认端口 6400 |
| 第二个 | 检测到 6400 被占用，使用 6401 |
| 第三个 | 检测到 6400、6401 被占用，使用 6402 |

每个实例：
- ✅ 使用不同的端口
- ✅ 状态文件正确反映实际端口
- ✅ MCP Server 能正确路由请求
- ✅ 跨项目操作正常工作

## 🔍 调试提示

如果仍然有问题，检查 Unity Console 的日志：

1. **端口冲突检测日志**:
   ```
   Stored port 6400 is occupied by another instance, finding alternative...
   ```

2. **端口分配成功日志**:
   ```
   MCPForUnityBridge started on port 6401.
   ```

3. **端口探测失败日志** (不应该出现):
   ```
   Port 6400 is occupied and no alternative port available
   ```

如果看到第3条日志，说明 6400-6409 所有端口都被占用了，需要检查系统端口占用情况。

## 📝 技术细节

### SO_REUSEADDR 的平台差异

| 平台 | SO_REUSEADDR 行为 |
|------|------------------|
| **macOS/Linux** | 允许多个进程绑定同一端口（TIME_WAIT 复用） |
| **Windows** | 只允许同一进程内复用（需要 ExclusiveAddressUse=false） |

这就是为什么问题主要在 macOS 上出现。

### 端口可用性检测

`IsPortAvailable()` 的实现:
```csharp
var testListener = new TcpListener(IPAddress.Loopback, port);
testListener.Start();  // 如果成功，说明端口可用
testListener.Stop();
```

这个方法在 macOS 上受 SO_REUSEADDR 影响，可能错误地报告端口"可用"，即使已被占用。

### 解决方案的权衡

我们保留了 SO_REUSEADDR，因为它对于 Unity 域重载场景很重要（避免 TIME_WAIT 导致的端口占用）。

同时在应用层添加了额外的冲突检测和端口切换逻辑，确保不同 Unity 实例使用不同端口。

## ✅ 总结

- **问题**: SO_REUSEADDR 导致多个 Unity 实例错误地绑定同一端口
- **修复**: 在 PortManager 和 MCPForUnityBridge 中添加真正的端口冲突处理
- **效果**: 多实例自动分配不同端口，MCP 工具能正确路由
- **测试**: 运行诊断脚本验证端口分配
