# 로컬 실행 가이드

이 문서는 React 운영 화면과 분석 API, 인증 서비스를 로컬에서 함께 실행하는 절차다.

## 1. 구성과 포트

| 구성 요소 | 주소 또는 포트 | 용도 |
| --- | --- | --- |
| MySQL | `localhost:3306` | 분석·운영 데이터와 인증 데이터 저장 |
| 분석 FastAPI | `http://127.0.0.1:8000` | React의 분석·운영 API |
| 인증 FastAPI | `http://127.0.0.1:8100` | 로그인, 회원가입, 승인, 세션 |
| React / Vite | `http://localhost:5173` | 운영 서비스 화면 |

MySQL에는 다음 두 DB가 서로 분리되어 있어야 한다.

| DB | 역할 |
| --- | --- |
| `yelp_data` | Yelp 분석 데이터와 운영 판단·접촉·대상 명단 |
| `reviewer_retention_auth` | 로그인 계정, 세션, 가입 승인 감사 이력 |

인증 DB에는 `auth_users`, `auth_sessions`, `auth_approval_events` 테이블이 생성된다.
인증 계정은 Yelp 리뷰어 데이터의 `user_id`와 별개다.

## 2. 사전 확인

- MySQL 서버가 `3306` 포트에서 실행 중이어야 한다.
- `database/.env`에는 `yelp_data` 연결 정보가 있어야 한다.
- `auth_service/.env`에는 `reviewer_retention_auth` 연결 정보가 있어야 한다.
- `.env`, 인증 DB 비밀번호, `auth_service/auth_service.db`는 Git에 올리지 않는다.
- Python 가상환경을 사용하는 경우, 아래 명령을 실행할 모든 터미널에서 먼저 활성화한다.

```powershell
.\venv\Scripts\Activate.ps1
```

프로젝트 환경에 가상환경 경로가 다르면 해당 경로를 사용한다.

## 3. 최초 관리자 계정 생성

새 `reviewer_retention_auth` DB에는 최초 관리자 계정이 필요하다. 프로젝트 루트에서 다음을 한 번 실행한다.

```powershell
python -m auth_service.cli create-admin --username admin --name "관리자"
```

명령이 요청하는 비밀번호는 터미널에 표시되지 않는다. 비밀번호를 명령줄 인수나 Git 파일에 기록하지 않는다.

## 4. 서비스 실행

각 명령은 프로젝트 루트에서 별도 터미널로 실행한다.

### 터미널 1 — 분석 API

```powershell
python -m uvicorn api.main:app --reload --port 8000
```

분석 API 상태 확인:

```text
http://127.0.0.1:8000/health
```

### 터미널 2 — 인증 서비스

```powershell
python -m uvicorn auth_service.main:app --reload --port 8100
```

인증 서비스 주소:

```text
로그인:       http://127.0.0.1:8100/auth/login
회원가입:     http://127.0.0.1:8100/auth/signup
관리자 승인:  http://127.0.0.1:8100/auth/admin
API 문서:     http://127.0.0.1:8100/auth/docs
```

`auth_service/.env`를 변경한 뒤에는 인증 서버를 완전히 종료하고 다시 시작한다.

### 터미널 3 — React 운영 화면

```powershell
cd app
npm run dev
```

운영 화면:

```text
http://localhost:5173
```

React 개발 서버는 `/auth/*` 요청을 인증 서비스 `http://127.0.0.1:8100`으로 프록시한다. 따라서 일반적인 로그인 진입 주소는 다음을 사용한다.

```text
http://localhost:5173/auth/login
```

## 5. 로그인 흐름

```text
브라우저 (localhost:5173)
  -> Vite /auth 프록시
  -> 인증 서비스 (8100)
  -> reviewer_retention_auth
  -> 로그인 성공 후 React 운영 화면 또는 관리자 화면
```

관리자 계정은 로그인 성공 후 `/auth/admin`으로 이동한다. 승인된 일반 사용자는 `AUTH_AFTER_LOGIN_URL` 설정에 따라 React 운영 화면으로 돌아간다.

## 6. 자주 발생하는 문제

### `8100` 포트가 이미 사용 중인 경우

Windows CMD에서 현재 포트를 사용 중인 프로세스를 찾는다.

```cmd
netstat -ano | findstr :8100
tasklist /FI "PID eq <PID>"
```

확인한 인증 서버 프로세스만 종료한 뒤 다시 실행한다.

```cmd
taskkill /PID <PID> /F
```

### 새 인증 DB로 바꿨는데 로그인이 되지 않는 경우

1. 인증 서버를 완전히 종료한 뒤 다시 시작한다.
2. `auth_service/.env`의 `AUTH_DATABASE_URL`이 `reviewer_retention_auth`를 가리키는지 확인한다.
3. 새 DB에서 관리자 계정을 다시 생성했는지 확인한다. 기존 SQLite 계정은 자동으로 이전되지 않는다.

### React 화면은 열리지만 데이터가 보이지 않는 경우

분석 API `8000`이 실행 중인지와 `database/.env`가 `yelp_data`를 가리키는지 확인한다.

## 7. 로컬 서비스 한 번에 실행하기

프로젝트 루트의 `RUN_LOCAL.cmd`를 더블클릭하거나, Windows CMD에서 아래 명령을 실행한다.

```cmd
RUN_LOCAL.cmd
```

분석 API(8000), 인증 API(8100), React(5173) 중 멈춰 있는 서비스만 백그라운드에서 시작하고 상태표를 출력한다. 이미 실행 중인 서비스와 MySQL은 다시 시작하지 않는다.

상태만 확인하려면 다음 명령을 사용한다.

```cmd
powershell -ExecutionPolicy Bypass -File scripts\check_local_status.ps1
```

API 코드 변경 후 분석 API만 재시작하려면 다음 명령을 사용한다.

```cmd
powershell -ExecutionPolicy Bypass -File scripts\start_local.ps1 -RestartApi -ApiOnly
```

`RUN_LOCAL.cmd`와 보조 스크립트는 데이터베이스, pipeline, 애플리케이션 소스 파일을 변경하지 않는다.
