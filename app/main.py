from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from app.routers import auth

app = FastAPI()

app.include_router(auth.router)
