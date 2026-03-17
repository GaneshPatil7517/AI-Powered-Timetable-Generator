from fastapi import FastAPI
from app.database import engine
from fastapi.middleware.cors import CORSMiddleware
import os

from app import models
from app.routers.inputs import router as input_router
from app.routers.timetable_new import router as timetable_router

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Timetable Generator",
    docs_url="/docs",
    redoc_url="/redoc"
)

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],   # frontend URL configured via FRONTEND_ORIGIN
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(input_router, prefix="/api", tags=["Inputs"])
app.include_router(timetable_router, prefix="/api", tags=["Timetable"])
