import json
import hashlib
import base64
import time
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

def get_clean_json_str(data):
    """
    1. 过滤空值 (None, "")
    2. jsonEncode (注意：通常需要按 key 排序以保证签名一致)
    """
    if not data:
        return "{}"
    clean_data = {k: v for k, v in data.items() if v is not None and v != ""}
    # separators=(',', ':') 用于去除多余空格，保证与大多数服务端生成的 JSON 字符串一致
    return json.dumps(clean_data, sort_keys=True, separators=(',', ':'))

def get_sign_source(data):
    """
    根据规则处理 signSource: key去掉stay前缀+首字母小写
    """
    if not data: return ""
    processed_data = {}
    for k, v in data.items():
        if v is None or v == "": continue
        new_key = k[4:] if k.startswith("stay") else k
        if new_key:
            new_key = new_key[0].lower() + new_key[1:]
        processed_data[new_key] = v
    return json.dumps(processed_data, sort_keys=True, separators=(',', ':'))

def aes_cbc_encrypt(raw_json_str, encrypt_key):
    """
    严格按照流程：
    JSON -> utf8 -> base64 -> AES-CBC-PKCS7 -> final base64
    """
    iv = "O6xlNQ4e5oRTVZSu".encode('utf-8')
    key = encrypt_key.encode('utf-8')
    
    # 1. utf8.encode -> base64.encode
    b64_step1 = base64.b64encode(raw_json_str.encode('utf-8'))
    
    # 2. AES-CBC-PKCS7 加密
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(b64_step1, AES.block_size)
    encrypted_bytes = cipher.encrypt(padded_data)
    
    # 3. 最终 base64 密文
    return base64.b64encode(encrypted_bytes).decode('utf-8')

def send_stay_code_request(payload, encrypt_key):
    url = "https://api.eastpointtest.com"
    locale = "zh"
    timestamp = str(int(time.time() * 1000))
    
    # --- 计算 Sign ---
    sign_source = get_sign_source(payload)
    # sign = SHA256( signSource + "&locale=" + locale + "&timestamp=" + timestamp + encryptKey )
    sign_str = f"{sign_source}&locale={locale}&timestamp={timestamp}{encrypt_key}"
    sign = hashlib.sha256(sign_str.encode('utf-8')).hexdigest().lower()
    
    # --- 加密 Body ---
    json_str = get_clean_json_str(payload)
    encrypted_body = aes_cbc_encrypt(json_str, encrypt_key)
    
    headers = {
        'content-type': 'application/json',
        'locale': locale,
        'appLanguage': 'en',
        'timestamp': timestamp,
        'sign': sign,
        'app-type': '0',
        'content-sign': 'sat1',
        'content-status': '1',
        'platform-type': '0',
        'variant-type': '0',
        'build-version': '317'
    }

    print(f"发送数据: {json_str}")
    print(f"加密后的Body: {encrypted_body[:50]}...") 

    try:
        # 直接作为 HTTP body 发送加密字符串
        response = requests.post(url, headers=headers, data=encrypted_body)
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
    except Exception as e:
        print(f"请求失败: {e}")

# --- 测试运行 ---
if __name__ == "__main__":
    # 请替换为你的实际 32 字节密钥
    MY_ENCRYPT_KEY = "kGJGJBTNcPI3t0NnWWe60hOcKXuxpyo7" 
    
    test_payload = {
        "stayMobile": "13800138000",
        "stayType": "1",
        "emptyTest": ""
    }
    
    send_stay_code_request(test_payload, MY_ENCRYPT_KEY)
