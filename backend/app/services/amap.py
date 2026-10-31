import json
from typing import Dict, List
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from app.core.config import settings


def _local_result(message: str) -> Dict[str, object]:
    return {"source": "local", "message": message, "items": []}


def _distance_text(value: str) -> str:
    try:
        meters = int(float(value))
    except (TypeError, ValueError):
        return ""
    if meters >= 1000:
        return f"{meters / 1000:.1f} 公里"
    return f"{meters} 米"


def search_courts(payload) -> Dict[str, object]:
    params = {
        "location": f"{payload.longitude:.6f},{payload.latitude:.6f}",
        "radius": payload.radius,
        "sortrule": "distance",
    }
    return _search('around', params, payload.keyword, payload.page)


def search_city_courts(payload) -> Dict[str, object]:
    return _search('text', {"city": payload.city.strip(), "citylimit": "true"}, payload.keyword, payload.page)


def _search(method, params, keyword, page):
    if not settings.amap_key:
        return _local_result("球馆查询尚未启用，请稍后再试")
    keyword = keyword.strip() or '羽毛球馆'
    if '羽毛球' not in keyword:
        keyword += ' 羽毛球馆'
    params = {**params, 'key': settings.amap_key, 'keywords': keyword, 'offset': 20,
              'page': page, 'extensions': 'base', 'output': 'JSON'}
    url = f"https://restapi.amap.com/v3/place/{method}?{urlencode(params)}"
    try:
        with urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        if data.get("status") != "1":
            return _local_result("球馆查询暂时不可用，请稍后再试")
        items = []
        for poi in data.get("pois", []):
            def value(key):
                item = poi.get(key)
                return item if isinstance(item, str) else ''
            features = [item for item in value('type').split(';') if item][:2] or ['羽毛球']
            address = ''.join(value(key) for key in ('cityname', 'adname', 'address'))
            items.append({
                "id": value('id') or value('name'), "name": value('name') or '羽毛球馆',
                "address": address or '地址请电话确认',
                "distance": _distance_text(value('distance')) if method == 'around' else '',
                "hours": "营业时间、价格和场地请电话确认", "location": value('location'),
                "tel": value('tel'), "features": features,
            })
        count = int(data.get('count') or 0)
        return {"source": "amap", "message": '' if items else "没有查到球馆，试试其他城市或名称",
                "items": items, "has_more": bool(items) and page*20 < count and page < 100}
    except (HTTPError, URLError, TimeoutError, ValueError, TypeError):
        return _local_result("暂时无法查找球馆，请稍后重试")


def amap_status() -> Dict[str, object]:
    if not settings.amap_key:
        return {"ready": False, "message": "还没填写高德钥匙"}

    params = {
        "key": settings.amap_key,
        "location": "116.557000,40.085000",
        "keywords": "羽毛球馆",
        "radius": 1000,
        "offset": 1,
        "page": 1,
        "extensions": "base",
        "output": "JSON",
    }
    url = f"https://restapi.amap.com/v3/place/around?{urlencode(params)}"
    try:
        with urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return {"ready": False, "message": "高德连接失败"}

    if data.get("status") != "1":
        return {"ready": False, "message": str(data.get("info") or "高德钥匙不可用")}
    return {"ready": True, "message": "高德地图已连接"}
