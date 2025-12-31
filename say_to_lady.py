import os
import requests
import datetime as dt
import pytz

# ============ Server酱推送 ============
def push_serverchan(title: str, desp: str = ""):
    """
    使用 Server酱推送通知
    :param title: 推送标题
    :param desp: 推送内容（可以是天气、每日提醒等）
    """
    key = os.getenv("SERVERCHAN_KEY")  # 从 GitHub Secrets 或本地环境变量中读取
    if not key:
        raise RuntimeError("未读取到 SERVERCHAN_KEY（请在 GitHub Secrets 中设置）")

    url = f"https://sctapi.ftqq.com/{key}.send"
    data = {
        "title": title,  # 通知标题
        "desp": desp  # 通知内容
    }
    response = requests.post(url, data=data, timeout=20)
    response.raise_for_status()  # 如果请求失败，抛出异常


# ============ 和风天气：获取天气信息 ============
def fetch_weather_from_hefeng(city: str) -> dict:
    """
    获取和风天气的实时天气数据
    :param city: 城市名（可以是拼音或城市 ID）
    :return: 天气数据字典
    """
    hefeng_api_key = os.getenv("HEFENG_API_KEY")  # 从环境变量中读取 API Key
    if not hefeng_api_key:
        raise RuntimeError("未读取到 HEFENG_API_KEY（请在 GitHub Secrets 中设置）")

    api_host = "kj564nbjm7.re.qweatherapi.com"  # 自定义 API Host
    url = f"https://{api_host}/v7/weather/now"  # 更新为新的 API 请求 URL

    params = {
        "location": city,  # 城市名（或者城市的 ID）
        "key": hefeng_api_key,  # 和风天气 API Key
    }

    # 发送请求
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()  # 如果请求失败，抛出异常
    d = r.json()

    if d.get("code") != "200":
        raise RuntimeError(f"和风天气 API 请求失败：{d.get('message')}")

    data = d.get("now", {})
    if not data:
        raise RuntimeError(f"天气数据解析失败：{d}")

    # 提取天气信息，避免字段缺失导致错误
    return {
        "temp": data.get("temp", "N/A"),  # 当前温度
        "feels_like": data.get("feels_like", "N/A"),  # 体感温度
        "wind_speed": data.get("wind_speed", "N/A"),  # 风速
        "weather": data.get("text", "N/A"),  # 天气状况（如 晴天、阴天）
        "humidity": data.get("humidity", "N/A"),  # 湿度
        "precip": data.get("precip", "0")  # 降水量
    }


# ============ 自动提醒：带伞和穿衣 ============
def weather_reminders(w: dict) -> str:
    """
    根据天气信息生成提醒
    :param w: 天气数据字典
    :return: 提醒信息
    """
    reminders = []

    # 降雨提醒
    try:
        if float(w["precip"]) > 0:
            reminders.append("记得带伞哦🌧️")
    except ValueError:
        pass  # 如果 "precip" 无法转换为数字，忽略

    # 温度过低提醒
    try:
        if float(w["temp"]) < 10:
            reminders.append("天气冷，记得穿暖和些🧥")
    except ValueError:
        pass  # 如果 "temp" 无法转换为数字，忽略

    return " ".join(reminders)


# ============ 主流程 ============
def main():
    # 1) 位置：LAT/LON > CITY > 默认潍坊
    tz = os.getenv("TZ", "Asia/Shanghai").strip() or "Asia/Shanghai"
    city = (os.getenv("CITY") or "").strip()

    lat_env = (os.getenv("LAT") or "").strip()
    lon_env = (os.getenv("LON") or "").strip()

    print("DEBUG CITY =", repr(city), "TZ =", repr(tz), "LAT =", repr(lat_env), "LON =", repr(lon_env))

    if lat_env and lon_env:
        lat, lon = float(lat_env), float(lon_env)
        loc_name = city or "自定义位置"
    elif city:
        loc_name = city
    else:
        loc_name = "Weifang · China"  # 默认潍坊

    # 2) 获取天气 + 每日一句
    w = fetch_weather_from_hefeng(loc_name)  # 获取天气数据
    quote = "每天一句，充实生活！"  # 可以替换为实际的每日一句获取逻辑
    source = "一言"

    # 3) 中国时间（UTC+8）
    now_cn = dt.datetime.now(pytz.timezone(tz))
    now_str = now_cn.strftime("%Y-%m-%d %H:%M")

    # 4) 通知列表直接看到句子
    title = "每日提醒"  # 改回标题

    # 5) 详情：天气 + 来源 + 时间
    weather_line = (
        f"{w['weather']} {loc_name}\n"
        f"当前 {w['temp']}°C（体感 {w['feels_like']}°C），风 {w['wind_speed']} km/h\n"
        f"湿度 {w['humidity']}%"
    )

    # 添加天气提醒
    reminders = weather_reminders(w)
    if reminders:
        weather_line += f"\n\n提醒：{reminders}"

    desp = (
        f"{quote}\n\n"
        f"—— {source}\n\n"
        f"{weather_line}\n\n"
        f"时间：{now_str}"
    )

    # 推送 Server酱通知
    push_serverchan(title=title, desp=desp)
    print("sent quote+weather")


if __name__ == "__main__":
    main()
