# 批处理命令指南

先按照 [README.md](README.md) 配置环境变量，并把脱敏模板复制到 `data/local/`。

## 登录

```bash
python batch_login.py --workers 3 --delay 1.5 --retry 2 --retry-delay 2.5 --jitter 0.3 --save-credentials
```

生成的凭证写入 `data/local/batch_login_credentials.json`，不会被 Git 跟踪。

## 注册、礼物和红包

每个命令的参数以 `--help` 为准：

```bash
python batch_register.py --help
python batch_send_gift.py --help
python batch_send_coin_red_packet.py --help
python batch_send_gift_red_packet.py --help
python batch_receive_red_packet.py --help
```

批处理脚本共用 `BatchRunner`，并发、初始延迟、重试退避和 jitter 都由相同 policy 控制。写操作不会在 HTTP transport 层隐式重试。
