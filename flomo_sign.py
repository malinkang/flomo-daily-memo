import hashlib


def _ksort(d):
    """对字典按键排序"""
    return dict(sorted(d.items()))


def get_sign(params):
    """
    生成 Flomo API 签名
    
    Args:
        params: 请求参数字典
    
    Returns:
        MD5 签名字符串
    """
    params = _ksort(params)
    t = ""
    
    for key in params:
        value = params[key]
        if value is not None and (value or value == 0):
            if isinstance(value, list):
                value.sort(key=lambda x: x if x else '')
                for item in value:
                    t += f"{key}[]={item}&"
            else:
                t += f"{key}={value}&"
    
    t = t[:-1]  # 去掉最后一个 &
    return _md5(t + "dbbc3dd73364b4084c3a69346e0ce2b2")


def _md5(text):
    """计算 MD5 哈希"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()
