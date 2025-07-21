from fastapi import FastAPI
from app.routers import chat

app = FastAPI()

app.include_router(chat.router, prefix="/chat", tags=["Chat"])

@app.get("/")
async def root():
    return {"message": "Store Helper Bot API is alive."}
