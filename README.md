# 🚀 AI Developer Assistant

> AI 기반 개발 학습 및 코드 분석 지원 시스템  
> FastAPI · AI Analysis · Fullstack · Deployment

---

# 🔗 Live Demo

## Frontend
https://dahunee1111.github.io/AI-Developer-Assistant/

## Backend API
https://ai-developer-assistant-0wz0.onrender.com

---

# 📌 Project Overview

AI Developer Assistant는  
개발 과정에서 발생하는 에러 분석, 학습 기록 관리, 출석 관리, 성장 시각화를 하나의 흐름으로 연결한  
AI 기반 개발 학습 지원 시스템입니다.

단순 기능 구현이 아니라,  
FastAPI 기반 백엔드 API 서버 구축, 데이터 저장 구조 설계, 프론트엔드 연동, 실제 배포 및 운영까지 포함한  
풀스택 프로젝트 형태로 개발했습니다.

또한 Docker 및 AWS EC2 환경을 활용해  
실제 서버 배포와 운영 경험까지 함께 진행했습니다.

---

# ✨ Main Features

## 🧠 AI Error Analysis

- 에러 메시지 기반 원인 분석
- 해결 방향 및 수정 포인트 제공

---

## 💻 Code Review

- 코드 개선 방향 제안
- 리팩토링 포인트 분석

---

## 📚 Learning Journal

- 학습 내용 저장 및 관리
- 기록 기반 학습 흐름 유지

---

## 📅 Attendance System

- 하루 1회 출석 체크
- 학습일 자동 계산

---

## 💰 Point System

- 활동 기반 포인트 지급
- 로그 기반 포인트 계산 구조

---

## 🛒 Shop System

- 포인트 기반 아이템 구매
- 프로필 커스터마이징 기능

---

## 📊 Dashboard & Statistics

- 활동 데이터 시각화
- 성장 흐름 그래프 제공

---

## 🔐 Authentication System

- JWT 기반 로그인 인증 구조
- 사용자 상태 관리

---

# 🛠 Tech Stack

## Backend

- Python
- FastAPI
- SQLite
- SQLAlchemy
- Pydantic
- JWT (python-jose)

---

## Frontend

- HTML
- CSS
- JavaScript (Vanilla)
- Chart.js

---

## AI

- Ollama
- Local AI Environment

---

## Deployment

- Docker
- AWS EC2
- Render
- GitHub Pages

---

# 🧩 System Architecture

```text
Frontend (GitHub Pages)
        ↓
FastAPI Backend API
        ↓
AI Analysis / Database
        ↓
SQLite Storage
```

---

# 🔥 Core Implementation Points

## 1. Log-Based Point System

- 모든 포인트 활동을 point_logs 테이블에 저장
- SUM(amount) 방식으로 총 포인트 계산
- 로그 기반 구조로 데이터 신뢰성 확보

---

## 2. Learning Day Calculation Logic

- 출석 데이터와 학습 기록 데이터를 결합
- 실제 활동 기반 학습일 계산 구조 구현

---

## 3. Frontend / Backend Separation

- API 기반 통신 구조 설계
- 프론트엔드와 백엔드 독립 배포 가능
- 유지보수 및 확장성 고려

---

## 4. Authentication Flow

- JWT 기반 인증 시스템 구현
- localStorage 기반 사용자 상태 유지
- API 요청 인증 구조 적용

---

## 5. Real Deployment Experience

- GitHub Pages + Render 연동
- Docker 기반 실행 환경 구성
- AWS EC2 서버 배포 경험
- 환경별 API 분기 처리

---

# 📈 Future Improvements

- PostgreSQL 도입
- Redis 캐싱 적용
- AI 분석 기능 고도화
- 사용자 맞춤 학습 추천
- 실시간 AI 질문 기능
- 관리자 기능 확장
- Docker 기반 운영 환경 개선

---

# 🧠 What I Learned

단순 기능 구현을 넘어서,  
실제 서비스 구조에서 중요한:

- API 설계
- 데이터 흐름
- 인증 구조
- 배포 환경
- 프론트/백엔드 연결
- 운영 및 유지보수

과정을 직접 경험할 수 있었습니다.

특히 AI 기능을 실제 웹 서비스 흐름 안에 연결하는 과정에서  
서비스형 AI 시스템 구조에 대한 이해를 높일 수 있었습니다.

---

# 👨‍💻 Developer

전다훈

- AI Developer
- Backend Developer
- FastAPI / AI System Development

GitHub:
https://github.com/dahunee1111

---

# ⭐ Summary

AI 분석, 학습 관리, 데이터 시각화, 인증 시스템, 배포 환경까지 연결하여  
실제 서비스 형태로 구현 및 운영한 AI 기반 개발 학습 지원 시스템 프로젝트.
