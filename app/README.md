# Yelp Reviewer Retention Frontend

Yelp 파워 리뷰어의 활동 감소와 이탈 위험을 확인하기 위한 React 기반 프론트엔드입니다.

현재 React 운영 화면은 `api/`의 읽기 전용 FastAPI를 통해 MySQL `yelp_data`의
실제 v04 데이터와 모델 결과를 조회합니다. `app/src/data/*.json`은 정합성 확인과
복구를 위한 정적 산출물이며 API 실패 시 자동으로 사용하는 폴백은 아닙니다.

---

## 1. 프로젝트 개요

이 프로젝트는 Yelp의 리뷰 활동 데이터를 활용하여 활동이 감소하거나 중단될 가능성이 있는 파워 리뷰어를 탐색하고, 관리 우선순위를 제공하는 것을 목표로 합니다.

주요 기능은 다음과 같습니다.

- 리뷰어 활동 현황 확인
- 관리 우선순위 리뷰어 목록 확인
- 리뷰어별 상세 활동 분석
- 리텐션 전략 추천
- 지역별 활동 위험 분석
- 모델 성능 및 신뢰도 확인

> 화면에 표시되는 `risk_score`는 실제 이탈 확률이 아니라, 리뷰어 관리 우선순위를 나타내기 위한 운영 점수입니다.

---

## 2. 기술 스택

### Frontend

- React
- Vite
- JavaScript
- Tailwind CSS
- React Router
- Recharts

### Backend / Data

- FastAPI 읽기 전용 API
- MySQL (`yelp_data`)
- SQLAlchemy / PyMySQL
- `shared/retention` 공용 판단·직렬화 로직

---

## 3. 프로젝트 폴더 위치

React 프론트엔드는 프로젝트 최상위의 `app` 폴더에 있습니다(과거에는 `frontend` 폴더였습니다).
기존 Streamlit 애플리케이션(v04)은 `archive/app_streamlit_v04`로, 과거 분석 프로토타입(v01)은
`archive/app_streamlit_v01_prototype`로 옮겨졌습니다.

```text
SKN34-2ND-5TEAM/
├─ api/                                    # React가 조회하는 FastAPI 읽기 전용 API
├─ app/                                    # React 프론트엔드(현재 운영 서비스)
│  ├─ public/
│  ├─ src/
│  ├─ package.json
│  ├─ package-lock.json
│  ├─ vite.config.js
│  └─ README.md
├─ shared/retention/                       # 위험 판단·정규화·직렬화 기준 구현
├─ database/                               # MySQL DDL·적재·검증
├─ scripts/                                # 정적 JSON 정합성·복구용 export
├─ archive/
│  ├─ app_streamlit_v04/                   # 기존 Streamlit UI와 호환 wrapper
│  └─ app_streamlit_v01_prototype/         # 과거 분석 프로토타입 · 수정 금지
├─ docs/
├─ notebooks/
├─ reports/
├─ requirements.txt
└─ README.md
```

React 코드는 프로젝트 최상위의 `app` 폴더에서 실행합니다.

---

## 4. 실행 전 준비

React 프론트엔드를 실행하려면 Node.js가 설치되어 있어야 합니다.

### 권장 실행 환경

- Node.js 24 LTS
- npm

개발 시 사용한 Node.js 버전은 다음과 같습니다.

```text
v24.18.0
```

팀원이 반드시 완전히 같은 버전을 설치해야 하는 것은 아니지만, 가능한 한 Node.js LTS 버전 사용을 권장합니다.

Node.js 설치 후 터미널에서 다음 명령으로 정상 설치 여부를 확인합니다.

```bash
node -v
npm -v
```

정상적으로 설치되었다면 아래와 같이 버전이 출력됩니다.

```text
v24.18.0
11.x.x
```

`node` 또는 `npm` 명령을 찾을 수 없다는 오류가 발생하면 Node.js 설치 후 터미널이나 VS Code를 다시 실행합니다.

---

## 5. 프로젝트 다운로드

GitHub에서 프로젝트를 Clone합니다.

```bash
git clone 저장소주소
```

Clone한 프로젝트 폴더로 이동합니다.

```bash
cd SKN34-2ND-5TEAM
```

이미 프로젝트를 받은 팀원은 최신 코드를 가져옵니다.

```bash
git pull
```

---

## 6. React 설치 및 실행

프로젝트 최상위 폴더에서 React 폴더로 이동합니다.

```bash
cd app
```

처음 프로젝트를 실행하는 경우 필요한 패키지를 설치합니다.

```bash
npm install
```

개발 서버를 실행합니다.

```bash
npm run dev
```

정상적으로 실행되면 터미널에 아래와 비슷한 주소가 표시됩니다.

```text
http://localhost:5173
```

브라우저에서 다음 주소로 접속합니다.

```text
http://localhost:5173
```

---

## 7. 팀원용 전체 실행 순서

처음 실행하는 팀원은 아래 순서대로 진행합니다.

```text
1. Python 3.12와 Node.js LTS 설치
2. GitHub 프로젝트 Clone 또는 Pull
3. `database/.env`에 MySQL 연결 정보 준비
4. Python 환경에 `requirements.txt`와 `api/requirements.txt` 설치
5. 프로젝트 최상위에서 FastAPI 실행
6. 새 터미널의 `app` 폴더에서 React 실행
7. http://localhost:5173 접속
```

실제 명령어는 다음과 같습니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r api\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload --port 8000
```

새 터미널에서는 다음 명령을 실행합니다.

```powershell
cd app
npm install
npm run dev
```

로컬 기본 API 주소는 `http://localhost:8000`입니다. 다른 API를 사용할 때는
React 빌드 또는 실행 전에 `VITE_API_BASE_URL`을 해당 주소로 설정합니다.

---

## 8. npm 명령어 설명

### 개발 서버 실행

```bash
npm run dev
```

React 개발 서버를 실행합니다.

---

### 패키지 설치

```bash
npm install
```

`package.json`과 `package-lock.json`을 기준으로 React, Tailwind CSS, React Router, Recharts 등 프로젝트에서 사용하는 라이브러리를 설치합니다.

설치된 패키지는 다음 폴더에 저장됩니다.

```text
app/node_modules/
```

`node_modules`는 용량이 크기 때문에 GitHub에 업로드하지 않습니다.

팀원은 프로젝트를 받은 후 `npm install`을 실행하여 동일한 패키지를 설치할 수 있습니다.

---

### 배포용 파일 생성

```bash
npm run build
```

배포용 파일을 생성합니다.

생성 결과는 다음 폴더에 저장됩니다.

```text
app/dist/
```

`dist` 폴더 역시 다시 생성할 수 있으므로 GitHub에 업로드하지 않습니다.

---

### 배포 결과 미리보기

```bash
npm run preview
```

`npm run build`로 생성된 배포용 화면을 로컬에서 확인합니다.

---

### 코드 검사

```bash
npm run lint
```

코드 작성 규칙 위반이나 오류 가능성을 검사합니다.

---

## 9. 주요 화면

현재 구현된 주요 화면은 다음과 같습니다.

| 경로 | 화면 | 설명 |
|---|---|---|
| `/` | 운영 대시보드 | 핵심 지표, 관리 큐, 운영 정책 확인 |
| `/reviewers` | 리뷰어 관리 | 리뷰어 목록, 검색, 필터, 정렬 |
| `/reviewers/:reviewerId` | 리뷰어 상세 | 리뷰어 활동 변화 및 관리 판단 |
| `/playbook` | 리텐션 플레이북 | 리뷰어 유형별 추천 전략 |
| `/regional` | 지역 분석 | 지역별 리뷰 활동 위험 분석 |
| `/trust` | Trust Center | 모델 성능, 검증 항목, 로드맵 확인 |

예시:

```text
http://localhost:5173/
http://localhost:5173/reviewers
http://localhost:5173/playbook
http://localhost:5173/regional
http://localhost:5173/trust
```

---

## 10. 주요 기능

### 운영 대시보드

- 전체 리뷰어 현황 확인
- 우선 관리 대상 확인
- 위험도별 리뷰어 수 확인
- 관리 큐 확인
- 운영 정책 확인

### 리뷰어 관리

- 리뷰어 목록 확인
- 이름 및 ID 검색
- 위험도 필터
- 지역 필터
- 위험 점수 기준 정렬
- 리뷰어 상세 페이지 이동

### 리뷰어 상세

- 리뷰어 기본 정보 확인
- 활동 점수 비교
- 과거 기간과 최근 기간 비교
- 주요 위험 근거 확인
- 관리자의 판단 저장
- 리뷰 활동 차트 확인

### 리텐션 플레이북

- 위험 유형별 전략 카드 확인
- 리뷰어 특성에 맞는 전략 확인
- 조건에 맞는 리뷰어 필터링
- 우선 적용 대상 확인

### 지역 분석

- 지역별 리뷰어 분포 확인
- 지역별 위험도 비교
- 위험 수준별 누적 막대그래프 확인
- 지역 및 위험 수준 필터

### Trust Center

- Precision 확인
- Recall 확인
- Lift 확인
- 평가 지표 설명
- 모델 검증 체크리스트
- 주요 특성 중요도
- 모델 비교
- 향후 개발 로드맵

---

## 11. 데이터 사용 방식

현재 React 운영 화면은 다음 런타임 경로를 사용합니다.

```text
React
  ↓ HTTP 요청
FastAPI (api/)
  ↓ SELECT
MySQL yelp_data
```

위험 유형·근거·전략 판단, 프로필 정규화, React 직렬화의 기준 구현은
`shared/retention/`입니다. API와 정적 export 스크립트는 이 모듈을 재사용합니다.

```text
app/src/data/*.json
└─ API 응답 정합성 확인 및 복구용 export 산출물
```

정적 JSON은 런타임 자동 폴백이 아니므로 API가 중단되면 화면에 데이터 로딩
오류가 표시됩니다. 합성·데모 데이터를 추가할 경우 화면에서 명확히 구분해야 합니다.

---

## 12. 관리자 판단 저장

리뷰어 상세 화면에서 저장하는 관리자 판단은 현재 브라우저의 `localStorage`를 사용합니다.

따라서 다음과 같은 특징이 있습니다.

- 현재 사용 중인 브라우저에만 저장됩니다.
- 다른 컴퓨터와 공유되지 않습니다.
- 브라우저 데이터를 삭제하면 함께 삭제될 수 있습니다.
- 실제 데이터베이스에 저장되는 기능은 아닙니다.

현재 FastAPI/MySQL 연동은 읽기 전용입니다. 관리자 판단의 서버 저장과 다중 운영자
이력 관리는 별도 고도화 범위입니다.

---

## 13. FastAPI와 React 실행

현재 운영 서비스는 FastAPI와 React를 서로 다른 터미널에서 실행합니다.

### FastAPI 실행

프로젝트 최상위에서 다음 명령을 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload --port 8000
```

상태 확인 주소:

```text
http://localhost:8000/health
```

### React 실행

프로젝트 최상위에서 다음 명령을 실행합니다.

```bash
cd app
npm install
npm run dev
```

React 기본 접속 주소:

```text
http://localhost:5173
```

다른 API 주소를 사용할 때는 `VITE_API_BASE_URL`을 설정한 뒤 React를 실행하거나
프로덕션 빌드를 생성해야 합니다.

기존 Streamlit 앱은 `archive/app_streamlit_v04`에 보존되어 있으며 현재 React의
런타임 데이터 경로가 아닙니다. 필요하면 다음과 같이 별도로 실행할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe -m streamlit run archive\app_streamlit_v04\streamlit_app.py
```

---

## 14. Python 가상환경 실행

FastAPI와 기존 Streamlit 앱을 실행하려면 Python 가상환경을 사용합니다.

가상환경 폴더명은 다음과 같습니다.

```text
.venv
```

### PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

### Windows CMD

```cmd
.venv\Scripts\activate
```

### Git Bash

```bash
source .venv/Scripts/activate
```

가상환경을 활성화한 후 필요한 Python 패키지를 설치합니다.

```bash
python -m pip install -r requirements.txt -r api/requirements.txt
```

---

## 15. GitHub에 포함해야 하는 파일

다음 React 관련 파일은 GitHub에 포함해야 합니다.

```text
app/src/
app/public/
app/package.json
app/package-lock.json
app/vite.config.js
app/eslint.config.js
app/index.html
app/README.md
app/.gitignore
```

특히 아래 파일은 팀원들이 같은 패키지를 설치하기 위해 반드시 필요합니다.

```text
app/package.json
app/package-lock.json
```

---

## 16. GitHub에 포함하지 않는 파일

다음 파일과 폴더는 GitHub에 업로드하지 않습니다.

```text
app/node_modules/
app/dist/
app/.vite/
app/.env
```

`app/.gitignore`에 아래와 같은 설정이 있으면 자동으로 제외됩니다.

```gitignore
node_modules
dist
dist-ssr
*.local
```

환경변수 파일을 사용하는 경우 다음 내용도 추가할 수 있습니다.

```gitignore
.env
.env.*
!.env.example
```

---

## 17. Git 작업 예시

React 작업 내용을 Git에 추가합니다.

```bash
git add app
```

변경 내용을 확인합니다.

```bash
git status
```

커밋합니다.

```bash
git commit -m "feat: React 프론트엔드 화면 구현"
```

원격 저장소로 업로드합니다.

```bash
git push
```

README만 수정한 경우 다음과 같이 커밋할 수 있습니다.

```bash
git add app/README.md
git commit -m "docs: 프론트엔드 실행 방법 보완"
git push
```

---

## 18. 자주 발생하는 오류

### `npm` 명령을 찾을 수 없는 경우

Node.js가 설치되어 있지 않거나 환경변수가 적용되지 않은 상태입니다.

Node.js LTS 설치 후 VS Code와 터미널을 완전히 종료했다가 다시 실행합니다.

확인 명령어:

```bash
node -v
npm -v
```

---

### `package.json`을 찾을 수 없는 경우

현재 터미널 위치가 `app` 폴더가 아닐 가능성이 큽니다.

현재 위치를 확인합니다.

```bash
pwd
```

Windows CMD에서는 다음 명령을 사용할 수 있습니다.

```cmd
cd
```

프로젝트 최상위 폴더에 있다면 다음 명령으로 이동합니다.

```bash
cd app
```

그다음 다시 실행합니다.

```bash
npm install
npm run dev
```

---

### `node_modules`가 없는 경우

프로젝트를 처음 받았을 때 정상적으로 발생할 수 있습니다.

다음 명령을 실행합니다.

```bash
cd app
npm install
```

---

### Recharts import 오류

다음과 같은 오류가 발생할 수 있습니다.

```text
Failed to resolve import "recharts"
```

`app` 폴더에서 다음 명령을 실행합니다.

```bash
npm install recharts
```

다만 `package.json`과 `package-lock.json`이 최신 상태라면 일반적으로 다음 명령만 실행해도 설치됩니다.

```bash
npm install
```

---

### 화면이 이전 코드로 보이는 경우

다음을 확인합니다.

1. 수정한 파일을 저장했는지 확인합니다.
2. 올바른 프로젝트 폴더를 열었는지 확인합니다.
3. React 개발 서버를 다시 실행합니다.
4. 브라우저를 새로고침합니다.

개발 서버 재실행:

```bash
Ctrl + C
npm run dev
```

브라우저 강력 새로고침:

```text
Ctrl + F5
```

---

### `npm install` 오류가 계속 발생하는 경우

기존 설치 파일을 삭제한 후 다시 설치합니다.

PowerShell:

```powershell
Remove-Item -Recurse -Force node_modules
Remove-Item -Force package-lock.json
npm install
```

다만 팀 프로젝트에서는 `package-lock.json`을 삭제하기 전에 팀원과 확인하는 것이 좋습니다.

우선 아래 순서로 시도하는 것을 권장합니다.

```bash
npm install
npm run dev
```

---

### 포트 5173이 이미 사용 중인 경우

Vite가 자동으로 다른 포트를 사용할 수 있습니다.

터미널에 표시되는 실제 접속 주소를 확인합니다.

예시:

```text
http://localhost:5174
```

---

## 19. 저장소 위치 주의

Windows에서 동일한 이름의 프로젝트를 여러 위치에 Clone하면 서로 다른 저장소를 수정할 수 있습니다.

현재 작업에 사용하는 저장소 위치는 다음 경로인지 확인합니다.

```text
C:\Users\playdata2\Documents\GitHub\SKN34-2nd-5Team
```

다음 경로와는 다른 저장소일 수 있습니다.

```text
C:\Users\playdata2\SKN34-2nd-5Team
```

VS Code에서 프로젝트를 열 때 반드시 올바른 폴더를 선택합니다.

---

## 20. 개발 진행 상태

현재 구현된 내용:

- React 프로젝트 생성
- Vite 개발 환경 설정
- Tailwind CSS 적용
- React Router 적용
- Recharts 적용
- 운영 대시보드 구현
- 리뷰어 관리 화면 구현
- 리뷰어 상세 화면 구현
- 리텐션 플레이북 구현
- 지역 분석 화면 구현
- Trust Center 구현
- FastAPI 읽기 전용 API 연결
- MySQL `yelp_data` 실제 v04 데이터 연결
- `shared/retention` 공용 로직 분리
- 정적 JSON을 정합성·복구용 산출물로 보존
- 관리자 판단 로컬 저장 기능 구현

향후 진행 예정:

- 사용자 인증 기능
- 관리자 판단 서버 저장
- AWS 배포 주소·환경변수·운영 절차 문서화
- 반응형 화면 개선
- 테스트 코드 추가

---

## 21. 참고 문서

프로젝트의 상세 실행 및 의존성 관련 문서는 `docs` 폴더에서 확인할 수 있습니다.

```text
docs/FRONTEND_RUN_GUIDE.md
docs/FRONTEND_DEPENDENCIES.md
```

문서 역할:

| 문서 | 내용 |
|---|---|
| `app/README.md` | React 프론트엔드 소개 및 기본 실행 방법 |
| `docs/FRONTEND_RUN_GUIDE.md` | 상세 실행 과정 및 오류 해결 |
| `docs/FRONTEND_DEPENDENCIES.md` | npm 패키지와 의존성 관리 설명 |

---

## 22. 빠른 실행 요약

Node.js가 이미 설치되어 있다면 아래 명령만 실행하면 됩니다.

```bash
cd app
npm install
npm run dev
```

브라우저 접속:

```text
http://localhost:5173
```

Node.js가 설치되어 있지 않다면 Node.js LTS 버전을 먼저 설치한 후 위 명령을 실행합니다.
