from fastapi import FastAPI
from .routes import router


app = FastAPI(
    title="Banking App API",
    description="API for managing bank accounts",
    version="1.0.0"
)


app.include_router(router)