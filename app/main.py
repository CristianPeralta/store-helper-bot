from fastapi import FastAPI
from app.routers import chat
from app.db import init_models
from dotenv import load_dotenv
from contextlib import asynccontextmanager
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()  # Initialize models and database
    yield
    # (Optional) Code to close connections or other resources

app = FastAPI(lifespan=lifespan)

app.include_router(chat.router, prefix="/chat", tags=["Chat"])

@app.get("/")
async def root():
    return {"message": "Store Helper Bot API is alive."}
