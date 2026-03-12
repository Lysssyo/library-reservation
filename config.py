import os

class Config:
    # 统一认证账号密码
    USER = os.environ.get("LIB_USER")
    PASS = os.environ.get("LIB_PASS")
    
    # 座位 ID
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

    # 阿里云 FC 配置
    ALIBABA_CLOUD_ACCESS_KEY_ID = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")
    ALIBABA_CLOUD_ACCESS_KEY_SECRET = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
    FC_ENDPOINT = os.environ.get("FC_ENDPOINT", "1400907468986719.cn-hongkong.fc.aliyuncs.com")
    FC_FUNCTION_NAME = os.environ.get("FC_FUNCTION_NAME", "library-reservation-trigger")

    @classmethod
    def validate(cls):
        """校验必要配置是否存在"""
        if not cls.USER or not cls.PASS:
            raise ValueError("错误：未检测到 LIB_USER 或 LIB_PASS 环境变量。请在 GitHub Secrets 中配置。")

    @classmethod
    def validate_fc(cls):
        """校验阿里云 FC 配置"""
        if not cls.ALIBABA_CLOUD_ACCESS_KEY_ID or not cls.ALIBABA_CLOUD_ACCESS_KEY_SECRET:
            raise ValueError("错误：未检测到阿里云 AK/SK 环境变量。")
