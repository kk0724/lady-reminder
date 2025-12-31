# -*- coding: utf-8 -*-
"""
Server酱版：每天不同时间段推送提醒到微信
- 依赖：requests, schedule
- SendKey 放在环境变量 SERVERCHAN_KEY（更安全）
"""

import os
import time
import random
import datetime as dt
import requests
import schedule


# ========== 1) Server酱推送 ==========
def push_serverchan(title: str, desp: str = "", sendkey: str | None = None) -> None:
    """
    Server酱推送（sctapi）
    """
    key = sendkey or os.getenv("SERVERCHAN_KEY")
    if not key:
        raise RuntimeError("未设置 SERVERCHAN_KEY 环境变量（或未传入 sendkey）")

    url = f"https://sctapi.ftqq.com/{key}.send"
    data = {"title": title, "desp": desp}

    # 简单重试：网络偶发失败时更稳
    last_err = None
    for _ in range(3):
        try:
            r = requests.post(url, data=data, timeout=15)
            r.raise_for_status()
            res = r.json()
            if res.get("code") != 0:
                raise RuntimeError(f"Server酱返回异常: {res}")
            return
        except Exception as e:
            last_err = e
            time.sleep(1.2)

    raise RuntimeError(f"推送失败（已重试）: {last_err}")


# ========== 2) 你的文案库（你可以随便改/加） ==========
MESSAGES = {
    "morning": [
        "早安～记得吃早餐，今天也要元气满满！",
        "起床啦小可爱～喝点水再出门～",
        "早上好❤️ 今天也要顺顺利利！",
    ],
    "noon": [
        "中午啦，记得按时吃饭～别饿着自己！",
        "午饭时间到！吃点喜欢的～",
        "忙也要吃饭噢～我会心疼的❤️",
    ],
    "afternoon": [
        "下午容易犯困，起来活动一下，喝点水～",
        "给你打个气～再坚持一下就下班啦！",
        "摸摸头～辛苦啦，别太累❤️",
    ],
    "night": [
        "晚上啦，早点休息～不要熬夜！",
        "今天辛苦啦❤️ 洗个热水澡放松一下～",
        "晚安～做个好梦，明天更开心！",
    ],
}

TITLES = {
    "morning": "早安提醒 ☀️",
    "noon": "午饭提醒 🍚",
    "afternoon": "下午小提醒 ☕",
    "night": "晚安提醒 🌙",
}


def pick_message(period: str) -> str:
    msgs = MESSAGES.get(period, ["想你啦～"])
    return random.choice(msgs)


# ========== 3) 定时配置：改这里就行 ==========
# 24小时制，按你想要的时间改
SCHEDULES = [
    ("morning", "08:30"),
    ("noon", "12:10"),
    ("afternoon", "16:30"),
    ("night", "22:30"),
]


def job(period: str) -> None:
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = pick_message(period)
    title = TITLES.get(period, "提醒")

    desp = f"{msg}\n\n> 发送时间：{now}"
    push_serverchan(title, desp)
    print(f"[OK] {now} {period} -> {msg}")


def main():
    # 启动时先发一条“上线”通知，方便你确认脚本在跑
    try:
        push_serverchan("提醒脚本已启动 ✅", f"> 启动时间：{dt.datetime.now():%Y-%m-%d %H:%M:%S}")
    except Exception as e:
        print(f"[WARN] 启动通知发送失败：{e}")

    # 注册定时任务
    for period, t in SCHEDULES:
        schedule.every().day.at(t).do(job, period=period)
        print(f"[SET] 每天 {t} 发送 {period}")

    # 常驻循环
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
