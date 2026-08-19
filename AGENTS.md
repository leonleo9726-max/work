# EastPoint API 自动化测试

## 1. 范围与授权

- 以用户当前请求、已提交代码和现有测试为行为与范围依据；需求无法从这些来源确定时，先说明缺口。
- Python 使用 `E:\python\work\.venv\Scripts\python.exe`。编写测试、安装依赖、运行本地脚本和修复本地环境可直接执行。
- 真实 API 调用必须显式携带 `--run-api`；提交、推送、建分支、创建 PR 和其他外部写操作仅在用户明确要求后执行。
- 回复使用简体中文，结论优先，说明已运行的验证和未运行的高风险检查。

## 2. 项目规约

- 业务领域：直播/社交平台 API 自动化测试，技术栈为 Python、pytest、requests、cryptography 与 Pandas。
- 所有业务请求使用 AES-CBC 加密与 SHA-256 签名。`config/settings.py` 从环境变量读取 `EASTPOINT_BASE_URL` 与 `EASTPOINT_TEST_ENCRYPT_KEY`；密钥缺失时不得降级为明文请求。
- `common/sign_utils.py` 负责过滤空值、`stay*` 键转换、签名和加密；`common/http_utils.py` 负责传输与 `980003000` 的 0.5-1.5 秒抖动重试。
- 业务调用优先使用 `common.api_client.EastPointClient`，测试与批量脚本只声明业务路径、载荷和凭证。
- `data/login_credentials.json` 与 `data/batch_login_credentials.json` 只保存本地运行凭证，已被 Git 忽略；不得重新加入版本控制。

## 3. 常用命令

在 `ApiAutomation` 目录执行：

- 安装依赖：`${PYTHON_EXE} -m pip install -r requirements.txt`
- 离线单元测试：`${PYTHON_EXE} -m pytest -m unit -p no:cacheprovider -o addopts=''`
- 全部真实接口测试：`pytest -m api --run-api`
- 单文件调试：`pytest tests/test_login_phone.py --run-api -s`
- 批量登录：`${PYTHON_EXE} batch_login.py --workers 3 --save-credentials`
- 批量发/领红包：`${PYTHON_EXE} batch_receive_red_packet.py --send-coin --workers 5`

## 4. 请求与断言

```python
from common.api_client import EastPointClient
from config import settings

client = EastPointClient(settings.TEST_ENCRYPT_KEY)
response = client.post("/api_path", {"payload": "data"}, token="credential_token")
```

- 业务载荷不应包含 `None`；传输层会再次过滤空值。
- 使用 `common.response_utils.is_api_success()` 判定成功。响应中出现的 `code/stayCode`、`success/stayIsSuccess` 和 `status` 指标必须全部一致为成功；不同接口可以只返回其中一类指标。
- 新的独立脚本开头包含 `sys.path.insert(0, os.path.dirname(__file__))`。
- 不使用 `common/excel_utils.py`。

## 5. 工程工作流

### 路由

- **评审**：有提交、分支、PR 或比较点时使用 `code-review`。
- **诊断**：报错、失败、异常行为或性能回退时，先使用 `diagnosing-bugs`；仅要求诊断时不改代码。
- **设计**：新增功能、模块边界、公共接口或可测试性调整时使用 `codebase-design`；术语不清时使用 `domain-modeling`。
- **测试**：用户要求测试先行、红绿重构或集成测试时使用 `tdd`；其他修改按风险补充测试。
- **调研**：需要外部技术事实、官方文档或方案比较时使用 `research`。
- **冲突**：进行中的 merge 或 rebase 冲突使用 `resolving-merge-conflicts`。
- **GitHub**：仓库、PR、Issue 使用 `github:github`；审查意见使用 `github:gh-address-comments`；Actions 失败使用 `github:gh-fix-ci`；发布使用 `github:yeet`。

### 变更闭环

1. 检查受影响代码、工作区状态和现有测试。
2. 以最小范围实现用户明确要求的行为。
3. 运行聚焦且无破坏性的验证；共享行为变更时运行完整相关测试集。
4. 报告改动、验证结果和仍需用户完成的外部操作。

### Git 边界

- 保留已有用户改动，不还原或覆盖无关文件。
- 删除前确认准确目标；完成后说明删除内容和可恢复性。
- 只在用户明确要求时提交、推送、创建分支或 PR。
