import fcntl
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from config import Config

BASE_DIR = Path(__file__).parent
STATE_FILE = BASE_DIR / "state.json"
LOG_DIR = BASE_DIR / "logs"
LOCK_FILE = BASE_DIR / "runtime" / "reserve.lock"

SHA_TZ = timezone(timedelta(hours=8))


def now_beijing():
    return datetime.now(SHA_TZ)


def load_state():
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_log_path():
    LOG_DIR.mkdir(exist_ok=True)
    return LOG_DIR / f"{now_beijing().strftime('%Y-%m-%d')}.log"


def write_log(msg):
    log_path = get_log_path()
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


class Tee:
    """将 stdout/stderr 同时写到日志文件和原始输出"""
    def __init__(self, log_path, original):
        self.log = open(log_path, "a", encoding="utf-8")
        self.original = original

    def write(self, data):
        self.log.write(data)
        self.original.write(data)

    def flush(self):
        self.log.flush()
        self.original.flush()

    def close(self):
        self.log.close()


def main():
    LOCK_FILE.parent.mkdir(exist_ok=True)

    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("[run_once] 已有任务在运行，跳过本次执行。", flush=True)
        lock_fd.close()
        return

    log_path = get_log_path()
    tee_out = Tee(log_path, sys.stdout)
    tee_err = Tee(log_path, sys.stderr)
    sys.stdout = tee_out
    sys.stderr = tee_err

    state = load_state()
    start_time = now_beijing()
    print(f"\n{'='*10} {start_time.strftime('%Y-%m-%d %H:%M:%S')} START {'='*10}")

    try:
        if not state.get("enabled", True):
            print("[run_once] 任务已关闭（enabled=false），跳过执行。")
            state["last_run_at"] = start_time.strftime("%Y-%m-%d %H:%M:%S")
            state["last_result"] = "skipped"
            save_state(state)
            return

        seat_id = state.get("seat_id") or Config.seat_id()
        print(f"[run_once] 目标座位 ID: {seat_id}")

        from refresh_all import run_reserve
        run_reserve(seat_id)

        state["last_result"] = "success"

    except Exception as exc:
        state["last_result"] = f"failed: {exc}"
        print(f"[run_once] 任务失败: {exc}", file=sys.stderr)
        raise

    finally:
        state["last_run_at"] = now_beijing().strftime("%Y-%m-%d %H:%M:%S")
        save_state(state)
        end_time = now_beijing()
        result = state.get("last_result", "unknown")
        print(f"{'='*10} {end_time.strftime('%Y-%m-%d %H:%M:%S')} END {result} {'='*10}\n")

        sys.stdout = tee_out.original
        sys.stderr = tee_err.original
        tee_out.close()
        tee_err.close()
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


if __name__ == "__main__":
    main()
