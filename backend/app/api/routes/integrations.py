from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.models.user import User
from app.services.limits import limit

from app.schemas.integrations import (
    AmapCourtQuery,
    AmapCityCourtQuery,
    AmapCourtResponse,
    AmapStatusResponse,
    TrainingAdviceRequest,
    TrainingAdviceResponse,
)
from app.services.amap import amap_status, search_courts, search_city_courts
from app.services.doubao import get_training_advice

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post("/doubao/training-advice", response_model=TrainingAdviceResponse)
def doubao_training_advice(payload: TrainingAdviceRequest, user: User = Depends(get_current_user)) -> TrainingAdviceResponse:
    limit(f"advice:{user.id}", 20, 60)
    return TrainingAdviceResponse(**get_training_advice(payload))


@router.post("/amap/courts", response_model=AmapCourtResponse)
def amap_courts(payload: AmapCourtQuery, user: User = Depends(get_current_user)) -> AmapCourtResponse:
    limit(f"courts:{user.id}", 20, 60)
    return AmapCourtResponse(**search_courts(payload))


@router.post('/amap/courts/city', response_model=AmapCourtResponse)
def amap_city_courts(payload: AmapCityCourtQuery, user: User = Depends(get_current_user)):
    limit(f'courts:{user.id}', 20, 60)
    if not payload.city.strip():
        from fastapi import HTTPException
        raise HTTPException(400, '请填写城市')
    return AmapCourtResponse(**search_city_courts(payload))


@router.get("/amap/status", response_model=AmapStatusResponse)
def amap_ready(user: User = Depends(get_current_user)) -> AmapStatusResponse:
    limit(f"map-status:{user.id}", 10, 60)
    return AmapStatusResponse(**amap_status())
