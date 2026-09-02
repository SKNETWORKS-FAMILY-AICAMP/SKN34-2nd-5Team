# AWS HTTPS 재배포 실행 보고서

- 실행일: 2026-09-02 (Asia/Seoul)
- 대상: Yelp 핵심 리뷰어 리텐션 운영 서비스 AWS Ubuntu 서버
- 공개 주소: `https://52.78.194.110`
- HTTPS 보안 배포 확인 commit: `9724f29`
- 관련 항목: A01, A03, A04, A05

이 문서는 2026-08-24 사전 QA에서 `FAIL` 또는 `PARTIAL`이었던 HTTPS·Secure
Cookie 항목을 실제 운영 서버에 적용하고 검증한 기록이다. 비밀번호, DB URL,
SSH 개인키, 쿠키 값은 기록하지 않는다.

## 1. 작업 전 상태

운영 서비스는 공인 IP의 HTTP 주소로 제공되고 있었다.

```text
http://52.78.194.110
```

확인된 초기 상태:

- Nginx `1.24.0`이 80 포트에서만 실행
- `listen 443 ssl` 없음
- HTTP→HTTPS redirect 없음
- Certbot 미설치
- `AUTH_COOKIE_SECURE=false`
- `RETENTION_ENV`, `RETENTION_ALLOW_DEV_OPERATOR`, `AUTH_ENV` 미설정
- 서버 Git branch `main`, 작업 트리 clean
- 서버 기준 기존 commit `964fd05`

## 2. 서버 구조 확인

### systemd 서비스

| 서비스 | 실행 사용자 | WorkingDirectory | 내부 주소 |
|---|---|---|---|
| `reviewer-retention.service` | `ubuntu:ubuntu` | `/srv/reviewer-retention` | `127.0.0.1:8000` |
| `reviewer-retention-auth.service` | `ubuntu:ubuntu` | `/srv/reviewer-retention` | `127.0.0.1:8100` |

`ubuntu` 계정에는 비대화형 `NOPASSWD` sudo 권한이 설정돼 있어 GitHub Actions
배포 스크립트가 Nginx 검사와 서비스 재시작을 수행할 수 있다.

### 주요 경로

```text
프로젝트       /srv/reviewer-retention
React 배포본   /var/www/reviewer-retention
Nginx 설정     /etc/nginx/sites-enabled/reviewer-retention
Nginx 캐시     /etc/nginx/conf.d/reviewer-retention-cache.conf
운영 DB 환경   /srv/reviewer-retention/database/.env
인증 환경      /srv/reviewer-retention/auth_service/.env
백업 경로      /srv/reviewer-retention-backups
```

기존 `/auth` → `8100`, `/api` → `8000`, `/health` → `8000/health` reverse
proxy 및 읽기 API microcache 설정은 유지했다.

## 3. 네트워크 준비

- `52.78.194.110` 고정 IP 사용 확인
- AWS 인바운드 규칙 `HTTPS / TCP / 443 / Any IPv4 address` 적용 확인
- Ubuntu UFW 상태 `inactive` 확인
- 80 포트는 HTTP redirect와 ACME HTTP-01 갱신을 위해 유지

## 4. 백업

변경 전 다음 파일을 생성했다.

```text
/srv/reviewer-retention-backups/
  nginx-reviewer-retention.before-https-20260902-031135.conf
  database.env.before-https-20260902-033640
  auth-service.env.before-https-20260902-033640
```

환경파일 백업은 원본의 제한된 파일 권한을 유지한다.

## 5. IP 인증서 적용

도메인이 없어 Let’s Encrypt short-lived IP 인증서를 적용했다.

- Certbot 설치 방식: snap classic
- 설치 버전: `certbot 5.8.0`
- 인증서 이름: `reviewer-retention-ip`
- 식별자: `52.78.194.110`
- 키 유형: ECDSA
- 최초 확인 만료 시각: `2026-09-08 18:20:00+00:00`

인증서 경로:

```text
/etc/letsencrypt/live/reviewer-retention-ip/fullchain.pem
/etc/letsencrypt/live/reviewer-retention-ip/privkey.pem
```

먼저 `reviewer-retention-ip-staging` 인증서로 HTTP-01 webroot 검증을 통과한 뒤
운영 인증서를 별도 이름으로 발급했다. 운영 인증서 적용 확인 후 staging 인증서는
삭제했다.

## 6. Nginx HTTPS 설정

기존 server block에 다음 구성을 추가했다.

```nginx
listen 443 ssl default_server;
listen [::]:443 ssl default_server;

ssl_certificate /etc/letsencrypt/live/reviewer-retention-ip/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/reviewer-retention-ip/privkey.pem;
ssl_protocols TLSv1.2 TLSv1.3;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 1d;

if ($scheme = http) {
    return 301 https://$host$request_uri;
}
```

적용 전후 `sudo nginx -t`가 모두 성공했으며, reload 후 Nginx가 IPv4·IPv6의
80·443 포트에서 listening 중임을 확인했다.

## 7. 인증서 자동 갱신

IP 인증서는 약 6일의 short-lived 인증서이므로 Certbot 자동 갱신과 갱신 후
Nginx reload를 구성했다.

deploy hook:

```text
/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
```

```sh
#!/bin/sh
/usr/sbin/nginx -t && /bin/systemctl reload nginx
```

검증 결과:

- `certbot renew --dry-run --run-deploy-hooks` 성공
- `snap.certbot.renew.timer` enabled
- `snap.certbot.renew.timer` active (waiting)
- 모의 갱신 후 deploy hook 실행 및 Nginx 설정 검사 성공

`nginx -t`는 성공 메시지를 stderr로 출력하므로 Certbot 로그에 hook의
`error output`처럼 표시됐지만, hook exit status와 전체 모의 갱신 결과는 성공이었다.

## 8. 운영 환경변수

### `database/.env`

```dotenv
RETENTION_ENV=production
RETENTION_ALLOW_DEV_OPERATOR=0
RETENTION_ALLOWED_ORIGINS=
```

### `auth_service/.env`

```dotenv
AUTH_ENV=production
AUTH_COOKIE_SECURE=true
AUTH_ALLOWED_ORIGINS=
```

React·API·Auth가 동일 HTTPS origin에서 제공되므로 CORS origin 목록은 비워 두었다.
실제 DB 접속정보와 인증 비밀값은 기존 파일에 유지하고 문서나 Git에 포함하지 않았다.

## 9. GitHub Actions 재배포

워크플로:

```text
.github/workflows/deploy-aws.yml
Deploy main to AWS
```

운영 빌드 변수:

```text
VITE_API_BASE_URL=https://52.78.194.110
```

GitHub Secrets는 이름만 확인하고 값을 출력하지 않았다.

```text
AWS_SSH_HOST
AWS_SSH_USER
AWS_SSH_PRIVATE_KEY
AWS_SSH_KNOWN_HOSTS
```

`main`의 보안 commit `9724f29`를 대상으로 수동 workflow를 실행했고 GitHub
Actions가 `Success`로 종료됐다. 서버에서도 다음 상태를 재확인했다.

```text
9724f29 (HEAD -> main, origin/main, origin/HEAD)
```

> 이 보고서는 HTTPS 보안 재배포 시점의 commit을 기록한다. 이후 GitHub main에
> 추가된 commit이 운영 서버에 자동 반영됐다는 의미는 아니다.

## 10. 운영 검증 결과

### HTTPS 및 redirect

```text
GET/HEAD https://52.78.194.110/ → 200 OK
GET/HEAD http://52.78.194.110/  → 301 Moved Permanently
Location                         → https://52.78.194.110/
```

브라우저에서 `https://52.78.194.110/auth/login`이 인증서 경고 없이 표시됐다.

### 서비스 보안 상태

`GET /health`:

```json
{"status":"ok","environment":"production","developmentOperator":false}
```

`GET /auth/health`:

```json
{"status":"ok","environment":"production","secureCookie":true}
```

### 미인증 API

```text
GET /api/retention/target-lists → 401 Unauthorized
{"detail":"로그인이 필요합니다."}
```

### 실제 로그인 쿠키

브라우저 개발자 도구에서 다음 속성을 확인했다. 쿠키 값은 기록하지 않았다.

| 쿠키 | Secure | HttpOnly | SameSite |
|---|---|---|---|
| `rr_auth_session` | Yes | Yes | Lax |
| `rr_auth_csrf` | Yes | No | Lax |

배포 직후 첫 화면 로딩이 일시적으로 실패했지만 새로고침 후 정상 복구됐고, 같은
시점의 `/health`, `/api/operations`, `/api/reviewers` 응답은 모두 200이었다.
전역 게이트가 일시적 API 장애를 전체 화면 장애로 확대하는 문제는 별도 React
resilience PR에서 처리한다.

## 11. A 영역 판정

| ID | 판정 | 근거 |
|---|---|---|
| A01 Retention 조회 API 인증 | PASS | 운영 HTTPS에서 미인증 조회 401 확인 |
| A02 OPERATOR 담당 권역 서버 강제 | PARTIAL | 코드·자동 테스트 통과, 실제 OPERATOR 권역 계정 smoke test 필요 |
| A03 HTTPS | PASS | 443, 유효 인증서, HTTP redirect, 자동 갱신 확인 |
| A04 Secure Cookie | PASS | production health와 실제 로그인 쿠키 속성 확인 |
| A05 Production CORS | PARTIAL | 동일 origin 운영 설정 적용, 비허용 cross-origin 운영 검증 필요 |
| A06 Snooze 저장·복원 | PARTIAL | 백엔드 검증 통과, React 새로고침·재로그인 QA 필요 |
| A07 History 상세 | PARTIAL | API 필드 준비, React 상세 UI 연결 필요 |
| A08~A10 React 부분 장애 대응 | NOT RUN | 별도 `fix/a-app-resilience` PR 범위 |
| A11~A13 최종 회귀·장애 QA | PARTIAL | HTTPS 배포본 기준 역할·장애·전체 회귀 추가 실행 필요 |

## 12. 남은 작업

1. VIEWER 저장 403 확인
2. OPERATOR 담당 권역 저장 성공 및 타 권역 저장 403 확인
3. ADMIN 전체 권역 접근 확인
4. 비허용 cross-origin에 CORS 허용 헤더가 없는지 확인
5. React 부분 장애 대응 PR 구현
6. Snooze 새로고침·재로그인 복원 및 History 상세 UI QA
7. 기존 QA FAIL 17건을 최종 배포본에서 재실행

## 13. 운영 확인 명령

비밀값을 출력하지 않는 상태 확인 명령:

```bash
curl -s https://52.78.194.110/health
curl -s https://52.78.194.110/auth/health
sudo /snap/bin/certbot certificates
systemctl list-timers --all | grep -i certbot
sudo nginx -t
sudo systemctl status reviewer-retention.service --no-pager
sudo systemctl status reviewer-retention-auth.service --no-pager
```

문제 발생 시 Nginx·환경파일 백업을 먼저 확인하고, 서버 코드를 직접 수정하거나
Git을 강제 초기화하지 않는다. 코드 문제는 새 commit과 GitHub Actions 재배포로
처리한다.
