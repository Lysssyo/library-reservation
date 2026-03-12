import requests
import json
from datetime import datetime, timedelta
import time
from config import Config


def get_acc_no(jsid, ic):
    url = f"{Config.BASE_URL}/auth/userInfo"
    headers = {
        "Cookie": f"JSESSIONID={jsid}; ic-cookie={ic}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "lan": "1"
    }
    try:
        res = requests.get(url, headers=headers).json()
        if res.get("code") == 0:
            return res.get("data", {}).get("accNo")
    except:
        pass
    return None


def get_reservations(jsid, ic, token, status):
    """查询指定状态的预约记录"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    url = f"{Config.BASE_URL}/reserve/resvInfo?beginDate={date_str}&endDate={date_str}&needStatus={status}&page=1&pageNum=10"
    headers = {
        "Cookie": f"JSESSIONID={jsid}; ic-cookie={ic}",
        "token": token,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
    }
    try:
        data = requests.get(url, headers=headers).json().get("data", [])
        return data if data else []
    except:
        return []


def reserve_action(jsid, ic, token, accNo, start_dt, end_dt):
    """执行预约请求，带 1 小时时长校验"""
    duration_min = (end_dt - start_dt).total_seconds() / 60
    if duration_min < 60:
        print(f"[Reserve] 时长仅 {duration_min:.0f} 分钟，不足 1 小时，跳过预约。")
        return False

    url = f"{Config.BASE_URL}/reserve"
    headers = {
        "Cookie": f"JSESSIONID={jsid}; ic-cookie={ic}",
        "token": token,
        "Content-Type": "application/json;charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
    }
    payload = {
        "sysKind": 8, "appAccNo": accNo, "memberKind": 1, "resvMember": [accNo],
        "resvBeginTime": start_dt.strftime("%Y-%m-%d %H:%M:00"),
        "resvEndTime": end_dt.strftime("%Y-%m-%d %H:%M:00"),
        "resvDev": [Config.SEAT_ID]
    }
    try:
        res = requests.post(url, headers=headers, data=json.dumps(payload)).json()
        print(f"[Reserve] {payload['resvBeginTime']} -> {payload['resvEndTime']} | 结果: {res.get('message')}")
        return res.get("code") == 0
    except:
        return False


def smart_refresh_logic(jsid, ic, token, accNo):
    now = datetime.now()
    r8450 = get_reservations(jsid, ic, token, "8450")  # 未来预约
    r8452 = get_reservations(jsid, ic, token, "8452")  # 进行中预约

    # 场景 1: 一天刚开始，没有任何预约
    if not r8450 and not r8452:
        print("[Scenario 1] 没有任何记录，开始贪婪预约...")
        current_start = now + timedelta(minutes=1)
        limit_time = now.replace(hour=Config.LIMIT_HOUR, minute=Config.LIMIT_MINUTE, second=0, microsecond=0)

        while current_start < limit_time:
            current_end = current_start + timedelta(hours=Config.MAX_HOURS) - timedelta(minutes=Config.GAP_MINUTES)
            if current_end > limit_time: current_end = limit_time

            if reserve_action(jsid, ic, token, accNo, current_start, current_end):
                current_start = current_end + timedelta(minutes=Config.GAP_MINUTES)
            else:
                break
            time.sleep(1)

    # 场景 2: 当前没在约，但未来有（在 Gap 休息中）
    elif not r8452 and r8450:
        print("[Scenario 2] 当前处于 Gap 休息时间或等待下次预约开始，不执行操作。")

    # 场景 3: 查 8452 不为空，刷新当前预约
    elif r8452:
        print(f"[Scenario 3] 发现进行中预约，执行断开重连刷新逻辑...")
        end_url = f"{Config.BASE_URL}/reserve/endAhaed"
        headers = {"Cookie": f"JSESSIONID={jsid}; ic-cookie={ic}", "token": token,
                   "Content-Type": "application/json;charset=UTF-8"}

        for res in r8452:
            old_end_str = res.get("resvEndTime")
            uuid = res.get("uuid")
            if not old_end_str or not uuid: continue

            old_end_dt = datetime.strptime(old_end_str, "%Y-%m-%d %H:%M:%S")
            print(f"[Smart] 刷新预约: 记录原结束时间 {old_end_str}，正在提前结束并补位...")

            # 1. 提前结束旧的
            try:
                requests.post(end_url, headers=headers, data=json.dumps({"uuid": uuid}))
                time.sleep(1)
            except:
                pass

            # 2. 补位：从现在起约到原来的结束时间
            new_start = datetime.now() + timedelta(minutes=1)
            reserve_action(jsid, ic, token, accNo, new_start, old_end_dt)

    else:
        print("[Unknown State] 未匹配到预设场景。")
