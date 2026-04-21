import sys

from login import LoginFatalError, get_library_credentials
from utils import get_acc_no, smart_refresh_logic
from config import Config

def main():
    try:
        Config.validate()
    except ValueError as e:
        print(e)
        sys.exit(1)

    print("=== [开始任务] 执行智能刷新与预约 ===")
    
    # 1. 登录
    try:
        jsid, ic, token = get_library_credentials(Config.USER, Config.PASS)
    except LoginFatalError:
        print("登录流程发生致命错误，本次任务直接失败结束，等待 GitHub Actions 重试。")
        sys.exit(1)

    if not (jsid and ic and token):
        print("登录失败，流程终止。")
        sys.exit(1)

    # 2. 获取 ID
    accNo = get_acc_no(jsid, ic)
    if not accNo:
        print("获取用户 ID 失败。")
        return
    print(f"用户 ID: {accNo}")

    # 3. 执行智能刷新逻辑
    # 包含：不碰未来预约(8450)、重约进行中预约(8452)、批量补全
    smart_refresh_logic(jsid, ic, token, accNo)

    print("\n=== 所有任务已完成 ===")

if __name__ == "__main__":
    main()
