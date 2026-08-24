# A 영역 서버·배포 보안 실행 결과 — 2026-08-24

- 기준 브랜치: `main`
- 기준 commit: `a095375`
- 작업 범위: `api/`, `auth_service/`, 배포 설정, 서버 자동 테스트
- 제외 범위: React `app/` 소스 수정
- 상태 표기: `PASS`, `FAIL`, `PARTIAL`, `NOT RUN`

과거 실행 증거인 `ADMIN_UI_QA_EXECUTION_2026-08-05.md`는 변경하지 않았다.
이번 문서는 현재 main 위 작업 트리에서 새로 확인한 결과만 기록한다.

## 1. 결과 요약

| ID | 결과 | 이번 실행의 실제 근거 | 남은 조건 |
|---|---|---|---|
| A01 | PASS | 미인증 retention 조회 200을 재현한 뒤 전체 `/api/retention/*`에 인증 경계 적용. 미로그인 401, 인증 서비스 장애 503 자동 테스트 통과 | 변경본 배포 후 공개 API smoke test |
| A02 | PASS | `auth_service`의 `region_code`를 API identity에 연결. OPERATOR 자기 권역 조회·저장 허용, 타 권역 리뷰어·지역 운영안 403, VIEWER 저장 403 테스트 통과 | 변경본 배포 후 실제 역할 계정 smoke test |
| A03 | FAIL | 배포 설정은 HTTPS origin, 443 SSL listener, HTTP redirect, 공개 HTTPS smoke test를 강제하도록 보완. 2026-08-24 실제 운영 주소는 HTTP 200이며 HTTPS는 10초 내 응답하지 않음 | 도메인·인증서·Nginx 실제 적용 및 재배포 |
| A04 | PARTIAL | 운영 모드에서 Secure Cookie가 꺼지면 인증 서비스 시작 거부. HTTPS 테스트에서 세션 `Secure·HttpOnly·SameSite`, CSRF `Secure·SameSite` 확인 | AWS `AUTH_ENV=production`, `AUTH_COOKIE_SECURE=true` 적용 후 공개 확인 |
| A05 | PASS | 개발 CORS 정규식과 운영 명시 origin 분리. credentialed `*` 금지, 허용/비허용 origin 테스트 통과 | 실제 운영 origin 환경변수 적용 |
| A06 | PARTIAL | 실제 MySQL 트랜잭션에서 스누즈 저장→재조회 일치 확인 후 전체 롤백 | React 화면 새로고침·재로그인 복원 QA는 app 범위 |
| A07 | PARTIAL | 판단 History API에 메모·담당자 subject·스누즈 변경 전후를 추가하고 실제 MySQL에서 검증 | React History 화면 표시 QA는 app 범위 |
| A08 | NOT RUN | React 전체 차단 제거는 이번 범위 밖 | app 수정 필요 |
| A09 | NOT RUN | React Decision Gate 변경은 이번 범위 밖 | app 수정 필요 |
| A10 | NOT RUN | 사진·지도 부분 fallback은 이번 범위 밖 | app 수정 필요 |
| A11 | PARTIAL | 발표 결함 중 미인증 조회·타 권역 저장·스누즈 서버 경로를 재검증 | 공개 배포 화면 전체 재현 필요 |
| A12 | PARTIAL | 전체 Python 테스트와 React lint/build 실행 | 기존 수동 QA FAIL 17건의 화면별 재실행 필요 |
| A13 | PARTIAL | 인증 서비스 장애와 DB OperationalError를 503으로 구분하고 SQL·파라미터 비노출 확인 | React에서 DB/API 5xx 부분 사용 가능성 확인 필요 |
| A14 | PARTIAL | 동일 판단 요청 재전송은 lock version·History를 중복 증가시키지 않으며 오래된 lock version은 차단 | 실제 slow-network E2E 미실행 |

## 2. 자동 검증

### 변경 범위 테스트

```text
python -m pytest api/tests auth_service/tests -q
19 passed, warning 1
```

경고는 Starlette `TestClient`의 향후 httpx2 전환 안내이며 테스트 실패는 아니다.

### 실제 MySQL 롤백 검증

```text
python scripts/validate_retention_persistence.py
PASS: snooze persistence, detailed history, and stale-write protection
```

미검토 리뷰어 한 명을 선택해 판단·메모·담당자·스누즈를 저장하고 재조회한 뒤,
동일 요청 재전송과 오래된 lock version을 확인했다. 외부 트랜잭션을 항상 rollback해
`retention_decisions`, History, review alert에 테스트 데이터를 남기지 않았다.

### 정적·프런트 회귀

```text
python -m compileall -q api auth_service shared scripts
PASS

npm run lint
PASS

npm run build
PASS — 750 modules transformed

Git Bash: bash -n scripts/deploy_server.sh
PASS
```

`git diff --name-only -- app` 결과는 비어 있으며 React 소스는 수정하지 않았다.

## 3. 전체 Python 회귀 결과

```text
python -m pytest tests api/tests auth_service/tests -q
37 passed / 13 failed / 4 errors
```

이번 A 영역 변경 테스트는 통과했다. 전체 모음의 기존 실패 원인은 다음과 같다.

- `models/final_core_logistic_multiclass_metadata_v04.json` 누락으로 DB loader 및
  보관 Streamlit UI 계약 테스트가 연쇄 실패
- `data/processed/regional_review_supply_v04.parquet` 누락
- Windows 임시 경로의 8.3 short path와 long path 비교 불일치 1건

위 파일을 임의 생성하거나 모델·데이터 파이프라인을 변경하지 않았다. 필요한 원본
artifact를 복구한 동일 환경에서 전체 테스트를 다시 실행해야 한다.

## 4. 배포 게이트

배포 워크플로와 서버 스크립트는 다음 조건을 만족하지 않으면 실패한다.

- `VITE_API_BASE_URL`이 경로 없는 `https://` origin
- Nginx에 `listen 443 ssl`
- HTTP→HTTPS 301 또는 308
- 인증 서비스가 `production` 모드이고 Secure Cookie 사용
- 분석 API가 `production` 모드이고 개발용 운영자 우회 비활성
- 공개 HTTPS `/`, `/health`, `/auth/health` 정상 응답

2026-08-24 운영 IP 점검 결과:

```text
http://52.78.194.110/  → 200, HTTPS redirect 없음
https://52.78.194.110/ → 10초 내 응답 없음
```

따라서 저장소의 HTTPS 준비가 완료됐더라도 A03 및 Production Approval은 계속
`HOLD`다. 실제 도메인·인증서 적용 후 동일 항목을 다시 실행해야 한다.
