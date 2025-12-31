# -*- coding: utf-8 -*-
import os
import datetime as dt
import requests

def push_serverchan(title: str, desp: str = ""):
    key = os.getenv("SERVERCHAN_KEY")
    if not key:
        raise RuntimeError("Missing SERVERCHAN_KEY")
    url = f"https://sctapi.ftqq.com/{key}.send"
    r = requests.post(url, data={"title": title, "desp": desp}, timeout=15)
    r.raise_for_status()

def fetch_hitokoto() -> dict:
    # 一言：v1.hitokoto.cn 的用法见官方文档
    # 这里用最简单的 JSON 返回
    r = requests.get("https://v1.hitokoto.cn/?encode=json", timeout=15)
    r.raise_for_status()
    return r.json()

def main():
    data = fetch_hitokoto()
    text = data.get("hitokoto", "").strip()
    frm  = data.get("from", "").strip()
    who  = (data.get("from_who") or "").strip()

    now_jst = dt.datetime.utcnow() + dt.timedelta(hours=9)
    now_str = now_jst.strftime("%Y-%m-%d %H:%M")

    source = " · ".join([x for x in [who, frm] if x])
    desp = f"{text}\n\n—— {source if source else '一言'}\n\n时间：{now_str}"

    push_serverchan("每日一句 ❤️", desp)
    print("sent")

if __name__ == "__main__":
    main()
