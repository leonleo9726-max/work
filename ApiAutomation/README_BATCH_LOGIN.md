# 批量登录使用指南

## Vscode批量修改数据格式

把 ID 列表粘贴到 VS Code。
选中所有行（Ctrl + A），按下 Alt + Shift + I（在每行末尾出现光标）。
按 Home 回到行首，输入 user:info:。
再次全选，按 Ctrl + J 将多行合并为一行，中间加空格。
最后在开头加上 DEL 即可。


## 修改用户余额
用户登录 
python tests/test_login_phone.py --run-api --phone 15200711073 --code 8888 --area 86 --password a123456

修改登录用户数据库余额 UPDATE app_user 
SET `password` = '8ac2e7db07f86bb93437527149cdb7da4ca91dd42f804a1281824661f50cdf65', 
    salt = 'mVNd4EuvcbYH' 
WHERE user_id = 15686

删除用户redis缓存
DEL user:info:15857 user:info:15860 user:info:15852

用户重新登录
python tests/test_login_phone.py --run-api --phone 15200711073 --code 8888 --area 86 --password a123456



# 发金币红包并抢红包
pytest tests/test_receive_red_packet.py -k "coin" --run-api -s

# 发礼物红包并抢红包
pytest tests/test_receive_red_packet.py -k "gift" --run-api -s

# 运行所有抢红包测试
pytest tests/test_receive_red_packet.py --run-api -s



## 使用建议

### 保守模式 (最高成功率)
```bash
python batch_login.py --workers 2 --delay 2.0 --retry 2 --retry-delay 3.0 --jitter 0.4 --save-credentials --verbose
```

### 平衡模式 (速度与成功率平衡)
```bash
python batch_login.py --workers 3 --delay 1.5 --retry 2 --retry-delay 2.5 --jitter 0.3 --save-credentials
```

### 快速模式 (可能有少量失败)
```bash
python batch_login.py --workers 5 --delay 0.8 --retry 1 --retry-delay 1.5 --jitter 0.2 --save-credentials
```

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--workers` | 3 | 并发线程数，建议 2-5 |
| `--delay` | 1.0 | 每个任务开始前等待秒数 |
| `--retry` | 2 | 每个手机号最大重试次数 |
| `--retry-delay` | 2.0 | 失败后重试前等待秒数 |
| `--jitter` | 0.3 | 随机抖动系数 (0-1) |
| `--verbose` | 无 | 打印详细日志 |
| `--save-credentials` | 无 | 保存登录凭证到JSON文件 |
| `--max-count` | 0 | 最多登录数量 (0表示全部) |
| `--start-index` | 0 | 从第几个手机号开始 |

## 数据文件

1. **手机号文件**: `data/login_phone.csv`
   - 包含 `phone_number` 字段
   - 每行一个手机号

2. **设备ID文件**: `data/device_ids.csv`
   - 包含 `uniqueId` 字段
   - 当手机号比设备ID多时，设备ID会循环使用

3. **凭证保存**: `data/batch_login_credentials.json`
   - 使用 `--save-credentials` 参数时生成
   - 包含 `stayUserId` 和 `stayToken`

## 故障排除

### 网络错误 100087
如果仍然出现此错误，请尝试：
1. 进一步降低并发数: `--workers 1`
2. 增加延迟时间: `--delay 3.0`
3. 增加重试延迟: `--retry-delay 5.0`

### 测试单线程登录
使用测试脚本验证单个手机号登录：
```bash
python test_single_login.py
```

## 性能预期

- **保守模式**: 约 2-3 个手机号/分钟
- **平衡模式**: 约 4-6 个手机号/分钟  
- **快速模式**: 约 8-10 个手机号/分钟

成功率应达到 90% 以上。