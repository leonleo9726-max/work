import hashlib

def generate_heard_sign(params, timestamp, secret_key="your_key"):
    """
    根据业务规则生成 heard 签名
    """
   
    query_str = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    base_str = f"{query_str}&timestamp={timestamp}&key={secret_key}"
    return hashlib.sha256(base_str.encode()).hexdigest()