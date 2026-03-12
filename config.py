import os

class Config:
    # 从环境变量读取
    USER = os.environ.get("LIB_USER")
    PASS = os.environ.get("LIB_PASS")
    
    # 座位 ID，如果没有环境变量则默认为空，脚本后续会检查
    SEAT_ID = os.environ.get("LIB_SEAT_ID", "101267824")
    
    # 预约参数
    MAX_HOURS = 4
    GAP_MINUTES = 10
    LIMIT_HOUR = 21
    LIMIT_MINUTE = 45
    
    # API 地址
    BASE_URL = "https://libbooking.gzhu.edu.cn/ic-web"
    LOGIN_URL = "https://libbooking.gzhu.edu.cn/#/ic/home"
    CAS_LOGIN_URL = "https://newcas.gzhu.edu.cn/cas/login?service=http%3A%2F%2Flibbooking.gzhu.edu.cn%2Fauthcenter%2FdoAuth%2Ffdbb015893c74659bfc4ba356807817a"

    @classmethod
    def validate(cls):
        """校验必要配置是否存在"""
        if not cls.USER or not cls.PASS:
            raise ValueError("错误：未检测到 LIB_USER 或 LIB_PASS 环境变量。请在 GitHub Secrets 中配置。")