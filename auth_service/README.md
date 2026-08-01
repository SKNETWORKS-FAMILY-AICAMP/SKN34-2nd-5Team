# Reviewer Retention Auth Service

기존 React `app/`, 분석 API `api/`, MySQL `yelp_data`, 모델 파이프라인과 분리된 회원가입·로그인·관리자 승인 서비스다.

React 담당자가 인수해 기존 운영 화면과 연결할 때는 [`REACT_INTEGRATION.md`](REACT_INTEGRATION.md)를 먼저 확인한다.

## 제공 기능

- 일반 사용자 회원가입과 `PENDING` 상태 저장
- Argon2 비밀번호 해시
- 승인 전 로그인 차단
- 서버에서만 생성하는 관리자 계정
- 관리자 가입 신청 조회·승인·거절
- 승인 시 `VIEWER`·`OPERATOR` 권한 부여 및 승인 후 권한 변경
- DB 기반 불투명 세션과 HttpOnly 쿠키
- 관리자 변경 요청 CSRF 검증
- 가입·승인·거절 감사 이력
- 발표용 독립 UI와 수동 `새로고침` 조회
- React 연동용 OpenAPI 문서

## 로컬 실행

프로젝트 루트에서 실행한다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r auth_service\requirements.txt
.\.venv\Scripts\python.exe -m auth_service.cli create-admin --username presentation_admin --name "발표 관리자"
.\.venv\Scripts\python.exe -m uvicorn auth_service.main:app --reload --port 8100
```

비밀번호 인수가 없으면 터미널에서 가려진 상태로 입력한다. 브라우저 주소는 다음과 같다.

- 회원가입: `http://127.0.0.1:8100/auth/signup`
- 로그인: `http://127.0.0.1:8100/auth/login`
- 관리자 승인: `http://127.0.0.1:8100/auth/admin`
- API 문서: `http://127.0.0.1:8100/auth/docs`

별도 환경변수가 없으면 `auth_service/auth_service.db` SQLite 파일을 만들며 Git에는 포함하지 않는다.

## 발표 순서

1. 사용자 브라우저에서 회원가입을 신청한다.
2. 승인 대기 안내와 승인 전 로그인 차단을 확인한다.
3. 관리자 브라우저에서 로그인한다.
4. 가입 승인 관리 화면의 `새로고침`을 누른다.
5. 방금 가입한 사용자를 승인한다.
6. 승인 완료 목록에서 회원 권한을 변경하고 새로고침해 결과를 확인한다.
7. 사용자 브라우저에서 다시 로그인해 승인된 회원 정보를 확인한다.

관리자와 일반 사용자 쿠키가 섞이지 않도록 서로 다른 브라우저 프로필 또는 시크릿 창을 사용한다.

## AWS 연결 전 조건

- 기존 `yelp_data`가 아닌 `reviewer_retention_auth` 같은 별도 DB를 만든다.
- 해당 DB만 읽고 쓸 수 있는 전용 DB 계정을 만든다.
- `.env.example`을 참고해 서버의 `.env`를 작성한다. 실제 비밀값은 Git에 올리지 않는다.
- 도메인과 HTTPS를 먼저 적용하고 `AUTH_COOKIE_SECURE=true`를 사용한다.
- Nginx에서 `/auth`를 이 서비스로 연결한다.
- 운영 전에는 로그인 시도 제한, 비밀번호 재설정과 운영 백업 정책을 추가한다.

AWS 배포 및 원격 DB 생성은 이 디렉터리를 로컬에서 검증하는 것과 별개의 작업이다.
