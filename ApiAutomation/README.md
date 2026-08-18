# EastPoint API 自动化测试

真实接口测试使用 AES-CBC 加密和 SHA-256 签名；默认只执行离线断言，必须显式传入 `--run-api` 才会调用环境接口。

## 配置

复制 `.env.example` 的变量名到本机环境变量或 CI Secret。至少配置 `EASTPOINT_TEST_ENCRYPT_KEY`；未配置时，加密请求会失败，不会降级为明文请求。

```powershell
$env:EASTPOINT_TEST_ENCRYPT_KEY = "<测试环境密钥>"
E:\python\work\.venv\Scripts\python.exe -m pytest -m api --run-api
```

## 验证

```powershell
E:\python\work\.venv\Scripts\python.exe -m pytest -m unit -p no:cacheprovider -o addopts=''
```

`common.api_client.EastPointClient` 是领域请求的统一入口，负责 URL、认证请求头和加密传输；测试与批处理脚本应只构造业务载荷。
