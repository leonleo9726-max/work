# API Automation

本项目提供离线可验证的请求构造、响应解析、凭证存储、HTTP transport 和批处理执行 module；真实接口测试默认关闭。

## 环境

- Python 3.11
- 安装运行依赖：`python -m pip install -r requirements.txt`
- 安装开发依赖：`python -m pip install -r requirements-dev.txt`
- uv 锁定安装：`uv sync --locked --group dev`

复制 `.env.example` 中的变量到自己的 shell 或凭证管理工具。项目不会自动加载 `.env`，也不会把密钥写入仓库。

## 本地数据

将 `data/examples/` 中需要的模板复制到 `data/local/`，再替换为自己的本地数据。`data/local/` 已被 Git 忽略。

## 验证

```bash
uv run --locked pytest
uv run --locked ruff check .
```

默认 `pytest` 会跳过所有 `api` 测试。执行真实接口前需要同时提供环境变量和显式授权：

```bash
export API_AUTOMATION_ENCRYPT_KEY='...'
export API_TEST_PHONE='...'
pytest -m api --run-api
```

需要 HTML 报告时显式生成：

```bash
pytest --html=reports/report.html --self-contained-html
```

批处理命令及参数可通过 `python batch_login.py --help` 等命令查看。
