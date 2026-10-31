from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.account import AccountFileDeletion
from app.services.security import verify_password
from app.services.sms import send_sms, check_sms_code, SmsError
from app.services.limits import limit
from app.services.account_deletion import delete_account_data, cleanup_account_files

router = APIRouter(prefix='/account', tags=['account'])


class DeleteAccountRequest(BaseModel):
    password: str = Field(min_length=1, max_length=50)
    sms_code: str = Field(pattern=r'^[0-9]{6}$')
    confirmation: str = Field(max_length=30)


@router.post('/deletion/code')
def deletion_code(user: User=Depends(get_current_user), db: Session=Depends(get_db)):
    limit('sms:'+user.phone,5,3600)
    try: return {'message':send_sms(user.phone,'delete_account',db)}
    except SmsError as exc: raise HTTPException(400,exc.message)


@router.post('/deletion')
def delete_account(payload: DeleteAccountRequest, user: User=Depends(get_current_user), db: Session=Depends(get_db)):
    limit(f'delete-account:{user.id}',10,3600)
    if payload.confirmation != '确认注销': raise HTTPException(400,'请填写“确认注销”')
    if not verify_password(payload.password,user.password_hash): raise HTTPException(400,'当前密码不正确')
    uid, version, phone = user.id, user.session_version, user.phone
    try:
        if not check_sms_code(phone,payload.sms_code,'delete_account',db): raise HTTPException(400,'验证码不正确')
    except SmsError as exc: raise HTTPException(400,exc.message)
    user=db.query(User).filter_by(id=uid).with_for_update().populate_existing().first()
    if not user or (user.phone,user.session_version)!=(phone,version): raise HTTPException(400,'账号信息已变化，请重新验证')
    paths=delete_account_data(user,db)
    cleanup_account_files(db)
    pending=db.query(AccountFileDeletion).filter(AccountFileDeletion.path.in_(paths)).count()
    return {'message':'账号已注销，登录已失效。' + ('部分文件等待清理。' if pending else '相关文件已清理。'), 'files_pending':pending>0}
