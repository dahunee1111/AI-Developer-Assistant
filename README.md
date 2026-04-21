# 🚀 AI Developer Assistant

> 개발자를 위한 AI 기반 에러 분석 및 학습 도우미 서비스

## 🔗 Demo
https://dahunee1111.github.io/AI-Developer-Assistant/

---

## 📌 프로젝트 소개

AI Developer Assistant는 개발 중 발생하는 에러를 분석하고,  
코드 리뷰 및 학습 기록을 통해 개발자의 성장을 돕는 웹 서비스입니다.

FastAPI 기반 백엔드와 HTML/CSS/JavaScript 프론트를 분리하여  
실제 배포까지 진행한 풀스택 프로젝트입니다.

---

## ✨ 주요 기능

### 🧠 AI 에러 분석
- 에러 메시지 입력 시 원인 및 해결 방법 분석

### 💻 코드 리뷰
- 코드 개선 포인트 및 리팩토링 방향 제시

### 📚 학습 기록 (Journal)
- 학습 내용 저장 및 관리

### 📅 출석 시스템
- 하루 1회 출석 체크
- 학습일 자동 계산

### 💰 포인트 시스템
- 출석, 분석, 기록 등 활동 기반 포인트 지급
- 로그 기반 포인트 계산 구조

### 🛒 상점 시스템
- 포인트로 아이템 구매
- 프로필 커스터마이징

### 📊 통계
- 활동 데이터 기반 통계 제공

---

## 🛠 기술 스택

### Backend
- FastAPI
- SQLite
- Pydantic

### Frontend
- HTML
- CSS
- JavaScript (Vanilla)

### Deployment
- Backend: Render
- Frontend: GitHub Pages

---

## 🧩 시스템 구조

Frontend (GitHub Pages)  
→ Backend (FastAPI - Render)  
→ Database (SQLite)

---

## 🔥 핵심 구현 포인트

### 1. 로그 기반 포인트 시스템
- point_logs 테이블에 모든 포인트 기록 저장
- SUM(amount) 방식으로 총 포인트 계산

### 2. 학습일 계산 로직
- 출석 데이터 + 학습 기록 데이터 결합
- 실제 학습일 기준으로 계산

### 3. 프론트/백엔드 분리 구조
- API 기반 통신 구조
- 독립 배포 가능

### 4. 실제 배포 경험
- GitHub Pages + Render 연동
- 환경별 API 분기 처리

---

## 🧠 느낀 점

단순 기능 구현을 넘어 실제 서비스 형태로 배포하면서  
전체 시스템 흐름과 API 설계의 중요성을 경험했습니다.

---

## 📌 향후 개선

- PostgreSQL 도입
- JWT 인증 적용
- AI 기능 고도화
- UI/UX 개선

---

## 👨‍💻 개발자

전다훈

---

## ⭐ 한 줄 요약

AI 기반 개발 도우미 서비스를 설계하고 실제 배포까지 완료한 풀스택 프로젝트
