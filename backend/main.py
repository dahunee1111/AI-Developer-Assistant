from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from backend.routers.auth import router as auth_router
    from backend.routers.study import router as study_router
    from backend.routers.exam import router as exam_router
    from backend.routers.shop import router as shop_router
    from backend.routers.profile import router as profile_router
    from backend.routers.admin import router as admin_router
    from backend.db import init_db, seed_exam_data, seed_shop_items
    from backend.settings import CORS_ALLOW_ORIGINS
except ImportError:
    from routers.auth import router as auth_router
    from routers.study import router as study_router
    from routers.exam import router as exam_router
    from routers.shop import router as shop_router
    from routers.profile import router as profile_router
    from routers.admin import router as admin_router
    from db import init_db, seed_exam_data, seed_shop_items
    from settings import CORS_ALLOW_ORIGINS

app = FastAPI(
    title="AI Developer Assistant API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
seed_exam_data()
seed_shop_items()

app.include_router(auth_router)
app.include_router(study_router)
app.include_router(exam_router)
app.include_router(shop_router)
app.include_router(profile_router)
app.include_router(admin_router)

@app.get("/")
def root():
    return {"message": "AI Developer Assistant API is working"}


@app.get("/health")
def health():
    return {"status": "ok"}
