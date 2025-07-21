from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Store Helper Bot API is alive."}
