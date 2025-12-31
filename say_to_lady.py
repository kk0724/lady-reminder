# -*- coding: utf-8 -*-
"""
每日一句（Server酱）
- 从一言(hitokoto)获取每日文案
- 在微信通知列表中直接显示句子（title + short）
- 适配 GitHub Actions 定时运行
"""

import os
import requests
import datetime as dt


# ================== Server酱推送 ==================
def push_serverchan(title: str, desp: str = "", short: str = ""):
    key = os.getenv("SERVERCHAN_KEY")
    if not key:
        raise RuntimeError("未读取到 SERVERCHAN_KEY（请在 GitHub Secrets 中设置）")

    url = f"https://sctapi.ftqq.com/{key}.send"
    data = {
        "title": title[:32],   # 微信通知标题最长 32 字
        "desp": desp
    }

    # short：微信卡片摘要，通知列表可见（最长 64 字）
    if short:
        data["short"] = short[:64]

    r = requests.post(url, data=data, timeout=15)
    r.raise_for_status()


# ================== 获取每日文案（一言） ==================
def fetch_daily_quote():
    r = requests.get("https://v1.hitokoto.cn/?encode=json", timeout=15)
    r.raise_for_status()
    data = r.json()

    text = data.get("hitokoto", "").strip()
    frm = data.get("from", "").strip()
    who = (data.get("from_who") or "").strip()

    source = " · ".join([x for x in [who, frm] if x])
    return text, source


# ================== 主逻辑 ==================
def main():
    quote, source = fetch_daily_quote()

    # 日本时间（UTC+9）
    now_jst = dt.datetime.utcnow() + dt.timedelta(hours=9)
    now_str = now_jst.strftime("%Y-%m-%d %H:%M")

    # 核心：让“句子”直接出现在通知列表
    title = quote[:32]          # 标题直接放句子
    short = quote               # 列表摘要也放句子
    desp = f"{quote}\n\n—— {source}\n\n时间：{now_str}"

    push_serverchan(title, desp, short)
    print("已发送每日一句")


if __name__ == "__main__":
    main()
