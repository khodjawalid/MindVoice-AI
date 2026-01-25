from fastapi import FastAPI
from app.api.routers.metrics import router as metrics_router
from app.api.routers.wellness import router as wellness_router
from app.api.routers.sync import router as sync_router
from app.api.routers.dashboard import router as dashboard_router
from app.api.routers.inference import router as inference_router
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metrics_router)
app.include_router(wellness_router)
app.include_router(sync_router)
app.include_router(dashboard_router)
app.include_router(inference_router)
