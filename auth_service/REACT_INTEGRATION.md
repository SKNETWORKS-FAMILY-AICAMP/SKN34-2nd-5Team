# React 담당자 전달 문서

작성 기준: 2026-08-01

이 문서는 기존 React 운영 화면 `app/`과 독립 인증 서비스 `auth_service/`를 연결하기 위한 인수인계 문서다. 현재까지 `app/`은 수정하지 않았으며, 인증 화면과 백엔드는 `auth_service/` 안에만 구현되어 있다.

**2026-08-01 갱신**: 아래 8절에서 권장한 최소 연동 구조를 `app/`에 적용했다.
`app/src/features/auth/`(`authApi.js`, `AuthProvider.jsx`, `auth-context.js`,
`ProtectedRoute.jsx`, `rolePolicy.js`)를 추가하고 `App.jsx`를
`AuthProvider` + `ProtectedRoute`로 감쌌다. `vite.config.js`에 `/auth`
프록시(9절)도 추가했다. 로그인→React 이동, 로그아웃→`/auth/login` 복귀,
관리자 로그인→`/auth/admin` 이동까지 로컬에서 실제로 확인했다. 이 화면
자체(Jinja 템플릿)는 변경하지 않았다 — React 쪽 연동만 추가한 것이다.

## 1. 현재 구현 상태

구현 완료:

- 회원가입 및 `PENDING` 상태 저장
- 이메일 또는 관리자 아이디 로그인
- Argon2 비밀번호 해시
- DB 기반 세션과 HttpOnly 쿠키
- 승인 전 로그인 차단
- 관리자 가입 승인·거절
- 승인 시 `VIEWER` 또는 `OPERATOR` 권한 부여
- 승인된 회원의 권한 변경
- 가입·승인·거절·권한 변경 감사 이력
- 관리자 목록 수동 새로고침
- 로그인 상태에 따른 상단 메뉴 변경
- 로그인 사용자의 로그인·회원가입 화면 재접근 방지

- React `app/` 내부 라우터·상태 관리와 연결(§8 최소 구조: `AuthProvider`,
  `ProtectedRoute`, Vite `/auth` 프록시)

아직 하지 않은 작업:

- 역할별(VIEWER/OPERATOR/ADMIN) 화면 내 버튼·액션 숨김 — `rolePolicy.js`에
  `canMutate()` 헬퍼만 추가했고, 개별 화면(판단 저장, 대상 명단 추가 등)에
  아직 연결하지 않았다
- 기존 React 화면 및 분석 API의 실제 접근 차단(Nginx `/auth/api/verify`
  서브리퀘스트 또는 `api/` 자체 인증 검사) — 지금은 React 라우팅만
  보호되고, `/api`를 직접 호출하면 그대로 응답한다
- AWS 회원 DB 연결
- AWS 인증 서비스 배포
- 도메인·HTTPS 적용

## 2. Git으로 전달되는 것과 전달되지 않는 것

Git으로 전달되는 것:

- `auth_service/` 소스 코드
- 독립 회원가입·로그인·관리자 화면
- API와 데이터 모델
- 자동 테스트
- `.env.example`과 실행 문서

Git으로 전달되지 않는 것:

- `auth_service/auth_service.db`
- 현재 로컬에서 만든 관리자·회원 계정
- 로그인 세션
- 실제 `.env`와 비밀번호

`auth_service/auth_service.db`는 `.gitignore` 대상이다. 코드를 받은 컴퓨터에서는 빈 로컬 DB가 새로 생성되며 관리자도 다시 만들어야 한다. DB 파일이나 실제 관리자 비밀번호를 Git에 추가하지 않는다.

## 3. 로컬 실행

프로젝트 루트에서 실행한다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r auth_service\requirements.txt
.\.venv\Scripts\python.exe -m auth_service.cli create-admin --username presentation_admin --name "발표 관리자"
.\.venv\Scripts\python.exe -m uvicorn auth_service.main:app --reload --port 8100
```

관리자 생성 명령에서 `--password`를 생략하면 터미널에서 비밀번호를 가려서 입력한다.

주요 주소:

| 화면 | 주소 |
|---|---|
| 회원가입 | `http://127.0.0.1:8100/auth/signup` |
| 로그인 | `http://127.0.0.1:8100/auth/login` |
| 관리자 회원 관리 | `http://127.0.0.1:8100/auth/admin` |
| 승인 회원 정보 | `http://127.0.0.1:8100/auth/profile` |
| Swagger | `http://127.0.0.1:8100/auth/docs` |

## 4. 현재 화면 동작

- 비로그인 상태 상단: `회원가입 / 로그인`
- 로그인 상태 상단: `로그아웃`
- 로그인 사용자 로고 클릭: 공통 운영 홈 `/`
- 비로그인 사용자 로고 클릭: `/auth/login`
- 로그인 사용자가 `/auth/login` 또는 `/auth/signup`에 직접 접근하면 공통 운영 홈으로 이동
- 관리자와 일반 회원 로그인 성공: `AUTH_AFTER_LOGIN_URL`

로그인 후 관리자와 일반 회원을 공통 운영 홈으로 보낼 경우 서버 환경변수를 다음과 같이 설정한다.

```dotenv
AUTH_AFTER_LOGIN_URL=/
```

관리자 승인 화면은 `/auth/admin`에서 계속 이용할 수 있으며, React 설정 메뉴에서 접근한다.

## 5. 계정 상태와 권한

계정 상태:

| 값 | 의미 |
|---|---|
| `PENDING` | 가입 승인 대기 |
| `APPROVED` | 로그인 가능한 승인 계정 |
| `REJECTED` | 가입 거절 |
| `SUSPENDED` | 사용 중지 |

접근 권한:

| 값 | 의미 | 생성·부여 방식 |
|---|---|---|
| `VIEWER` | 조회 전용 | 관리자가 승인 또는 권한 변경 시 부여 |
| `OPERATOR` | 운영 업무 수행 | 관리자가 승인 또는 권한 변경 시 부여 |
| `ADMIN` | 회원 승인 및 권한 관리 | 서버의 `create-admin` 명령으로만 생성 |

일반 회원을 API로 `ADMIN`으로 승격할 수 없도록 제한되어 있다.

## 6. 핵심 API

| 기능 | 메서드·경로 | 인증 |
|---|---|---|
| 회원가입 | `POST /auth/api/register` | 없음 |
| 로그인 | `POST /auth/api/login` | 없음 |
| 내 정보 | `GET /auth/api/me` | 승인 사용자 |
| 로그아웃 | `POST /auth/api/logout` | 승인 사용자 + CSRF |
| 접근 확인 | `GET /auth/api/verify` | 승인 사용자 |
| 상태별 회원 목록 | `GET /auth/api/admin/users?status=PENDING` | 관리자 |
| 가입 승인 | `POST /auth/api/admin/users/{userId}/approve` | 관리자 + CSRF |
| 가입 거절 | `POST /auth/api/admin/users/{userId}/reject` | 관리자 + CSRF |
| 승인 회원 권한 변경 | `PATCH /auth/api/admin/users/{userId}/role` | 관리자 + CSRF |

정확한 요청·응답 필드는 실행 서버의 `/auth/docs`를 기준으로 한다.

### 로그인

일반 회원은 이메일, 관리자는 아이디를 `identifier`에 전달한다.

```js
const response = await fetch("/auth/api/login", {
  method: "POST",
  credentials: "include",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ identifier, password }),
});

const result = await response.json();
```

로그인 성공 응답의 주요 필드:

```json
{
  "message": "로그인되었습니다.",
  "user": {
    "id": "uuid",
    "username": "admin_id_or_null",
    "email": "member@example.com",
    "status": "APPROVED",
    "access_role": "VIEWER",
    "is_admin": false
  },
  "redirect_to": "/auth/profile"
}
```

### 현재 사용자 확인

React 앱이 시작될 때 한 번 호출해 로그인 상태를 복원한다.

```js
const response = await fetch("/auth/api/me", {
  credentials: "include",
});
```

- `200`: 로그인 사용자 정보를 React 상태에 저장
- `401`: 미로그인으로 처리
- `403`: 승인되지 않았거나 사용할 수 없는 계정으로 처리
- 확인이 끝날 때까지 보호 화면을 먼저 렌더링하지 말고 로딩 상태를 둔다.

### 승인·권한 변경

승인 요청:

```json
{
  "access_role": "OPERATOR",
  "note": "관리자 승인"
}
```

권한 변경 요청:

```json
{
  "access_role": "VIEWER",
  "note": "조회 전용으로 변경"
}
```

관리자 목록은 실시간 구독하지 않는다. 새로고침 버튼을 누를 때 아래 두 API를 다시 호출한다.

```text
GET /auth/api/admin/users?status=PENDING
GET /auth/api/admin/users?status=APPROVED
```

## 7. 쿠키와 CSRF

로그인 성공 시 서버가 다음 쿠키를 발급한다.

| 쿠키 | 용도 | JavaScript 접근 |
|---|---|---|
| `rr_auth_session` | 인증 세션 | 불가, HttpOnly |
| `rr_auth_csrf` | 변경 요청 검증 | 가능 |

모든 인증 API 호출에 다음 설정을 사용한다.

```js
credentials: "include"
```

로그아웃·승인·거절·권한 변경 요청에는 `rr_auth_csrf` 값을 `X-CSRF-Token` 헤더로 전달한다.

```js
function getCsrfToken() {
  const item = document.cookie
    .split("; ")
    .find((value) => value.startsWith("rr_auth_csrf="));
  return item ? decodeURIComponent(item.split("=").slice(1).join("=")) : "";
}

await fetch(`/auth/api/admin/users/${userId}/role`, {
  method: "PATCH",
  credentials: "include",
  headers: {
    "Content-Type": "application/json",
    "X-CSRF-Token": getCsrfToken(),
  },
  body: JSON.stringify({ access_role: "VIEWER", note: "권한 변경" }),
});
```

세션 기본 유지시간은 8시간이다. 로그아웃하면 DB 세션을 폐기하고 두 쿠키를 삭제한다.

## 8. React 연결 권장 구조

독립 인증 화면을 유지하면서 React와 연결하는 최소 구조:

```text
미로그인 사용자가 React 접속
  → 인증 확인 실패
  → /auth/login 이동
  → 로그인 성공 및 쿠키 발급
  → React / 이동
  → /auth/api/me로 사용자·권한 복원
```

React 담당자가 추가할 권장 모듈:

```text
app/src/features/auth/
├─ authApi.js
├─ AuthProvider.jsx
├─ ProtectedRoute.jsx
└─ rolePolicy.js
```

역할별 화면 정책 예시:

- `ADMIN`: 기존 운영 화면 전체 + `/auth/admin` 회원 관리 링크
- `OPERATOR`: 운영에 필요한 화면과 액션
- `VIEWER`: 조회 화면만 허용하고 변경 액션 숨김

중요: React에서 메뉴나 버튼을 숨기는 것은 사용자 경험 처리일 뿐 보안 경계가 아니다. 직접 URL 및 API 호출도 차단하려면 Nginx 또는 기존 FastAPI에서 권한을 다시 확인해야 한다.

## 9. Vite 개발 환경 연결

React와 인증 서비스를 서로 다른 포트로 실행할 때는 React 개발 서버에서 `/auth`를 프록시하는 방식을 권장한다. React 담당자가 현재 Vite 설정 형식에 맞게 추가한다.

```js
server: {
  proxy: {
    "/auth": {
      target: "http://127.0.0.1:8100",
      changeOrigin: true,
    },
  },
}
```

React에서는 API 주소를 `http://127.0.0.1:8100`으로 하드코딩하지 않고 `/auth/api/...` 상대 경로로 호출한다.

프록시를 사용하지 않고 직접 교차 출처로 호출한다면 `AUTH_ALLOWED_ORIGINS` 설정이 필요하다. `localhost`와 `127.0.0.1`을 섞으면 쿠키가 전달되지 않을 수 있으므로 호스트명을 통일한다.

## 10. 배포 구조

권장 운영 경로:

```text
Nginx
├─ /          → React 정적 빌드
├─ /api       → 기존 분석 FastAPI
└─ /auth      → auth_service:8100
```

React와 인증 서비스를 같은 도메인에 두면 쿠키와 CORS 구성이 단순해진다. `/auth`는 로그인 전에도 접근할 수 있어야 하므로 React 보호 규칙에서 제외한다.

기존 React 화면을 실제로 보호하려면 Nginx의 인증 서브리퀘스트에서 다음 엔드포인트를 사용한다.

```text
GET /auth/api/verify
```

이 엔드포인트는 승인된 세션이면 `204`를 반환하고 다음 헤더를 제공한다.

```text
X-Auth-User-Id
X-Auth-User-Email
X-Auth-Is-Admin
X-Auth-Role
```

기존 분석 API `/api`도 보호하지 않으면 사용자가 React를 거치지 않고 직접 호출할 수 있다. 화면과 API의 보호 범위를 함께 결정해야 한다.

## 11. AWS DB 연결 시

기존 `yelp_data`를 사용하지 않고 별도 DB를 사용한다.

```text
reviewer_retention_auth
├─ auth_users
├─ auth_sessions
└─ auth_approval_events
```

필요 환경변수 예시는 `auth_service/.env.example`에 있다.

```dotenv
AUTH_DATABASE_URL=mysql+pymysql://auth_app:URL_ENCODED_PASSWORD@DB_HOST/reviewer_retention_auth?charset=utf8mb4
AUTH_COOKIE_SECURE=true
AUTH_AFTER_LOGIN_URL=/
```

AWS 연결만으로 현재 로컬 계정이 자동 이전되지는 않는다. 운영 DB에서는 관리자와 시연 회원을 다시 생성하는 방식을 권장한다.

실제 비밀번호를 사용하는 배포는 도메인과 HTTPS가 준비된 후 진행한다. 현재 공개 IP의 HTTP 주소에서는 운영 계정을 사용하지 않는다.

## 12. 주요 오류 코드

오류는 보통 다음 형태로 반환된다.

```json
{
  "detail": {
    "code": "approval_pending",
    "message": "관리자 승인 대기 중입니다."
  }
}
```

주요 코드:

| 코드 | 의미 |
|---|---|
| `invalid_credentials` | 아이디·이메일 또는 비밀번호 불일치 |
| `approval_pending` | 관리자 승인 대기 |
| `account_unavailable` | 거절·중지 등 사용할 수 없는 계정 |
| `not_authenticated` | 로그인 필요 |
| `invalid_session` | 유효하지 않은 세션 |
| `expired_session` | 세션 만료 |
| `admin_required` | 관리자 권한 필요 |
| `csrf_failed` | CSRF 검증 실패 |
| `registration_unavailable` | 중복 등의 이유로 가입 처리 불가 |
| `already_decided` | 이미 처리된 가입 신청 |
| `user_not_approved` | 승인되지 않은 회원의 권한 변경 시도 |

## 13. 인수 후 확인 순서

1. 새 관리자 계정을 로컬에서 생성한다.
2. `auth_service`를 8100 포트로 실행한다.
3. 회원가입 → 승인 대기 → 승인 전 로그인 차단을 확인한다.
4. 관리자로 로그인해 `VIEWER` 또는 `OPERATOR` 권한으로 승인한다.
5. 승인 회원의 권한을 변경하고 새로고침해 반영을 확인한다.
6. 일반 회원 로그인 후 `/auth/api/me` 응답을 확인한다.
7. Vite `/auth` 프록시와 `credentials: "include"`를 적용한다.
8. React 초기 로딩에서 `/auth/api/me`로 사용자 상태를 복원한다.
9. 미로그인·권한별 React 라우팅을 검증한다.
10. Nginx 또는 API의 서버 측 접근 차단을 검증한다.
11. React 린트·빌드와 기존 전체 화면·데이터 조회를 회귀 테스트한다.

## 14. 테스트

프로젝트 루트에서 실행한다.

```powershell
.\.venv\Scripts\python.exe -m pytest auth_service\tests -q
.\.venv\Scripts\python.exe -m pytest -q
```

현재 기준 전체 테스트는 32개가 통과한다. 테스트 경고 중 `.pytest_cache` 접근 경고는 이 Windows 작업공간의 캐시 권한 문제이며 기능 실패는 아니다.
