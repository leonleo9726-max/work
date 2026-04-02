import requests

def test_get_weather():
    """测试一个公开的查询接口"""
    url = "https://httpbin.org/get"
    response = requests.get(url)
    
    # 断言状态码
    assert response.status_code == 200
    # 断言返回结果包含特定字段
    data = response.json()
    assert "origin" in data
#   assert "ip" in response.json()
    print(f"\n当前请求的IP地址是: {data['origin']}")