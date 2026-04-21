from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.auth import router as auth_router
from routers.study import router as study_router
from routers.exam import router as exam_router
from routers.shop import router as shop_router
from routers.profile import router as profile_router
from routers.admin import router as admin_router
from db import init_db, seed_exam_data, seed_shop_items

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
