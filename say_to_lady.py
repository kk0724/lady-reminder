# -*- coding: utf-8 -*-
"""
每日一句 + 天气（Server酱）
- GitHub Actions 定时每天运行一次
- 从 和风天气 获取天气（需要 API Key）
- 从 一言 Hitokoto 获取每日一句（JSON）
- 用 Server酱推送每日提醒

环境变量（建议在 GitHub Secrets / Variables 里设置）：
- SERVERCHAN_KEY   必填：Server酱 SendKey（用女友的）
- CITY             可选：城市名（英文，如 Weifang）
- LAT / LON        可选：经纬度（优先级高于 CITY）
- TZ               可选：时区（默认 Asia/Shanghai）
- HEFENG_API_KEY   必填：和风天气 API Key
"""

import os
import datetime as dt
import pytz
import requests


# ============ Server酱推送 ============
def push_serverchan(title: str, desp: str = "", short: str = ""):
    key = os.getenv("SERVERCHAN_KEY")
    if not key:
        raise RuntimeError("未读取到 SERVERCHAN_KEY（请在 GitHub Secrets 中设置）")

    url = f"https://sctapi.ftqq.com/{key}.send"
    data = {
        "title": (title or "")[:32],  # 通知标题尽量短
        "desp": desp or "",
    }
    r = requests.post(url, data=data, timeout=20)
    r.raise_for_status()


# ============ 一言：每日一句 ============
def fetch_hitokoto() -> tuple[str, str]:
    r = requests.get("https://v1.hitokoto.cn/?encode=json", timeout=20)
    r.raise_for_status()
    d = r.json()

    text = (d.get("hitokoto") or "").strip()
    frm = (d.get("from") or "").strip()
    who = (d.get("from_who") or "").strip()
    source = " · ".join([x for x in [who, frm] if x]).strip()
    return text, (source or "一言")


# ============ 和风天气：获取天气信息 ============
def fetch_weather_from_hefeng(city: str) -> dict:
    hefeng_api_key = os.getenv("HEFENG_API_KEY")  # 获取和风天气的 API Key
    if not hefeng_api_key:
        raise RuntimeError("未读取到 HEFENG_API_KEY（请在 GitHub Secrets 中设置）")

    url = f"https://api.heweather.com/v7/weather/now"
    params = {
        "location": city,  # 城市名（或者经纬度）
        "key": hefeng_api_key,  # 和风天气 API Key
    }

    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    d = r.json()

    if d.get("code") != "200":
        raise RuntimeError(f"和风天气 API 请求失败：{d.get('message')}")
    
    data = d.get("now", {})
    if not data:
        raise RuntimeError(f"天气数据解析失败：{d}")

    temp = data.get("temp")  # 当前温度
    feels_like = data.get("feels_like")  # 体感温度
    wind_speed = data.get("wind_speed")  # 风速
    weather = data.get("text")  # 天气状况（如 晴天、阴天）
    humidity = data.get("humidity")  # 湿度
    return {
        "temp": temp,
        "feels_like": feels_like,
        "wind_speed": wind_speed,
        "weather": weather,
        "humidity": humidity
    }


def fmt_num(x, unit=""):
    if x is None:
        return "—"
    try:
        return f"{float(x):.0f}{unit}"
    except Exception:
        return f"{x}{unit}"


# ============ 自动提醒：带伞和穿衣 ============
def weather_reminders(w: dict) -> str:
    reminders = []
    
    # 降雨提醒
    if "rain" in w["weather"].lower() or w["humidity"] > 80:
        reminders.append("记得带伞哦🌧️")

    # 温度过低提醒
    if w["temp"] and w["temp"] < 10:
        reminders.append("天气冷，记得穿暖和些🧥")

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
    w = fetch_weather_from_hefeng(loc_name)
    quote, source = fetch_hitokoto()

    # 3) 中国时间（UTC+8）
    now_cn = dt.datetime.now(pytz.timezone(tz))
    now_str = now_cn.strftime("%Y-%m-%d %H:%M")

    # 4) 通知列表直接看到句子
    title = "每日提醒"  # 改回标题
    short = quote  # 不用短句

    # 5) 详情：天气 + 来源 + 时间
    weather_line = (
        f"{w['weather']} {loc_name}\n"
        f"当前 {fmt_num(w['temp'],'°C')}（体感 {fmt_num(w['feels_like'],'°C')}），风 {fmt_num(w['wind_speed'],' km/h')}\n"
        f"湿度 {fmt_num(w['humidity'],'%')}"
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

    push_serverchan(title=title, desp=desp, short=short)
    print("sent quote+weather")


if __name__ == "__main__":
    main()
