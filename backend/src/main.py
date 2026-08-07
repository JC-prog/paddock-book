from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.modules.auth.router import router as auth_router
from src.modules.chat.router import router as chat_router
from src.modules.health.router import router as health_router

app = FastAPI(title="PaddockBook API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(auth_router)
