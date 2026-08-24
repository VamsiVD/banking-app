from fastapi import FastAPI
from app.routers import applications

app = FastAPI()

app.include_router()


