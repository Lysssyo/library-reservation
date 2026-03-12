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
    except: pass
    return None

def cancel_all_logic(jsid, ic, token):
    """逻辑：查询状态为 8450 的预约并全部删除"""
    today = datetime.now()
    begin = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    end = (today + timedelta(days=7)).strftime("%Y-%m-%d")
    # 注意：这里使用了您更新后的 needStatus=8450
    query_url = f"{Config.BASE_URL}/reserve/resvInfo?beginDate={begin}&endDate={end}&needStatus=8450&page=1&pageNum=50&orderKey=gmt_create&orderModel=desc"
    delete_url = f"{Config.BASE_URL}/reserve/delete"
    
    headers = {
        "Cookie": f"JSESSIONID={jsid}; ic-cookie={ic}",
        "token": token,
        "Content-Type": "application/json;charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
    }

    try:
        res_list = requests.get(query_url, headers=headers).json().get("data", [])
        if not res_list:
            print("[Cancel] 没有发现待生效的预约。")
            return
        
        for item in res_list:
            uuid = item.get("uuid")
            print(f"[Cancel] 正在取消预约: {uuid}")
            res = requests.post(delete_url, headers=headers, data=json.dumps({"uuid": uuid})).json()
            print(f"[Cancel] 响应: {res.get('message')}")
            time.sleep(0.5)
    except Exception as e:
        print(f"[Cancel] 过程出错: {e}")

def end_ahead_logic(jsid, ic, token):
    """逻辑：查询今日预约并执行提前结束"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    # 注意：这里使用了您更新后的 needStatus=8452
    query_url = f"{Config.BASE_URL}/reserve/resvInfo?beginDate={date_str}&endDate={date_str}&needStatus=8452&page=1&pageNum=10"
    end_url = f"{Config.BASE_URL}/reserve/endAhaed"
    
    headers = {
        "Cookie": f"JSESSIONID={jsid}; ic-cookie={ic}",
        "token": token,
        "Content-Type": "application/json;charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
    }

    try:
        res_list = requests.get(query_url, headers=headers).json().get("data", [])
        if not res_list:
            print("[EndAhead] 没有发现进行中的预约。")
            return

        for item in res_list:
            uuid = item.get("uuid")
            print(f"[EndAhead] 尝试提前结束预约: {uuid}")
            res = requests.post(end_url, headers=headers, data=json.dumps({"uuid": uuid})).json()
            print(f"[EndAhead] 响应: {res.get('message')}")
            time.sleep(0.5)
    except Exception as e:
        print(f"[EndAhead] 过程出错: {e}")

def batch_reserve_logic(jsid, ic, token, accNo):
    """逻辑：从现在起按规则分段预约"""
    reserve_url = f"{Config.BASE_URL}/reserve"
    now = datetime.now()
    current_start = now + timedelta(minutes=1)
    limit_time = now.replace(hour=Config.LIMIT_HOUR, minute=Config.LIMIT_MINUTE, second=0, microsecond=0)
    
    headers = {
        "Cookie": f"JSESSIONID={jsid}; ic-cookie={ic}",
        "token": token,
        "Content-Type": "application/json;charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
    }

    print(f"[Reserve] 开始批量预约，截止 {Config.LIMIT_HOUR}:{Config.LIMIT_MINUTE}")

    while current_start < limit_time:
        # 计算当前段结束时间
        current_end = current_start + timedelta(hours=Config.MAX_HOURS) - timedelta(minutes=Config.GAP_MINUTES)
        if current_end >= limit_time: 
            current_end = limit_time
        
        # 校验最低时长（1小时 = 3600秒）
        if (current_end - current_start).total_seconds() < 3600:
            print(f"[Reserve] 剩余时间不足1小时，停止预约。")
            break

        payload = {
            "sysKind": 8, "appAccNo": accNo, "memberKind": 1, "resvMember": [accNo],
            "resvBeginTime": current_start.strftime("%Y-%m-%d %H:%M:00"),
            "resvEndTime": current_end.strftime("%Y-%m-%d %H:%M:00"),
            "resvDev": [Config.SEAT_ID]
        }
        
        print(f"[Reserve] 正在预约: {payload['resvBeginTime']} -> {payload['resvEndTime']}")
        try:
            res = requests.post(reserve_url, headers=headers, data=json.dumps(payload)).json()
            print(f"[Reserve] 结果: {res.get('message')}")
        except Exception as e:
            print(f"[Reserve] 请求出错: {e}")
        
        # 准备下一段：当前结束时间 + GAP
        current_start = current_end + timedelta(minutes=Config.GAP_MINUTES)
        time.sleep(1)
