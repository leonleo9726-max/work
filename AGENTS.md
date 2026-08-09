# API 自动化仓库指南

## 目标

只做满足请求所需的最小正确变更，同时保持现有 API 测试架构和真实服务安全边界。

## 仓库概况

- 领域：EastPoint 直播/社交平台 API 自动化。
- 运行环境：Python。
- 主要工具：Python 3.11、Pytest、Requests、Cryptography、pytest-html 和 Ruff。
- 依赖入口：`ApiAutomation/pyproject.toml`；兼容安装文件为 `requirements*.txt`。
- 当前仓库使用 uv 管理锁定环境，并使用 Ruff 做静态检查；未使用 FastAPI 或 Pydantic，不要假设或引入未配置的框架。

## 目录结构

- `ApiAutomation/conftest.py`：pytest 选项和共享 fixture。
- `ApiAutomation/pytest.ini`：测试发现规则和 HTML 报告设置。
- `ApiAutomation/common/`：HTTP、签名、认证、响应和业务辅助模块。
- `ApiAutomation/config/settings.py`：URL、路径、加密设置和请求头构建的集中配置。
- `ApiAutomation/tests/`：API 测试套件。
- `ApiAutomation/data/examples/`：可提交的脱敏模板；真实输入和凭证只放在被忽略的 `data/local/`。
- `ApiAutomation/reports/`：生成的测试报告，不作为源文件处理。
- `plans/` 和 `docs/`：规划、Agent 与领域文档。

优先扩展现有辅助模块，不创建功能重复的工具模块。已有合适的 `common/` 模块时，将可复用的请求行为保留在其中，不要散落到单个测试里。

## 工作方式

编辑前：

- 阅读受影响的实现、测试、fixture 和配置。
- 遵循现有导入与执行约定。
- 在已有支持范围内，同时保持从仓库根目录和 `ApiAutomation` 目录运行的兼容性。

保持变更集中。处理局部任务时，不重组包结构、不统一全部导入，也不顺带现代化无关代码。

## 加密与签名约束

- 加密请求尽量通过 `common/http_utils.py` 发送。
- `common/sign_utils.py` 包含安全敏感的签名和 AES-CBC 行为。
- 生成签名前，按现有签名流程要求移除 null/空值。
- 保持以 `stay` 开头字段的现有转换规则：移除前缀，并将余下名称的首字母转为小写。
- 保持必需的 `locale`、`timestamp` 和 `sign` 请求头。
- 修改加密密钥、签名规则、请求路径或成功判定逻辑前，必须有针对性测试并明确说明原因。

## 测试与真实 API 安全

除非命令另有说明，从 `Python/work` 目录运行：

- 锁定安装：在 `ApiAutomation` 目录运行 `uv sync --locked --group dev`
- 兼容安装：`python3 -m pip install -r ApiAutomation/requirements-dev.txt`
- 安全的本地收集/默认运行：`pytest ApiAutomation`
- 真实 API 测试：`pytest ApiAutomation -m api --run-api`
- 静态检查：在 `ApiAutomation` 目录运行 `uv run --locked ruff check .`

规则：

- 只有用户明确要求或授权真实外部调用后，才能使用 `--run-api` 运行测试。
- `api` marker 与 `--run-api` collection 门禁是唯一真实请求 seam；新增真实测试必须标记 `api`。
- 先运行范围最小的相关测试。
- 只有测试实际成功完成后才能声称通过。
- 未运行真实 API 测试时必须明确说明；不能把仅完成收集或全部跳过描述为端到端验证。
- 保持现有测试使用的确定性种子和 CSV 列契约。

## 数据与密钥

- 手机号、用户 ID、令牌、设备 ID、加密密钥和生成的凭证 JSON 均按敏感数据处理。
- 不打印、不写入报告、不提交，也不在回复中暴露敏感值。
- 未经明确要求，不替换类生产数据文件，也不修改账户余额、Redis 数据或其他外部状态。
- 使用 fixture 和集中配置，避免在测试中硬编码 URL、凭证、请求头或密钥。
- 不静默关闭 TLS 校验、身份认证、权限控制或响应校验。

## Python 风格

- 遵循所在模块的现有风格。
- 优先使用显式、可读的函数、描述性命名、提前返回、上下文管理器和 f-string。
- 避免全局可变状态、通配符导入、吞掉宽泛异常、重复请求逻辑和不必要的抽象。
- 类型标注有助于理解变更时可以添加，但不要为无关任务进行全仓库类型清理。
- 默认不新增 `sys.path` 操作；除非任务就是重构导入，否则保持现有兼容性。
- 不在未说明原因的情况下抑制警告或异常。

## 依赖与工具链

- 除非任务确有需要，不安装或修改依赖。
- 只有依赖行为变化时才更新 `requirements.txt`。
- 不为仓库尚未配置的工具虚构验证命令。
- 修改依赖后同步更新 `pyproject.toml` 与兼容的 `requirements*.txt`。

## Git 与生成文件

- 未经明确要求，不提交、推送、创建分支/worktree 或改写历史。
- 不把生成的报告、缓存、字节码或本地凭证产物当作源文件编辑。
- 保留工作区中与当前任务无关的用户变更。

## Agent skills

### Issue tracker

发布或管理 issue、spec 和 ticket 前，先阅读 `docs/agents/issue-tracker.md`，并使用其中约定的 GitHub Issues 工作流。

### Triage labels

分类或改变 issue 状态前，先阅读 `docs/agents/triage-labels.md`，并使用其中五个 Matt Pocock 标准标签。

### Domain docs

进行领域建模、架构工作或依赖历史设计决策的变更前，先阅读 `docs/agents/domain.md`。本仓库采用单一上下文领域文档布局。

## 完成标准

回复完成前：

- 检查差异中不存在意外变更或敏感信息。
- 运行相关的安全测试，或说明未运行的原因。
- 移除临时诊断和调试代码。
- 汇总改动内容、变更文件、验证结果及仍然存在的真实环境风险。
