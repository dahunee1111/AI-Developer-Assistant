from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS 설정 (프론트 연결용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "API is working"}

@app.post("/analyze")
def analyze_error(data: dict):
    error = data.get("error", "")

    # 🔥 MVP용 간단 분석 (나중에 AI로 바꿀 예정)
    if "ModuleNotFoundError" in error:
        return {"result": "pip install 패키지를 설치하세요"}
    elif "SyntaxError" in error:
        return {"result": "문법 오류를 확인하세요"}
    else:
        return {"result": "에러를 분석 중입니다..."}
