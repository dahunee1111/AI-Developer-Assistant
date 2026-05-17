# 🚀 AI Developer Assistant

> AI 기반 개발 학습 및 코드 분석 지원 시스템  
> FastAPI · AI Analysis · Fullstack · AWS EC2 · Docker

---

# 🔗 Live Demo

## Frontend
https://dahunee1111.github.io/AI-Developer-Assistant/

## Backend API
https://dahun-ai.duckdns.org

---

# 📌 Project Overview

AI Developer Assistant는  
개발 과정에서 발생하는 에러 분석, 코드 리뷰, 학습 기록 관리, 출석 관리, 성장 시각화를 하나의 흐름으로 연결한  
AI 기반 개발 학습 지원 시스템입니다.

단순 기능 구현이 아니라,  
FastAPI 기반 백엔드 API 서버 구축, 데이터 저장 구조 설계, 프론트엔드 연동, 인증 처리, 실제 배포 및 운영까지 포함한  
풀스택 프로젝트 형태로 개발했습니다.

프론트엔드는 GitHub Pages로 배포하고,  
백엔드는 Docker 기반 환경에서 AWS EC2 서버에 배포한 뒤 DuckDNS 도메인을 연결하여 운영했습니다.

---

# ✨ Main Features

## 🧠 AI Error Analysis

- 에러 메시지 기반 원인 분석
- 해결 방향 및 수정 포인트 제공
- 개발 중 발생하는 문제를 빠르게 이해할 수 있도록 지원

---

## 💻 Code Review

- 코드 개선 방향 제안
- 리팩토링 포인트 분석
- 코드 품질 향상을 위한 피드백 제공

---

## 📚 Learning Journal

- 학습 내용 저장 및 관리
- 기록 기반 학습 흐름 유지
- 누적 학습 데이터 관리

---

## 📅 Attendance System

- 하루 1회 출석 체크
- 학습일 자동 계산
- 꾸준한 학습 루틴 관리

---

## 💰 Point System

- 출석, 분석, 기록 등 활동 기반 포인트 지급
- point_logs 테이블 기반 포인트 이력 저장
- SUM(amount) 방식의 총 포인트 계산 구조

---

## 🛒 Shop System

- 포인트 기반 아이템 구매
- 사용자 프로필 커스터마이징 기능
- 활동 보상 기반 서비스 구조

---

## 📊 Dashboard & Statistics

- 활동 데이터 기반 통계 제공
- 학습 성장 흐름 시각화
- Chart.js 기반 그래프 표시

---

## 🔐 Authentication System

- JWT 기반 로그인 인증 구조
- 사용자별 데이터 관리
- localStorage 기반 사용자 상태 유지
- API 요청 시 인증 토큰 활용

---

## 🤖 Floating AI Chatbot

- 사이트 우측 하단에 고정되는 플로팅 챗봇 UI
- 사용자가 어느 페이지에 있든 바로 질문 가능
- 프로젝트 설명, 기술 스택, EC2 배포 구조 안내
- Python / FastAPI 관련 질문 응답
- 오류 해결 순서 및 개발 흐름 안내
- 사용자별 챗봇 대화 기록 저장
- AI 응답 실패 시 기본 fallback 답변 제공
- 프로젝트 제작자 및 서비스 정보에 대한 고정 응답 처리

---

# 🛠 Tech Stack

## Backend

- Python
- FastAPI
- SQLite
- SQLAlchemy
- Pydantic
- JWT / python-jose

---

## Frontend

- HTML
- CSS
- JavaScript
- Chart.js

---

## AI

- Ollama
- Local AI Environment

---

## Deployment

- Docker
- AWS EC2
- DuckDNS
- GitHub Pages

---

# 🧩 System Architecture

```text
Frontend (GitHub Pages)
        ↓
Backend API (FastAPI + AWS EC2 + DuckDNS)
        ↓
AI Analysis / Service Logic
        ↓
SQLite Database
```

---

# 🌐 Deployment Architecture

```text
User Browser
        ↓
GitHub Pages Frontend
        ↓
https://dahun-ai.duckdns.org
        ↓
AWS EC2 Server
        ↓
Docker Container
        ↓
FastAPI Backend
        ↓
SQLite Database
```

---

# 🔥 Core Implementation Points

## 1. Frontend / Backend Separation

- 프론트엔드와 백엔드를 분리한 구조로 설계
- GitHub Pages에서 정적 프론트엔드 배포
- AWS EC2 서버에서 FastAPI 백엔드 운영
- API 기반 통신 구조 적용

---

## 2. AWS EC2 Backend Deployment

- AWS EC2 서버 환경 구성
- DuckDNS 도메인 연결
- `https://dahun-ai.duckdns.org` 백엔드 API 주소 사용
- 실제 외부 접속 가능한 API 서버 운영

---

## 3. Docker-Based Backend Environment

- Docker 기반 백엔드 실행 환경 구성
- 서버 환경 차이로 인한 실행 문제 최소화
- 배포 및 운영 안정성 향상

---

## 4. Log-Based Point System

- 모든 포인트 활동을 point_logs 테이블에 저장
- 출석, 분석, 기록 등 활동별 포인트 로그 관리
- SUM(amount) 방식으로 총 포인트 계산
- 로그 기반 구조로 데이터 신뢰성 확보

---

## 5. Learning Day Calculation Logic

- 출석 데이터와 학습 기록 데이터를 결합
- 실제 활동 기반 학습일 계산 구조 구현
- 학습 지속성을 확인할 수 있는 기능 구성

---

## 6. Authentication Flow

- JWT 기반 인증 시스템 구현
- 로그인 성공 시 accessToken 저장
- 사용자 정보와 토큰을 localStorage에 저장
- 인증이 필요한 API 요청에 토큰 활용

---

## 7. AI Analysis Flow

- 사용자가 에러 메시지 또는 코드를 입력
- FastAPI 백엔드가 분석 요청 처리
- AI 분석 결과 생성
- 결과를 프론트엔드에 반환
- 필요 시 분석 기록 저장

---

# 📁 Main Pages

- Login Page
- Signup Page
- Main Dashboard
- Study / Journal Page
- Error Analysis Page
- Exam / Quiz Page
- Shop Page
- Admin Page

---

# 📈 Future Improvements

- PostgreSQL 도입
- Redis 캐싱 적용
- AI 분석 기능 고도화
- 사용자 맞춤 학습 추천
- 실시간 AI 질문 기능
- 관리자 기능 확장
- 배포 자동화 개선
- HTTPS 및 서버 운영 안정성 강화

---

# 🧠 What I Learned

이 프로젝트를 통해 단순한 기능 구현을 넘어서  
실제 서비스 개발 과정에서 중요한 전체 흐름을 경험했습니다.

특히 다음과 같은 부분을 직접 다루었습니다.

- FastAPI 기반 API 설계
- 프론트엔드와 백엔드 분리 구조
- JWT 인증 흐름
- SQLite 기반 데이터 저장
- 로그 기반 포인트 계산 구조
- GitHub Pages 프론트엔드 배포
- Docker 기반 백엔드 실행 환경 구성
- AWS EC2 서버 배포
- DuckDNS 도메인 연결
- 실제 외부 접속 가능한 서비스 운영

AI 기능을 웹 서비스 흐름 안에 연결하면서,  
AI 모델 또는 AI 분석 기능이 실제 사용자 화면과 데이터 저장 구조까지 이어지는  
서비스형 AI 시스템 구조에 대한 이해를 높일 수 있었습니다.

---

# 👨‍💻 Developer

전다훈

- AI Developer
- Backend Developer
- FastAPI / AI System Development

GitHub:  
https://github.com/dahunee1111

Portfolio:  
https://dahunee1111.github.io/Main/index.html

---

# ⭐ Summary

AI 분석, 코드 리뷰, 학습 관리, 데이터 시각화, 인증 시스템, 포인트 시스템,  
Docker 기반 백엔드 실행 환경, AWS EC2 배포, DuckDNS 도메인 연결까지 경험한  
실제 서비스형 AI 개발 학습 지원 시스템 프로젝트입니다.
