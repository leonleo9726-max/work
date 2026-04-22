import time
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from common.http_utils import HttpUtils
from config import settings
from tests.test_login_phone import build_business_headers_from_login


RECEIVE_RED_PACKET_PATH = "/payer/redPacket/receive"


def receive_red_packet(headers, credential, red_packet_id):
    """抢红包的辅助函数"""
    url = f"{settings.BASE_URL}{RECEIVE_RED_PACKET_PATH}"
    
    payload = {
        "redPacketId": red_packet_id
    }
    
    print(f"[receive_red_packet] 发送请求到: {url}")
    print(f"[receive_red_packet] 请求头: {headers}")
    print(f"[receive_red_packet] 请求参数: {payload}")
    
    response = HttpUtils.post(
        url=url,
        data=payload,
        headers=headers,
        encrypt_key=settings.TEST_ENCRYPT_KEY,
        locale="en",
        timestamp=str(int(time.time() * 1000)),
    )
    
    print(f"[receive_red_packet] 完整响应: {response}")
    
    if response is None:
        raise AssertionError("抢红包接口未返回有效响应")
    
    if not isinstance(response, dict):
        raise AssertionError("抢红包接口返回值应为 JSON 对象")
    
    return response


@pytest.mark.api
@pytest.mark.parametrize(
    "phone_number,red_packet_id",
    [
        ("15200711073", 1),  # 默认红包ID测试
        ("13710011001", 2),  # 自定义红包ID测试
    ],
    ids=["default_receive", "custom_receive"],
)
def test_receive_red_packet(request, phone_number, red_packet_id):
    """抢红包接口测试，从 login_credentials.json 读取登录凭证。"""
    if not request.config.getoption("--run-api"):
        pytest.skip("need --run-api option to execute real API tests")

    headers, credential = build_business_headers_from_login(phone_number=phone_number)
    assert credential["stayToken"], "读取到的 stayToken 不能为空"
    assert credential["stayUserId"], "读取到的 stayUserId 不能为空"

    # 记录请求头中的 token
    token = credential["stayToken"]
    print(f"[receive_red_packet] 用户 {credential['stayUserId']} 的 token: {token[:20]}... (长度: {len(token)})")

    # 抢红包并获取完整响应
    response = receive_red_packet(headers, credential, red_packet_id)

    # 检查响应是否成功
    success = (
        response.get("code") == 0
        or response.get("stayCode") == 200
        or response.get("stayIsSuccess") is True
        or response.get("success") is True
        or response.get("status") == "success"
    )

    if not success:
        error_message = (
            response.get("message")
            or response.get("errorMessage")
            or response.get("msg")
            or "未知错误"
        )
        pytest.fail(f"抢红包失败: {error_message}, 完整响应: {response}")

    print(f"[receive_red_packet] 用户 {credential['stayUserId']} 抢红包成功，红包ID: {red_packet_id}，响应: {response}")


def parse_args():
    """解析命令行参数"""
    import argparse
    parser = argparse.ArgumentParser(description="抢红包测试")
    parser.add_argument("--phone", type=str, default="15200711073",
                       help="手机号码，默认: 15200711073")
    parser.add_argument("--red-packet-id", type=int, default=1,
                       help="红包ID，默认: 1")
    parser.add_argument("--run-api", action="store_true",
                       help="执行真实API测试（需要此参数才会调用接口）")
    parser.add_argument("--verbose", action="store_true",
                       help="打印详细日志")
    return parser.parse_args()


def _receive_red_packet_direct(phone_number, red_packet_id):
    """直接运行模式下的抢红包函数"""
    import sys
    from tests.test_login_phone import build_business_headers_from_login
    from config import settings
    from common.http_utils import HttpUtils
    
    # 获取登录凭证
    headers, credential = build_business_headers_from_login(phone_number=phone_number)
    if not credential.get("stayToken") or not credential.get("stayUserId"):
        print(f"错误: 用户 {phone_number} 登录凭证无效")
        sys.exit(1)
    
    # 记录请求头中的 token
    token = credential["stayToken"]
    print(f"[直接运行] 用户 {credential['stayUserId']} 的 token: {token[:20]}... (长度: {len(token)})")
    
    url = f"{settings.BASE_URL}{RECEIVE_RED_PACKET_PATH}"
    payload = {
        "redPacketId": red_packet_id
    }
    
    print(f"[直接运行] 抢红包参数: {payload}")
    print(f"[直接运行] 请求URL: {url}")
    
    # 发送请求
    response = HttpUtils.post(
        url=url,
        data=payload,
        headers=headers,
        encrypt_key=settings.TEST_ENCRYPT_KEY,
        locale="en",
        timestamp=str(int(time.time() * 1000)),
    )
    
    print(f"[直接运行] 完整响应: {response}")
    
    success = (
        response.get("code") == 0
        or response.get("stayCode") == 200
        or response.get("stayIsSuccess") is True
        or response.get("success") is True
        or response.get("status") == "success"
    )
    
    if success:
        print(f"[直接运行] 抢红包成功")
        return True
    else:
        # 不打印详细错误信息，只返回False
        return False


if __name__ == "__main__":
    args = parse_args()
    print(f"[命令行参数] phone={args.phone}, red-packet-id={args.red_packet_id}, "
          f"run-api={args.run_api}, verbose={args.verbose}")
    
    if not args.run_api:
        print("警告: 需要 --run-api 参数才会执行真实API测试")
        print("示例: python tests/test_receive_red_packet.py --run-api --phone 15200711073 --red-packet-id 1")
        sys.exit(0)
    
    success = _receive_red_packet_direct(
        phone_number=args.phone,
        red_packet_id=args.red_packet_id,
    )
    
    if success:
        print("[直接运行] 测试通过")
        sys.exit(0)
    else:
        print("[直接运行] 测试失败")
        sys.exit(1)