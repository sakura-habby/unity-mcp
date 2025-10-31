# 多实例问题诊断与修复

## 🐛 问题根源

### 发现的问题
用户发现即使指定不同的 `unity_instance` 参数，所有请求都路由到同一个Unity实例。

### 根本原因
诊断工具和 `port_discovery.py` 中的端口探测函数**没有正确实现 Unity 的帧格式协议**。

## 📡 Unity 的帧格式协议

Unity MCP Bridge 使用严格的帧格式协议 (Framed Protocol)：

### 连接流程
```
1. 客户端连接到 Unity 的 TCP 端口
   ↓
2. Unity 发送握手消息
   "WELCOME UNITY-MCP 1 FRAMING=1\n"
   ↓
3. 客户端发送带帧格式的命令
   [8字节长度头] + [命令负载]
   ↓
4. Unity 返回带帧格式的响应
   [8字节长度头] + [响应负载]
```

### 帧格式
```python
# 发送
payload = b"ping"
header = struct.pack('>Q', len(payload))  # 大端序 uint64
socket.sendall(header + payload)

# 接收
header = socket.recv(8)
length = struct.unpack('>Q', header)[0]
response = socket.recv(length)
```

## ❌ 错误的实现

### 之前的探测代码（错误）
```python
def check_port(port):
    with socket.create_connection(("127.0.0.1", port), timeout=0.5) as s:
        s.sendall(b"ping")  # ❌ 直接发送，没有帧头
        data = s.recv(512)
        return b'"message":"pong"' in data
```

**问题**：Unity 期望接收 `[8字节长度] + "ping"`，但收到的是直接的 `"ping"`，无法解析。

## ✅ 正确的实现

### 修复后的探测代码
```python
def check_port(port):
    with socket.create_connection(("127.0.0.1", port), timeout=1.0) as s:
        # 1. 接收握手
        handshake = s.recv(512)
        if b"FRAMING=1" not in handshake:
            return False

        # 2. 发送帧格式的 ping
        payload = b"ping"
        header = struct.pack('>Q', len(payload))
        s.sendall(header + payload)

        # 3. 接收帧格式的响应
        response_header = s.recv(8)
        response_length = struct.unpack('>Q', response_header)[0]
        response = s.recv(response_length)

        return b'"message":"pong"' in response
```

## 🔧 已修复的文件

1. **diagnose_instances.py** - 诊断脚本
2. **cleanup_stale_instances.py** - 清理脚本
3. **Server/port_discovery.py** - 端口发现模块

## 🧪 测试步骤

### 1. 清理旧的状态文件
```bash
cd ~/work/unity-mcp
python3 cleanup_stale_instances.py
```

### 2. 启动第一个 Unity 项目
打开 Unity Editor，等待完全启动。

### 3. 验证单实例
```bash
python3 diagnose_instances.py
```

应该看到：
```
Port Responding: ✅ YES
Ports actually responding: 1 - [6400]
```

### 4. 启动第二个 Unity 项目
打开另一个 Unity Editor（不同项目）。

### 5. 验证多实例
```bash
python3 diagnose_instances.py
```

应该看到：
```
Found 2 status files
Unique ports in files: 2 - [6400, 6401]
Ports actually responding: 2 - [6400, 6401]
```

### 6. 测试连接池
```bash
python3 test_connection_pool.py
```

应该显示不同实例使用不同的连接和端口。

## 💡 为什么之前 MCP Server 能工作？

Python MCP Server 的 `unity_connection.py` **正确实现了帧格式协议**：

```python
# unity_connection.py:288-291
if self.use_framing:
    header = struct.pack('>Q', len(payload))
    self.sock.sendall(header)
    self.sock.sendall(payload)
```

所以：
- ✅ MCP Server 与 Unity 的通信正常
- ❌ 诊断工具的端口探测失败
- ❌ 导致误判所有实例使用同一端口

## 🎯 预期结果

修复后，当启动多个 Unity Editor 时：

1. **每个 Unity 会分配不同端口**
   - 第一个：6400
   - 第二个：6401（如果6400被占用）
   - 第三个：6402（如果6401被占用）

2. **诊断工具能正确检测**
   ```bash
   python3 diagnose_instances.py
   # 显示所有实例和正确的端口状态
   ```

3. **MCP 工具能路由到不同实例**
   ```python
   # 操作 ProjectA
   manage_scene(action="get_active", unity_instance="ProjectA")

   # 操作 ProjectB
   manage_scene(action="get_active", unity_instance="ProjectB")
   ```

## 🔍 调试提示

如果仍然有问题：

1. **检查 Unity Console**
   看是否有端口冲突或 MCP Bridge 错误

2. **检查实际监听的端口**
   ```bash
   lsof -i :6400
   lsof -i :6401
   ```

3. **查看 MCP Server 日志**
   确保连接池正在创建不同的连接

4. **验证帧格式握手**
   ```bash
   nc 127.0.0.1 6400
   # 应该立即收到: WELCOME UNITY-MCP 1 FRAMING=1
   ```

## ✅ 总结

- **问题**：端口探测未实现帧格式协议
- **影响**：诊断工具误报，但实际功能正常
- **修复**：所有探测代码都正确实现帧格式协议
- **验证**：重新测试多实例功能
