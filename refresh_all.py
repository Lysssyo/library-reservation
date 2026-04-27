import sys

from login import LoginFatalError, get_library_credentials
from utils import get_acc_no, smart_refresh_logic
from config import Config


def run_reserve(seat_id=None):
    Config.validate()

    if seat_id is None:
        seat_id = Config.seat_id()

    print("=== [开始任务] 执行智能刷新与预约 ===")

    # 1. 登录
    try:
        jsid, ic, token = get_library_credentials(Config.USER, Config.PASS)
    except LoginFatalError:
        print("登录流程发生致命错误，本次任务失败。")
        raise

    if not (jsid and ic and token):
        raise RuntimeError("登录失败，未获取到有效凭据。")

    # 2. 获取用户 ID
    accNo = get_acc_no(jsid, ic)
    if not accNo:
        raise RuntimeError("获取用户 ID 失败。")
    print(f"用户 ID: {accNo}")

    # 3. 执行智能刷新逻辑
    smart_refresh_logic(jsid, ic, token, accNo, seat_id)

    print("\n=== 所有任务已完成 ===")


if __name__ == "__main__":
    try:
        run_reserve()
    except Exception as e:
        print(e)
        sys.exit(1)
