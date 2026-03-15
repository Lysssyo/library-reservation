import os
import requests
import json
from datetime import datetime, timedelta, timezone
import time
from config import Config

# 定义北京时区 (UTC+8)
SHA_TZ = timezone(timedelta(hours=8))


def get_now_beijing():
    """获取当前北京时间，支持通过环境变量 MOCK_NOW 模拟时间 (格式: YYYY-MM-DD HH:MM:SS)"""
    mock_now = os.environ.get("MOCK_NOW")
    if mock_now:
        return datetime.strptime(mock_now, "%Y-%m-%d %H:%M:%S")
    return datetime.now(SHA_TZ).replace(tzinfo=None)


def parse_lib_time(val):
    """解析图书馆返回的时间，强制转为北京时间并去掉时区信息方便计算"""
    if not val: return None
    if isinstance(val, (int, float)):
        ts = val / 1000 if val > 1e11 else val
        return datetime.fromtimestamp(ts, SHA_TZ).replace(tzinfo=None)
    else:
        return datetime.strptime(val, "%Y-%m-%d %H:%M:%S")


def get_corrected_start_time(base_time, scenario_name="Smart"):
    """计算起始时间（base_time + 1min），并强制不早于 08:30"""
    start = base_time + timedelta(minutes=1)
    eight_thirty = base_time.replace(hour=8, minute=30, second=0, microsecond=0)
    if start < eight_thirty:
        print(f"[{scenario_name}] 当前时间早于 08:30，将起始时间设为 08:30")
        return eight_thirty
    return start


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
    date_str = get_now_beijing().strftime("%Y-%m-%d")
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
    """
    实现用户定义的三种核心场景逻辑
    """
    now = get_now_beijing()
    r8450 = get_reservations(jsid, ic, token, "8450")  # 未来预约
    r8452 = get_reservations(jsid, ic, token, "8452")  # 进行中预约

    # 场景 1: 一天刚开始，没有任何预约
    if not r8450 and not r8452:
        print("[Scenario 1] 没有任何记录，开始分段预约...")
        current_start = get_corrected_start_time(now, "Scenario 1")
        limit_time = now.replace(hour=Config.LIMIT_HOUR, minute=Config.LIMIT_MINUTE, second=0, microsecond=0)

        while current_start < limit_time:
            current_end = current_start + timedelta(hours=Config.MAX_HOURS) - timedelta(minutes=Config.GAP_MINUTES)
            if current_end > limit_time: current_end = limit_time

            if reserve_action(jsid, ic, token, accNo, current_start, current_end):
                current_start = current_end + timedelta(minutes=Config.GAP_MINUTES)
            else:
                break
            time.sleep(1)

    # 场景 2: 当前无预约，但未来有预约。检查是否可以补齐当前到未来最早预约之间的空隙
    elif not r8452 and r8450:
        print("[Scenario 2] 当前无预约但未来有记录，检查补全逻辑...")
        
        # 获取未来所有预约中最早的起始时间
        min_future_start = None
        for res in r8450:
            st = parse_lib_time(res.get("resvBeginTime"))
            if st:
                if min_future_start is None or st < min_future_start:
                    min_future_start = st
        
        if min_future_start:
            current_start = get_corrected_start_time(now, "Scenario 2")
            # 补全段的结束时间：未来最早开始时间 - Gap
            current_end = min_future_start - timedelta(minutes=Config.GAP_MINUTES)
            
            # 检查空隙是否大于等于 1 小时
            gap_duration = current_end - current_start
            if gap_duration >= timedelta(hours=1):
                print(f"[Scenario 2] 补全预约空档 (时长 {gap_duration}): {current_start.strftime('%H:%M')} -> {current_end.strftime('%H:%M')}")
                reserve_action(jsid, ic, token, accNo, current_start, current_end)
            else:
                print(f"[Scenario 2] 距离未来最早预约 ({min_future_start.strftime('%H:%M')}) 空隙不足 1 小时，保持静默。")
        else:
            print("[Scenario 2] 无法解析未来起始时间。")

    # 场景 3: 刷新进行中预约
    elif r8452:
        print(f"[Scenario 3] 发现进行中预约，检查刷新逻辑...")
        end_url = f"{Config.BASE_URL}/reserve/endAhaed"
        headers = {"Cookie": f"JSESSIONID={jsid}; ic-cookie={ic}", "token": token,
                   "Content-Type": "application/json;charset=UTF-8"}

        for res in r8452:
            uuid = res.get("uuid")
            status_code = res.get("resvStatus")
            old_end_dt = parse_lib_time(res.get("resvEndTime"))

            if not uuid or not old_end_dt: continue

            if status_code == 1093:
                print(f"[Smart] 预约 [{uuid}] 已签到 (Status: 1093)，保持现状。")
                continue

            print(f"[Smart] 刷新预约: 记录原结束时间 {old_end_dt.strftime('%H:%M:%S')}，正在刷新...")

            try:
                requests.post(end_url, headers=headers, data=json.dumps({"uuid": uuid}))
                time.sleep(1)
            except:
                pass

            new_start = get_corrected_start_time(get_now_beijing(), "Scenario 3")
            reserve_action(jsid, ic, token, accNo, new_start, old_end_dt)

    else:
        print("[Unknown State] 无法匹配场景。")
