import hashlib
import time
import uuid

class Signer:
    @staticmethod
    def generate_signature(params, app_secret):
        """
        1. 过滤掉空值
        2. 按参数名 ASCII 码升序排列
        3. 拼接 AppSecret
        4. MD5 加密
        """
        # 1. 过滤 & 排序
        # 注意：如果签名也包含 Body 里的数据，params 需要传入字典
        keys = sorted([k for k in params if params[k] is not None])
        query_string = "&".join([f"{k}={params[k]}" for k in keys])
        
        # 2. 拼接密钥
        sign_str = f"{query_string}&secret={app_secret}"
        
        # 3. MD5 加密并返回大写
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()