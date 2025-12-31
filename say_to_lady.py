# -*- coding: utf-8 -*-
"""
每日一句 + 天气（Server酱）
- GitHub Actions 定时每天运行一次
- 从 Open-Meteo 获取天气（无需 API Key）
- 从 一言 Hitokoto 获取每日一句（JSON）
- 用 Server酱 short 让通知列表直接显示句子摘要

环境变量（建议在 GitHub Secrets / Variables 里设置）：
- SERVERCHAN_KEY   必填：Server酱 SendKey（用女友的）
- CITY             可选：城市名（英文，如 Xi'an）
- LAT / LON        可选：经纬度（优先级高于 CITY）
- TZ               可选：时区（默认 Asia/Shanghai）
"""

import os
import datetime as dt
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
    # short：卡片摘要（通知列表更容易显示到正文）
    if short:
        data["short"] = short[:64]

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


# ============ Open-Meteo：地理编码（城市->经纬度） ============
def geocode_city(city: str) -> tuple[float, float, str]:
    url = "https://geocoding-api.open-meteo.com/v1/search"
    r = requests.get(
        url,
        params={"name": city, "count": 1, "language": "en", "format": "json"},
        timeout=20,
    )
    r.raise_for_status()
    d = r.json()
    results = d.get("results") or []
    if not results:
        raise RuntimeError(f"地理编码失败：找不到城市 {city!r}")

    x = results[0]
    name = x.get("name") or city
    country = x.get("country") or ""
    loc_name = f"{name}{(' · ' + country) if country else ''}"
    return float(x["latitude"]), float(x["longitude"]), loc_name


# ============ Open-Meteo：天气 ============
def weather_emoji(weathercode: int) -> str:
    if weathercode == 0:
        return "☀️"
    if weathercode in (1, 2):
        return "🌤️"
    if weathercode == 3:
        return "☁️"
    if weathercode in (45, 48):
        return "🌫️"
    if weathercode in (51, 53, 55, 56, 57):
        return "🌦️"
    if weathercode in (61, 63, 65, 66, 67, 80, 81, 82):
        return "🌧️"
    if weathercode in (71, 73, 75, 77, 85, 86):
        return "🌨️"
    if weathercode in (95, 96, 99):
        return "⛈️"
    return "🌡️"


def fetch_weather(lat: float, lon: float, tz: str) -> dict:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": tz,
        "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "forecast_days": 1,
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    d = r.json()

    cur = d.get("current") or {}
    daily = d.get("daily") or {}

    tmax = (daily.get("temperature_2m_max") or [None])[0]
    tmin = (daily.get("temperature_2m_min") or [None])[0]
    pop = (daily.get("precipitation_probability_max") or [None])[0]

    wc = cur.get("weather_code")
    return {
        "temp": cur.get("temperature_2m"),
        "feel": cur.get("apparent_temperature"),
        "wind": cur.get("wind_speed_10m"),
        "weathercode": wc,
        "emoji": weather_emoji(int(wc)) if wc is not None else "🌡️",
        "tmax": tmax,
        "tmin": tmin,
        "pop": pop,
    }


def fmt_num(x, unit=""):
    if x is None:
        return "—"
    try:
        return f"{float(x):.0f}{unit}"
    except Exception:
        return f"{x}{unit}"


# ============ 主流程 ============
def main():
    # 1) 位置：LAT/LON > CITY > 默认西安
    tz = os.getenv("TZ", "Asia/Shanghai").strip() or "Asia/Shanghai"
    city = (os.getenv("CITY") or "").strip()

    lat_env = (os.getenv("LAT") or "").strip()
    lon_env = (os.getenv("LON") or "").strip()

    if lat_env and lon_env:
        lat, lon = float(lat_env), float(lon_env)
        loc_name = city or "自定义位置"
    elif city:
        lat, lon, loc_name = geocode_city(city)
    else:
        # 兜底：默认西安（避免再回到东京）
        lat, lon, loc_name = 34.3416, 108.9398, "Xi'an · China"

    # 2) 获取天气 + 每日一句
    w = fetch_weather(lat, lon, tz)
    quote, source = fetch_hitokoto()

    # 3) 时间：按中国时间显示（UTC+8）
    now_cn = dt.datetime.utcnow() + dt.timedelta(hours=8)
    now_str = now_cn.strftime("%Y-%m-%d %H:%M")

    # 4) 通知列表直接看到句子：title/short 放 quote
    title = f"{w['emoji']} {quote[:28]}"
    short = quote

    # 5) 点进去的详细内容：天气 + 来源 + 时间
    weather_line = (
        f"{w['emoji']} {loc_name}\n"
        f"当前 {fmt_num(w['temp'],'°C')}（体感 {fmt_num(w['feel'],'°C')}），风 {fmt_num(w['wind'],' km/h')}\n"
        f"今日 {fmt_num(w['tmin'],'°C')} ~ {fmt_num(w['tmax'],'°C')}，降雨概率 {fmt_num(w['pop'],'%')}"
    )
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
