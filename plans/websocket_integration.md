# WebSocket 集成计划

## 目标
在现有 API 自动化测试框架中集成 WebSocket 测试能力，模拟用户进房场景，复用登录接口的 token 和 userid。

## 项目结构调整

### 新增文件
```
ApiAutomation/
├── common/
│   ├── websocket_utils.py   # WebSocket 工具类
├── config/
│   └── settings.py          # 添加 WEBSOCKET_URL 配置
├── tests/
│   └── test_websocket_room.py # WebSocket 进房测试用例
└── requirements.txt         # 添加 websocket-client 依赖
```

### 配置变更
在 `config/settings.py` 中添加：
```python
WEBSOCKET_URL = "wss://api.eastpointtest.com/ws"  # 示例，根据实际调整
WEBSOCKET_ROOM_PATH = "/room/join"
```

### 依赖更新
在 `requirements.txt` 中添加：
```
websocket-client==1.6.0
```

## 详细设计

### 1. WebSocket 工具类 (`common/websocket_utils.py`)
提供同步 WebSocket 客户端操作，支持认证头传递。

```python
import json
import logging
from websocket import WebSocket

class WebSocketUtils:
    """WebSocket 工具类"""
    
    @staticmethod
    def connect(url, headers=None, timeout=10):
        """建立 WebSocket 连接"""
        ws = WebSocket()
        if headers:
            # 将 headers 转换为合适的格式（例如作为查询参数或协议头）
            # 这里根据实际服务端要求实现
            pass
        ws.connect(url, timeout=timeout)
        return ws
    
    @staticmethod
    def send(ws, message):
        """发送消息（支持 dict 或 str）"""
        if isinstance(message, dict):
            message = json.dumps(message)
        ws.send(message)
    
    @staticmethod
    def receive(ws, timeout=5):
        """接收消息，返回解析后的 dict 或原始文本"""
        result = ws.recv()
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return result
    
    @staticmethod
    def close(ws):
        """关闭连接"""
        ws.close()
```

### 2. 认证集成
复用登录接口返回的 `stayToken` 和 `stayUserId`，通过以下方式传递：
- 作为查询参数：`wss://.../ws?token=xxx&userId=xxx`
- 作为协议头：`Sec-WebSocket-Protocol: token, userId`
- 作为首次握手后的认证消息

具体方式需根据服务端实现调整。

### 3. 测试用例 (`tests/test_websocket_room.py`)
```python
import pytest
from common.websocket_utils import WebSocketUtils
from config import settings
from tests.test_login_phone import ensure_login_credentials

@pytest.mark.api
@pytest.mark.websocket
def test_user_join_room(request, encrypt_key):
    """模拟用户进房"""
    if not request.config.getoption("--run-api"):
        pytest.skip("need --run-api option to execute real API tests")
    
    # 1. 获取登录凭证
    phone = "15200711073"
    credential = ensure_login_credentials(phone, encrypt_key)
    token = credential["stayToken"]
    user_id = credential["stayUserId"]
    
    # 2. 构建 WebSocket URL（带认证参数）
    ws_url = f"{settings.WEBSOCKET_URL}{settings.WEBSOCKET_ROOM_PATH}?token={token}&userId={user_id}"
    
    # 3. 建立连接
    ws = WebSocketUtils.connect(ws_url)
    
    try:
        # 4. 发送进房消息
        join_msg = {
            "type": "join",
            "roomId": "test_room_001",
            "userId": user_id
        }
        WebSocketUtils.send(ws, join_msg)
        
        # 5. 接收服务端响应
        response = WebSocketUtils.receive(ws, timeout=5)
        assert response.get("type") == "joined"
        assert response.get("roomId") == "test_room_001"
        
        # 6. 可选的额外验证
        # ...
    finally:
        WebSocketUtils.close(ws)
```

### 4. 测试夹具扩展
在 `conftest.py` 中添加 WebSocket 夹具：

```python
@pytest.fixture(scope="function")
def websocket_client():
    """提供 WebSocket 客户端实例"""
    from common.websocket_utils import WebSocketUtils
    client = None
    yield client
    if client:
        client.close()
```

## 实施步骤

1. **更新配置**：在 `config/settings.py` 中添加 WebSocket 相关配置项
2. **安装依赖**：执行 `pip install websocket-client`
3. **创建工具类**：编写 `common/websocket_utils.py`
4. **编写测试用例**：创建 `tests/test_websocket_room.py`
5. **验证集成**：运行测试确保 WebSocket 连接正常
6. **文档更新**：在 README 中添加 WebSocket 测试说明

## 注意事项
- WebSocket 服务端地址需根据实际环境配置
- 认证方式需与服务端协商（查询参数、协议头或自定义握手）
- 考虑连接超时、重连机制和错误处理
- 测试数据清理：确保测试后断开连接

## 后续扩展
- 支持多个用户同时进房测试
- 添加消息订阅/发布模式测试
- 集成异步 WebSocket 客户端（如 `websockets` 库）
- 添加性能测试和负载测试