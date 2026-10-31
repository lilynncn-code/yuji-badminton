import hashlib
import hmac
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.sms import SmsChallenge

from Tea.exceptions import TeaException
from alibabacloud_dypnsapi20170525.client import Client
from alibabacloud_dypnsapi20170525 import models as dypns_models
from alibabacloud_tea_openapi import models as open_api_models

from app.core.config import settings


class SmsError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


SCENE_NAMES: Dict[str, str] = {
    "register": "注册",
    "login": "登录",
    "change_phone": "更换手机号",
    "reset_password": "忘记密码",
    "bind_new_phone": "绑定新手机号",
    "check_bind_phone": "确认已绑定手机号",
    "delete_account": "注销账号",
}

ERROR_MESSAGES: Dict[str, str] = {
    "MOBILE_NUMBER_ILLEGAL": "手机号格式不正确",
    "BUSINESS_LIMIT_CONTROL": "发送次数超限，请明天再试",
    "FREQUENCY_FAIL": "发送太频繁，请稍后再试",
    "biz.FREQUENCY": "发送太频繁，请稍后再试",
    "biz.BUSINESS_LIMIT_CONTROL": "发送次数超限，请明天再试",
    "biz.MOBILE_NUMBER_ILLEGAL": "手机号格式不正确",
    "OK": "验证码已发送",
    "isv.BUSINESS_LIMIT_CONTROL": "发送次数超限，请明天再试",
    "isv.MOBILE_NUMBER_ILLEGAL": "手机号格式不正确",
    "isv.FREQUENCY_FAIL": "发送太频繁，请稍后再试",
    "isv.MOBILE_COUNT_OVER_LIMIT": "这个手机号今天发送次数已达上限",
    "isv.DAY_LIMIT_CONTROL": "今天发送次数已达上限，请明天再试",
    "isv.SMS_TEMPLATE_ILLEGAL": "短信模板配置不正确",
    "isv.SMS_SIGNATURE_ILLEGAL": "短信签名配置不正确",
    "isv.INVALID_PARAMETERS": "短信参数不正确",
    "MissingAccessKeyId": "短信配置未完成",
    "InvalidAccessKeyId.NotFound": "短信配置不正确",
    "SignatureDoesNotMatch": "短信配置不正确",
}

def _scene_templates() -> Dict[str, str]:
    return {
        "register": settings.aliyun_sms_template_register,
        "login": settings.aliyun_sms_template_login,
        "change_phone": settings.aliyun_sms_template_change_phone,
        "reset_password": settings.aliyun_sms_template_reset_password,
        "bind_new_phone": settings.aliyun_sms_template_bind_new_phone,
        "check_bind_phone": settings.aliyun_sms_template_check_bind_phone,
        "delete_account": settings.aliyun_sms_template_check_bind_phone,
    }


def validate_sms_scene(scene: str) -> None:
    if scene not in SCENE_NAMES:
        raise SmsError("短信场景不正确")


def _template_code(scene: str) -> str:
    validate_sms_scene(scene)
    template_code = _scene_templates().get(scene, "")
    if not template_code:
        raise SmsError("短信配置未完成")
    return template_code


def _missing_sms_settings(scene: str) -> list[str]:
    missing = []
    if not settings.aliyun_access_key_id:
        missing.append("阿里云 AccessKeyId")
    if not settings.aliyun_access_key_secret:
        missing.append("阿里云 AccessKeySecret")
    if not settings.aliyun_sms_sign_name:
        missing.append("短信签名")
    if not _scene_templates().get(scene, ""):
        missing.append(f"{SCENE_NAMES[scene]}短信模板")
    return missing


def _real_sms_ready(scene: str) -> bool:
    validate_sms_scene(scene)
    return not _missing_sms_settings(scene)


def _ensure_sms_settings(scene: str) -> None:
    missing = _missing_sms_settings(scene)
    if missing:
        raise SmsError("短信配置未完成")


def _client(scene: str) -> Client:
    _ensure_sms_settings(scene)
    config = open_api_models.Config(
        access_key_id=settings.aliyun_access_key_id,
        access_key_secret=settings.aliyun_access_key_secret,
        endpoint=settings.aliyun_dypns_endpoint,
    )
    return Client(config)


def _friendly_error(code: str = "", fallback: str = "短信服务暂时不可用，请稍后再试") -> str:
    return ERROR_MESSAGES.get(code or "", fallback)


def _body_code(response) -> str:
    body = getattr(response, "body", None)
    return getattr(body, "code", "") or ""


def _code_hash(phone, scene, out_id, code):
    # Binding the code to the exact phone, use and send prevents cross-use even
    # when an upstream provider only treats out_id as a tracing identifier.
    message = f'{phone}:{scene}:{out_id}:{code}'.encode()
    if not settings.secret_key: raise SmsError('账号服务暂时不可用，请稍后再试')
    return hmac.new(settings.secret_key.encode(), message, hashlib.sha256).hexdigest()


def send_sms(phone: str, scene: str, db: Session) -> str:
    validate_sms_scene(scene)
    if not settings.secret_key:
        raise SmsError('账号服务暂时不可用，请稍后再试')
    local = settings.can_use_local_sms_code
    if not local:
        _ensure_sms_settings(scene)
    now = datetime.utcnow()
    saved = db.query(SmsChallenge).filter_by(phone=phone, scene=scene).with_for_update().first()
    if saved and (now-saved.sent_at).total_seconds() < settings.aliyun_sms_interval:
        raise SmsError('发送太频繁，请稍后再试')
    out_id = uuid4().hex
    values = dict(out_id=out_id, sent_at=now, expires_at=now+timedelta(seconds=settings.aliyun_sms_valid_time), used=False, attempts=0, local=local, code_hash='')
    if saved:
        for key, value in values.items(): setattr(saved, key, value)
    else:
        saved = SmsChallenge(phone=phone, scene=scene, **values)
        db.add(saved)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise SmsError('验证码正在发送，请稍后再试') from exc
    try:
        if local:
            code = settings.local_sms_code
        else:
            request = dypns_models.SendSmsVerifyCodeRequest(
                phone_number=phone, out_id=out_id, return_verify_code=True,
                sign_name=settings.aliyun_sms_sign_name, template_code=_template_code(scene),
                template_param='{"code":"##code##","min":"5"}',
                code_length=settings.aliyun_sms_code_length, valid_time=settings.aliyun_sms_valid_time,
                interval=settings.aliyun_sms_interval, code_type=settings.aliyun_sms_code_type,
            )
            response = _client(scene).send_sms_verify_code(request)
            body = getattr(response, 'body', None)
            if not getattr(body, 'success', False):
                raise SmsError(_friendly_error(_body_code(response), '短信发送失败，请稍后再试'))
            code = getattr(getattr(body, 'model', None), 'verify_code', '')
            if not isinstance(code, str) or not code:
                raise SmsError('短信验证暂时不可用，请稍后重新获取')
        saved.code_hash = _code_hash(phone, scene, out_id, code)
        db.commit()
    except TeaException as exc:
        db.rollback()
        raise SmsError(_friendly_error(getattr(exc, 'code', ''))) from exc
    except SmsError:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise SmsError('短信发送失败，请稍后再试') from exc
    return f'开发验证码：{settings.local_sms_code}' if local else '验证码已发送'


def check_sms_code(phone: str, code: str, scene: str, db: Session) -> bool:
    validate_sms_scene(scene)
    saved = db.query(SmsChallenge).filter_by(phone=phone, scene=scene).with_for_update().populate_existing().first()
    if not saved: raise SmsError('请先获取本次操作的验证码')
    if saved.used: raise SmsError('验证码已失效，请重新获取')
    if saved.expires_at <= datetime.utcnow():
        saved.used = True; db.commit()
        raise SmsError('验证码已过期，请重新获取')
    if saved.attempts >= 5: raise SmsError('尝试次数过多，请重新获取验证码')
    out_id = saved.out_id
    # The guarded update also protects use by separate server processes.
    count = db.query(SmsChallenge).filter_by(phone=phone,scene=scene,out_id=out_id,used=False).filter(SmsChallenge.attempts < 5).update({SmsChallenge.attempts:SmsChallenge.attempts+1}, synchronize_session=False)
    if not count:
        db.rollback()
        raise SmsError('验证码已失效，请重新获取')
    if not hmac.compare_digest(saved.code_hash, _code_hash(phone,scene,out_id,code)):
        db.commit()
        raise SmsError('验证码不正确，请使用本次操作收到的验证码')
    try:
        if not saved.local:
            if settings.can_use_local_sms_code: raise SmsError('验证码已失效，请重新获取')
            request = dypns_models.CheckSmsVerifyCodeRequest(phone_number=phone, verify_code=code, out_id=out_id)
            response = _client(scene).check_sms_verify_code(request)
            model = getattr(getattr(response, 'body', None), 'model', None)
            if getattr(model, 'verify_result', '') != 'PASS': raise SmsError('验证码不正确或已失效，请重新获取')
        elif not settings.can_use_local_sms_code:
            raise SmsError('验证码已失效，请重新获取')
    except TeaException as exc:
        db.commit()
        raise SmsError(_friendly_error(getattr(exc,'code',''), '验证码校验失败，请稍后再试')) from exc
    except SmsError:
        db.commit()
        raise
    except Exception as exc:
        db.commit()
        raise SmsError('验证码校验失败，请稍后再试') from exc
    claimed = db.query(SmsChallenge).filter_by(phone=phone,scene=scene,out_id=out_id,used=False).update({'used':True}, synchronize_session=False)
    db.commit()
    if not claimed: raise SmsError('验证码已失效，请重新获取')
    return True
