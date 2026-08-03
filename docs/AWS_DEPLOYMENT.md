# AWS 반자동 배포 가이드

이 프로젝트의 운영 배포는 GitHub Actions의 `Deploy main to AWS` 워크플로를
사람이 실행하면, 검증과 서버 반영은 자동으로 처리하는 방식이다.

## 배포 범위

- GitHub `main`의 React, 분석 FastAPI, 인증 FastAPI 코드를 배포한다.
- React lint/build, Python 컴파일, 배포 관련 계약·인증 테스트가 모두 통과한
  커밋만 배포한다. 원본 데이터가 필요한 오프라인 파이프라인 테스트는 배포
  워크플로에서 제외한다.
- AWS 서버가 GitHub와 다른 추적 파일을 가지고 있으면 변경하지 않고 중단한다.
- 기존 `.env`, MySQL 데이터, `data/`, `models/`, 사진, Parquet 파일은 건드리지 않는다.
- DB 스키마 변경과 데이터 적재는 이 워크플로에 포함하지 않는다.

## 최초 1회 준비

자동 배포를 사용하기 전에 AWS 서버의 직접 수정사항을 로컬/GitHub 커밋으로
정리해야 한다. 서버에서 아래 결과가 비어 있어야 한다.

```bash
cd /srv/reviewer-retention
git status --short --untracked-files=no
```

결과가 있으면 삭제하거나 강제로 덮어쓰지 말고, 로컬의 같은 변경과 비교하여
먼저 `main`에 커밋한다.

AWS 서버에서 실제 systemd 서비스 이름을 확인한다.

```bash
sudo systemctl list-units --type=service | grep -E "reviewer|retention|api|auth"
```

배포용 SSH 사용자는 다음 명령을 비밀번호 없이 실행할 권한이 필요하다.

```text
systemctl cat <분석 API 서비스>
systemctl cat <인증 API 서비스>
systemctl restart <분석 API 서비스>
systemctl restart <인증 API 서비스>
nginx -t
```

전체 관리자 권한을 주는 대신 위 명령만 허용하는 sudoers 설정을 권장한다.

## GitHub Secrets

GitHub 저장소의 `Settings > Secrets and variables > Actions`에서 다음
Repository secrets를 등록한다.

| 이름 | 값 |
|---|---|
| `AWS_SSH_HOST` | Lightsail 고정 IP 또는 도메인 |
| `AWS_SSH_USER` | 배포용 Linux 사용자명 |
| `AWS_SSH_PRIVATE_KEY` | 해당 사용자의 SSH 개인키 전체 내용 |
| `AWS_SSH_KNOWN_HOSTS` | 검증된 AWS 서버 host key 한 줄 |

`AWS_SSH_KNOWN_HOSTS`는 신뢰할 수 있는 환경에서 서버 fingerprint를 확인한 뒤
다음과 같이 만든다.

```bash
ssh-keyscan -H <AWS 고정 IP>
```

출력값을 바로 신뢰하지 말고 Lightsail 인스턴스의 SSH host fingerprint와
일치하는지 먼저 확인한다.

## GitHub Variables

다음 값은 현재 AWS 구성에 맞는 기본값이 워크플로에 들어 있다. 서버 이름이나
주소가 바뀌었을 때만 같은 화면의 `Variables`에서 덮어쓴다.

| 이름 | 현재 기본값 |
|---|---|
| `AWS_DEPLOY_PATH` | `/srv/reviewer-retention` |
| `AWS_FRONTEND_ROOT` | `/var/www/reviewer-retention` |
| `AWS_API_SERVICE` | `reviewer-retention.service` |
| `AWS_AUTH_SERVICE` | `reviewer-retention-auth.service` |
| `VITE_API_BASE_URL` | `http://52.78.194.110:8000` |

위 서비스 이름은 AWS 서버에서 직접 확인한 값이다.
`VITE_API_BASE_URL`을 누락하면 React가 관람자의 `localhost:8000`을 조회하게 되므로
워크플로가 배포를 시작하기 전에 실패하도록 구성되어 있다.

## 배포 실행

1. 작업 브랜치를 Pull Request로 검토한다.
2. 테스트가 통과하면 `main`에 병합한다.
3. GitHub 저장소의 `Actions`를 연다.
4. `Deploy main to AWS`를 선택한다.
5. `Run workflow`를 누르고 확인란에 `DEPLOY`를 입력한다.
6. `validate`와 `deploy` 작업이 모두 초록색인지 확인한다.
7. 공개 사이트를 `Ctrl+F5`로 새로고침한다.

## 안전장치

- 동시에 두 배포가 실행되지 않는다.
- 확인값이 정확히 `DEPLOY`일 때만 실행된다.
- 서버가 `main` 브랜치가 아니거나 추적 파일이 수정됐으면 중단된다.
- GitHub에서 검사한 SHA와 서버가 받은 SHA가 다르면 중단된다.
- 검증된 배포 스크립트를 임시 경로로 전송하므로 최초 배포에도 사용할 수 있다.
- fast-forward가 아닌 Git 변경은 중단된다.
- React는 `dist.next`에서 먼저 빌드하고 성공한 경우에만 교체한다.
- 서버 Node.js 버전과 Nginx의 실제 React 경로가 맞지 않으면 교체 전에 중단한다.
- API·인증·Nginx 상태 검사가 실패하면 워크플로가 실패로 표시된다.
- React 상태 검사 실패 시 직전 `dist` 화면을 복원한다.

## 실패했을 때

GitHub Actions 로그에서 처음 실패한 단계의 메시지를 확인한다. 서버가 수정된
상태라는 오류가 나오면 서버에서 강제 초기화하지 말고 변경 파일을 먼저 비교한다.
서비스 상태는 다음과 같이 확인한다.

```bash
sudo systemctl status <분석 API 서비스> --no-pager
sudo systemctl status <인증 API 서비스> --no-pager
sudo journalctl -u <서비스 이름> -n 100 --no-pager
```

DB 적재 실패, 사진·Parquet 누락은 코드 자동 배포와 별개의 문제이므로 기존 데이터
적재 절차로 처리한다.
