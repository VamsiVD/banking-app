from fastapi import FastAPI
from app.routers import BankProfile

app = FastAPI()

app.include_router(BankProfile.router)


