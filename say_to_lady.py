# -*- coding: utf-8 -*-
"""
GitHub Actions 版本：
每次运行 → 给女友发一条提醒
"""

import os
import datetime as dt
import requests


def push_serverchan(title: str, desp: str = ""):
    key = os.getenv("SERVERCHAN_KEY")
    if not key:
        raise RuntimeError("没有读取到 SERVERCHAN_KEY")

    url = f"https://sctapi.ftqq.com/{key}.send"
    r = requests.post(url, data={"title": title, "desp": desp}, timeout=15)
    r.raise_for_status()


def main():
    now_jst = dt.datetime.utcnow() + dt.timedelta(hours=9)
    now_str = now_jst.strftime("%Y-%m-%d %H:%M")

    push_serverchan(
        "贴心提醒 ❤️",
        f"这是 GitHub 自动定时发送的提醒\n\n时间：{now_str}"
    )
    print("消息已发送")


if __name__ == "__main__":
    main()
