from login import get_library_credentials
from utils import get_acc_no, cancel_all_logic, end_ahead_logic, batch_reserve_logic
from config import Config

def main():
    try:
        Config.validate()
    except ValueError as e:
        print(e)
        return

    print("=== [步骤 1] 正在执行自动登录 ===")
    # 从配置类读取账号密码
    jsid, ic, token = get_library_credentials(Config.USER, Config.PASS)
    
    if not (jsid and ic and token):
        print("登录失败，流程终止。")
        return

    print("=== [步骤 2] 正在获取用户账户信息 ===")
    accNo = get_acc_no(jsid, ic)
    if not accNo:
        print("获取用户 ID 失败。")
        return
    print(f"用户 ID: {accNo}")

    print("=== [步骤 3] 正在取消所有待生效预约 ===")
    cancel_all_logic(jsid, ic, token)

    print("=== [步骤 4] 正在尝试提前结束当前预约 ===")
    end_ahead_logic(jsid, ic, token)

    print("=== [步骤 5] 正在重新执行分段预约 ===")
    batch_reserve_logic(jsid, ic, token, accNo)

    print("=== 所有任务已完成 ===")

if __name__ == "__main__":
    main()
