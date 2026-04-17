import json
import base64
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

class SignUtils:
    # Keep class-level key for backward compatibility.
    test_encrypt_key = "kGJGJBTNcPI3t0NnWWe60hOcKXuxpyo7"

    @staticmethod
    def filter_empty_values(data):
        """过滤空值"""
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if v is not None and v != '' and v != [] and v != {}}
        return data
    
    @staticmethod
    def json_encode(data):
        """JSON编码并过滤空值"""
        filtered_data = SignUtils.filter_empty_values(data)
        return json.dumps(filtered_data, ensure_ascii=False, separators=(',', ':'))
    
    @staticmethod
    def encrypt(data, encrypt_key, iv="O6xlNQ4e5oRTVZSu"):
        """AES-CBC-PKCS7加密"""
        # 1. JSON编码并过滤空值
        json_str = SignUtils.json_encode(data)
        # 2. utf8.encode → base64.encode
        utf8_encoded = json_str.encode('utf-8')
        base64_encoded = base64.b64encode(utf8_encoded)
        # 3. AES-CBC-PKCS7加密
        backend = default_backend()
        key = encrypt_key.encode('utf-8')
        iv_bytes = iv.encode('utf-8')
        
        # 填充
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(base64_encoded) + padder.finalize()
        
        # 加密
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv_bytes), backend=backend)
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        
        # 4. 返回base64密文
        return base64.b64encode(encrypted).decode('utf-8')
    
    @staticmethod
    def generate_sign(data, locale, timestamp, encrypt_key):
        """生成签名"""
        # 处理signSource：key去掉stay前缀+首字母小写，过滤空值
        sign_source_data = {}
        for key, value in data.items():
            if key.startswith('stay'):
                # 去掉stay前缀
                new_key = key[4:]
                # 首字母小写
                if new_key:
                    new_key = new_key[0].lower() + new_key[1:]
            else:
                # 首字母小写
                if key:
                    new_key = key[0].lower() + key[1:]
                else:
                    new_key = key
            sign_source_data[new_key] = value
        
        # 过滤空值
        filtered_data = SignUtils.filter_empty_values(sign_source_data)
        sign_source = json.dumps(filtered_data, ensure_ascii=False, separators=(',', ':'))
        
        # 生成签名
        sign_string = f"{sign_source}&locale={locale}&timestamp={timestamp}{encrypt_key}"
        sha256 = hashlib.sha256()
        sha256.update(sign_string.encode('utf-8'))
        return sha256.hexdigest().lower()

# 测试环境key
test_encrypt_key = "kGJGJBTNcPI3t0NnWWe60hOcKXuxpyo7"