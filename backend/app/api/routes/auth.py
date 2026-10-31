from fastapi import APIRouter, Depends, Header, HTTPException, status, Request
from app.services.limits import limit
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    SendSmsRequest,
    UserResponse,
    PhoneChangeStartRequest, PhoneChangeTicketRequest, PhoneChangeFinishRequest,
)
from app.services.security import create_token, hash_password, verify_password
from app.services.sms import SmsError, check_sms_code, send_sms, validate_sms_scene

router = APIRouter()
import hashlib
import secrets
from datetime import datetime,timedelta
from sqlalchemy.exc import IntegrityError
from app.models.account import PhoneChange

PHONE_PREFIXES = {
    "13",
    "14",
    "15",
    "16",
    "17",
    "18",
    "19",
}


def to_auth_response(user: User, message: str) -> AuthResponse:
    return AuthResponse(
        token=create_token(user.id, user.session_version or 0),
        user=UserResponse.model_validate(user),
        message=message,
    )


def fail(message: str, code: int = status.HTTP_400_BAD_REQUEST) -> None:
    raise HTTPException(status_code=code, detail=message)


def ensure_phone(phone: str) -> str:
    if not phone:
        fail("请填写手机号")
    if not phone.isascii() or not phone.isdigit():
        fail("手机号只能填写数字")
    if len(phone) != 11 or phone[:2] not in PHONE_PREFIXES:
        fail("请填写正确的 11 位手机号")
    return phone


def ensure_username(username: str) -> str:
    if not username:
        fail("请填写用户名")
    if len(username) < 2:
        fail("用户名至少 2 个字")
    if len(username) > 50:
        fail("用户名不能超过 50 个字")
    if username.isdigit():
        fail("用户名不能全是数字")
    if username != username.strip() or any(char.isspace() for char in username):
        fail("用户名不能包含空格")
    allowed = set("_-")
    if not all(char.isalnum() or char in allowed for char in username):
        fail("用户名只能使用中文、英文、数字、下划线或短横线")
    return username


def ensure_name(name: str, username: str) -> str:
    display_name = name or username
    if len(display_name) > 50:
        fail("昵称不能超过 50 个字")
    return display_name


def ensure_password(password: str, field_name: str = "密码") -> str:
    if not password:
        fail(f"请填写{field_name}")
    if password != password.strip():
        fail(f"{field_name}开头或结尾不能有空格")
    if len(password) < 6:
        fail(f"{field_name}至少 6 位")
    if len(password) > 50:
        fail(f"{field_name}不能超过 50 位")
    if any(char.isspace() for char in password):
        fail(f"{field_name}不能包含空格")
    has_letter = any(char.isalpha() for char in password)
    has_number = any(char.isdigit() for char in password)
    if not has_letter or not has_number:
        fail(f"{field_name}需要同时包含字母和数字")
    return password


def ensure_sms_code(code: str) -> str:
    if not code:
        fail("请填写验证码")
    if not code.isascii() or not code.isdigit():
        fail("验证码只能填写数字")
    if len(code) != 6:
        fail("请填写 6 位验证码")
    return code


def ensure_account(account: str) -> str:
    if not account:
        fail("请填写用户名或手机号")
    if len(account) > 50:
        fail("用户名或手机号不能超过 50 个字")
    return account


def verify_sms_or_fail(phone: str, code: str, scene: str, db: Session) -> None:
    try:
        passed = check_sms_code(phone, code, scene, db)
    except SmsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    if not passed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码不正确")


from app.api.deps import get_current_user


@router.post("/send-sms", response_model=MessageResponse)
def send_sms_code(payload: SendSmsRequest, db: Session = Depends(get_db)) -> MessageResponse:
    phone = ensure_phone(payload.phone)
    limit("sms:" + phone, 5, 3600)
    scene = payload.scene
    try:
        validate_sms_scene(scene)
    except SmsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    try:
        message = send_sms(phone, scene, db)
    except SmsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    return MessageResponse(message=message)


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    username = ensure_username(payload.username)
    phone = ensure_phone(payload.phone)
    password = ensure_password(payload.password)
    name = ensure_name(payload.name or "", username)
    sms_code = ensure_sms_code(payload.sms_code)

    username_exists = db.query(User).filter(User.username == username).first()
    if username_exists:
        fail("用户名已存在")
    phone_exists = db.query(User).filter(User.phone == phone).first()
    if phone_exists:
        fail("手机号已注册")
    verify_sms_or_fail(phone, sms_code, "register", db)

    user = User(
        username=username,
        phone=phone,
        password_hash=hash_password(password),
        name=name,
        city="",
        level_tag="羽毛球爱好者",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return to_auth_response(user, "注册成功")


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> AuthResponse:
    account = ensure_account(payload.account)
    limit("login-account:" + account, 12, 600)
    limit("login-ip:" + (request.client.host if request.client else "unknown"), 60, 600)
    if not payload.password:
        fail("请填写密码")
    user = db.query(User).filter(or_(User.username == account, User.phone == account)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码不正确")
    user.last_active_at = __import__("datetime").datetime.utcnow()
    db.commit()
    return to_auth_response(user, "登录成功")


@router.post("/forgot-password", response_model=AuthResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> AuthResponse:
    account = ensure_account(payload.account)
    phone = ensure_phone(payload.phone)
    sms_code = ensure_sms_code(payload.sms_code)
    new_password = ensure_password(payload.new_password, "新密码")
    user = db.query(User).filter(or_(User.username == account, User.phone == account)).first()
    if not user or user.phone != phone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号和手机号不匹配")
    verify_sms_or_fail(phone, sms_code, "reset_password", db)

    user.session_version += 1
    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return to_auth_response(user, "密码已重置")


@router.post("/change-password", response_model=AuthResponse)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuthResponse:
    if not payload.old_password:
        fail("请填写旧密码")
    new_password = ensure_password(payload.new_password, "新密码")
    if not payload.confirm_password:
        fail("请填写确认新密码")
    if payload.new_password != payload.confirm_password:
        fail("两次新密码不一致")
    if not verify_password(payload.old_password, current_user.password_hash):
        fail("旧密码不正确")
    if verify_password(new_password, current_user.password_hash):
        fail("新密码不能和旧密码一样")

    current_user.session_version += 1
    current_user.password_hash = hash_password(new_password)
    db.commit()
    return to_auth_response(current_user, "密码修改成功")


@router.post("/logout", response_model=MessageResponse)
def logout(authorization: str = Header(default=""), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    import hashlib
    from app.models.user import RevokedSession
    token_hash = hashlib.sha256(authorization.split()[1].encode()).hexdigest()
    if not db.get(RevokedSession, token_hash):
        db.add(RevokedSession(token_hash=token_hash))
        db.commit()
    return MessageResponse(message="已退出登录")


@router.post('/change-phone/code',response_model=MessageResponse)
def send_current_phone_code(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    limit('sms:'+user.phone,5,3600)
    try:return MessageResponse(message=send_sms(user.phone,'change_phone',db))
    except SmsError as exc:fail(exc.message)


@router.post('/change-phone/start')
def start_phone_change(payload:PhoneChangeStartRequest,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    limit(f'phone-change:{user.id}',10,3600)
    new_phone=ensure_phone(payload.new_phone)
    if new_phone==user.phone:fail('新手机号不能与原手机号相同')
    if db.query(User.id).filter(User.phone==new_phone).first():fail('新手机号已被使用')
    if not verify_password(payload.password,user.password_hash):fail('当前密码不正确')
    old_phone,version=user.phone,user.session_version
    verify_sms_or_fail(old_phone,payload.old_code,'change_phone',db)
    user=db.query(User).filter_by(id=user.id).with_for_update().populate_existing().one()
    if (user.phone,user.session_version)!=(old_phone,version):fail('账号信息已变化，请重新验证')
    # A new verification invalidates previous unfinished changes for this account.
    db.query(PhoneChange).filter_by(user_id=user.id,used=False).update({'used':True},synchronize_session=False)
    ticket=secrets.token_urlsafe(32)
    row=PhoneChange(key_hash=hashlib.sha256(ticket.encode()).hexdigest(),user_id=user.id,old_phone=old_phone,new_phone=new_phone,session_version=version,expires_at=datetime.utcnow()+timedelta(minutes=5),used=False)
    db.add(row)
    limit('sms:'+new_phone,5,3600)
    try:message=send_sms(new_phone,'bind_new_phone',db)
    except SmsError as exc:fail(exc.message)
    return {'change_id':ticket,'message':message,'expires_at':row.expires_at.isoformat()+'Z'}


def phone_change_ticket(ticket,user,db):
    row=db.get(PhoneChange,hashlib.sha256(ticket.encode()).hexdigest())
    if not row or row.user_id!=user.id:fail('更换手机号的验证不存在',404)
    if row.used or row.expires_at<=datetime.utcnow() or (row.old_phone,row.session_version)!=(user.phone,user.session_version):
        fail('验证已失效，请重新开始')
    return row


@router.post('/change-phone/resend',response_model=MessageResponse)
def resend_new_phone_code(payload:PhoneChangeTicketRequest,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    row=phone_change_ticket(payload.change_id,user,db)
    limit('sms:'+row.new_phone,5,3600)
    try:return MessageResponse(message=send_sms(row.new_phone,'bind_new_phone',db))
    except SmsError as exc:fail(exc.message)


@router.post('/change-phone/finish',response_model=AuthResponse)
def finish_phone_change(payload:PhoneChangeFinishRequest,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    row=phone_change_ticket(payload.change_id,user,db)
    if db.query(User.id).filter(User.phone==row.new_phone,User.id!=user.id).first():fail('新手机号已被使用，请重新开始')
    verify_sms_or_fail(row.new_phone,payload.new_code,'bind_new_phone',db)
    user=db.query(User).filter_by(id=user.id).with_for_update().populate_existing().one()
    db.expire(row)
    row=phone_change_ticket(payload.change_id,user,db)
    user.phone=row.new_phone;user.session_version+=1;row.used=True
    try:db.commit()
    except IntegrityError:
        db.rollback();fail('新手机号已被使用，请重新开始')
    return to_auth_response(user,'手机号已更换，其他设备需要重新登录')


@router.post('/change-phone/cancel',response_model=MessageResponse)
def cancel_phone_change(payload:PhoneChangeTicketRequest,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    row=db.get(PhoneChange,hashlib.sha256(payload.change_id.encode()).hexdigest())
    if not row or row.user_id!=user.id:fail('更换手机号的验证不存在',404)
    row.used=True;db.commit()
    return MessageResponse(message='已取消这次验证')
