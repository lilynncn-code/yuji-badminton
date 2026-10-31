import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def env_text(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def env_int(name: str, default: int) -> int:
    value = env_text(name, str(default))
    try:
        return int(value)
    except ValueError:
        return default


class Settings:
    app_env: str = env_text("APP_ENV", "prod").lower()
    allow_local_sms_code: bool = env_text("ALLOW_LOCAL_SMS_CODE", "true").lower() in {"1", "true", "yes", "on"}
    local_sms_code: str = env_text("LOCAL_SMS_CODE", "123456")
    mysql_host: str = env_text("MYSQL_HOST", "127.0.0.1")
    mysql_port: str = env_text("MYSQL_PORT", "3306")
    mysql_user: str = env_text("MYSQL_USER", "root")
    mysql_password: str = env_text("MYSQL_PASSWORD")
    mysql_database: str = env_text("MYSQL_DATABASE", "my_app")
    secret_key: str = env_text("SECRET_KEY")
    aliyun_access_key_id: str = env_text("ALIYUN_ACCESS_KEY_ID")
    aliyun_access_key_secret: str = env_text("ALIYUN_ACCESS_KEY_SECRET")
    aliyun_dypns_endpoint: str = env_text("ALIYUN_DYPNS_ENDPOINT", "dypnsapi.aliyuncs.com")
    aliyun_sms_sign_name: str = env_text("ALIYUN_SMS_SIGN_NAME", "速通互联验证码")
    aliyun_sms_template_register: str = env_text("ALIYUN_SMS_TEMPLATE_REGISTER", "100001")
    aliyun_sms_template_login: str = env_text("ALIYUN_SMS_TEMPLATE_LOGIN", "100001")
    aliyun_sms_template_change_phone: str = env_text("ALIYUN_SMS_TEMPLATE_CHANGE_PHONE", "100002")
    aliyun_sms_template_reset_password: str = env_text("ALIYUN_SMS_TEMPLATE_RESET_PASSWORD", "100003")
    aliyun_sms_template_bind_new_phone: str = env_text("ALIYUN_SMS_TEMPLATE_BIND_NEW_PHONE", "100004")
    aliyun_sms_template_check_bind_phone: str = env_text("ALIYUN_SMS_TEMPLATE_CHECK_BIND_PHONE", "100005")
    aliyun_sms_code_length: int = env_int("ALIYUN_SMS_CODE_LENGTH", 6)
    aliyun_sms_valid_time: int = env_int("ALIYUN_SMS_VALID_TIME", 300)
    aliyun_sms_interval: int = env_int("ALIYUN_SMS_INTERVAL", 60)
    aliyun_sms_code_type: int = env_int("ALIYUN_SMS_CODE_TYPE", 1)
    doubao_api_key: str = env_text("DOUBAO_API_KEY")
    doubao_model: str = env_text("DOUBAO_MODEL")
    doubao_base_url: str = env_text("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    doubao_realtime_app_id: str = env_text("DOUBAO_REALTIME_APP_ID", env_text("DOUBAO_APP_ID"))
    doubao_realtime_access_key: str = env_text("DOUBAO_REALTIME_ACCESS_KEY", env_text("DOUBAO_ACCESS_KEY"))
    doubao_realtime_api_key: str = env_text("DOUBAO_REALTIME_API_KEY", env_text("DOUBAO_API_KEY"))
    doubao_realtime_resource_id: str = env_text("DOUBAO_REALTIME_RESOURCE_ID", "volc.speech.dialog")
    doubao_realtime_app_key: str = env_text("DOUBAO_REALTIME_APP_KEY", "")
    doubao_realtime_url: str = env_text(
        "DOUBAO_REALTIME_URL",
        "wss://openspeech.bytedance.com/api/v3/realtime/dialogue",
    )
    amap_key: str = env_text("AMAP_KEY")
    match_source_url: str = env_text("MATCH_SOURCE_URL")
    match_source_file: str = env_text("MATCH_SOURCE_FILE")
    match_source_token: str = env_text("MATCH_SOURCE_TOKEN")
    match_sync_enabled: bool = env_text("MATCH_SYNC_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    match_sync_timeout: int = env_int("MATCH_SYNC_TIMEOUT", 20)

    @property
    def is_release(self) -> bool:
        return self.app_env == "prod"

    @property
    def can_use_local_sms_code(self) -> bool:
        return self.app_env == "dev" and self.allow_local_sms_code

    @property
    def server_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/?charset=utf8mb4"
        )

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )


settings = Settings()
