from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.api.deps import get_current_user
from app.services.files import valid_image_url
from app.services.people_pages import people_query
from app.services.public_media import validate_public_media, retire_public_media
from app.services.file_cleanup import cleanup_files

router = APIRouter(prefix="/profile", tags=["profile"])
current_user_dep = get_current_user


def clean(value: str) -> str:
    return value.strip()


def fail(message: str) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


def clean_required_name(value: str) -> str:
    name = clean(value)
    if not name:
        fail("昵称不能为空")
    return name


def to_profile(user: User, db: Session) -> ProfileResponse:
    return ProfileResponse(
        id=user.id,
        can_review_reports=user.can_review_reports == 1,
        following=people_query(db, user.id, 'following')[0].count(),
        followers=people_query(db, user.id, 'followers')[0].count(),
        username=user.username,
        phone=user.phone,
        name=user.name,
        nickname=user.name,
        avatar=user.avatar,
        cover=user.cover,
        club=user.club,
        hand=user.hand,
        city=user.city,
        level_tag=user.level_tag,
        levelTag=user.level_tag,
        level=user.level_tag,
        bio=user.bio,
    )


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(current_user: User = Depends(current_user_dep), db: Session = Depends(get_db)) -> ProfileResponse:
    return to_profile(current_user, db)


@router.patch("/me", response_model=ProfileResponse)
def update_my_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(current_user_dep),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    current_user=db.query(User).filter_by(id=current_user.id).with_for_update().populate_existing().one()
    old_images={current_user.avatar,current_user.cover}
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    for field in ("avatar", "cover"):
        if field in changes:
            changes[field]=clean(changes[field])
            valid_image_url(changes[field])
            if changes[field]!=getattr(current_user,field):validate_public_media(db,changes[field],current_user.id,'image')
    if "name" in changes:
        current_user.name = clean_required_name(changes["name"])
    if "nickname" in changes:
        current_user.name = clean_required_name(changes["nickname"])
    if "avatar" in changes:
        current_user.avatar = clean(changes["avatar"])
    if "city" in changes:
        current_user.city = clean(changes["city"])
    if "level_tag" in changes:
        current_user.level_tag = clean(changes["level_tag"])
    if "levelTag" in changes:
        current_user.level_tag = clean(changes["levelTag"])
    if "level" in changes:
        current_user.level_tag = clean(changes["level"])
    if "bio" in changes:
        current_user.bio = clean(changes["bio"])

    for field in ("cover", "club", "hand"):
        if field in changes:
            setattr(current_user, field, clean(changes[field]))
    db.add(current_user)
    paths=retire_public_media(db,current_user.id,old_images-{current_user.avatar,current_user.cover})
    db.commit()
    if paths:cleanup_files(db,paths)
    db.refresh(current_user)
    return to_profile(current_user, db)
