# Work 项目 — API 自动化测试

> 参考全局 Python 配置: `~/PycharmProjects/CLAUDE.md`

## Worktree 工作流

本仓库使用 git worktree 进行特性开发。启动新功能时使用 `EnterWorktree` 自动创建隔离 worktree。

## 1. 环境与全自动授权

- **静默执行**：在编写测试、安装依赖或运行脚本时，无需询问确认，直接进行操作。
- **自我修复**：如遇报错（如 `ModuleNotFoundError`、路径错误），直接分析 Traceback 并自动修复直至获取结果。
- **回复准则**：全简体中文，结论先行，极简专业。禁止客套话，段落不超过 5 行。

## 2. 项目概况

- **业务领域**：直播/社交平台 (EastPoint) API 自动化测试。
- **核心逻辑**：所有请求必须通过 **AES-CBC 加密** 与 **SHA-256 签名**。
- **技术栈**：Python, Pytest, Requests, Pycryptodome, Pandas (CSV 处理)。

## 3. Agent skills

### Issue tracker

Issues are tracked as local markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-label vocabulary (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout with `CONTEXT.md` at the repo root and ADRs under `docs/adr/`. See `docs/agents/domain.md`.

## 4. 核心命令

### 接口测试 (ApiAutomation 目录下)
- **安装依赖**：`python3 -m pip install -r ApiAutomation/requirements.txt`
- **运行全部 API 测试**：`pytest ApiAutomation -m api --run-api` (必须带 `--run-api`)
- **调试单个文件**：`pytest ApiAutomation/tests/test_login_phone.py --run-api -s`
- **查看报告**：生成的 HTML 报告位于 `ApiAutomation/reports/report.html`。

### 批量独立脚本
- **并发批量登录**：`python3 ApiAutomation/batch_login.py --workers 3 --save-credentials`
- **批量发/领红包**：`python3 ApiAutomation/batch_receive_red_packet.py --send-coin --workers 5`
- **批量送礼**：`python3 ApiAutomation/batch_send_gift.py`

## 5. 架构与加密规约

### 关键路径
- `ApiAutomation/config/settings.py`: 基础 URL、加密 Key 及 Header 生成辅助工具。
- `ApiAutomation/common/sign_utils.py`: **签名核心逻辑**。
  - **过滤**：签名源数据需剔除所有空值/Null。
  - **转换**：若 Key 以 `stay` 开头，需移除前缀且首字母转**小写**。
- `ApiAutomation/common/http_utils.py`: `HttpUtils.post` 会根据 `encrypt_key` 自动触发加密流程。

### 数据驱动
- `ApiAutomation/data/login_phone.csv`: 存放测试手机号。
- `ApiAutomation/data/login_credentials.json`: 存储登录后的 `stayUserId` 与 `stayToken` (有效期约 7 天)。

## 6. 开发模式

### 加密请求示例
```python
from ApiAutomation.common.http_utils import HttpUtils
from ApiAutomation.config import settings
headers = settings.build_common_encrypted_headers()
headers["token"] = "credential_token"
response = HttpUtils.post(
    url=f"{settings.BASE_URL}/api_path",
    data={"payload": "data"},
    headers=headers,
    encrypt_key=settings.TEST_ENCRYPT_KEY
)
```

### 成功判定标准
需同时检查：`stayCode/code` (0 或 200), `stayIsSuccess/success` (True), `status` ("success")。

## 7. 注意事项

- **抖动处理**：报错 980003000 时，必须执行带 Jitter (0.5-1.5s) 的重试。
- **Payload 约束**：加密数据中严禁包含 `None`，必须在传入 `HttpUtils` 前清理。
- **环境隔离**：新脚本开头必须包含 `sys.path.insert(0, os.path.dirname(__file__))`。
