from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.services.files import UPLOADS

from app.api.routes import auth, chat, content, discovery, integrations, media, posts, profile, training, social, games, clinic, account, notifications
from app.db.init_db import init_db
from app.services.match_scheduler import match_scheduler

app = FastAPI(title="Hao Yu Backend")
(UPLOADS / "images").mkdir(parents=True, exist_ok=True)
app.mount("/uploads/images", StaticFiles(directory=UPLOADS / "images"), name="images")
(UPLOADS / 'videos').mkdir(parents=True, exist_ok=True)
app.mount('/uploads/videos', StaticFiles(directory=UPLOADS / 'videos'), name='videos')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    match_scheduler.start()


@app.on_event("shutdown")
def on_shutdown() -> None:
    match_scheduler.stop()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


app.include_router(profile.router)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(media.router, prefix="/media", tags=["media"])
app.include_router(integrations.router)
app.include_router(posts.router, prefix="/posts", tags=["posts"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(discovery.router, prefix="/discovery", tags=["discovery"])
app.include_router(content.router)
app.include_router(training.router, prefix="/training", tags=["training"])

app.include_router(social.router)

app.include_router(games.router)

app.include_router(clinic.router)
app.include_router(account.router)
app.include_router(notifications.router)
