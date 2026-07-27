# React 프론트엔드 실행 가이드

## 1. 문서 목적

이 문서는 `SKN34-2ND-5TEAM` 프로젝트의 React 프론트엔드를 설치하고 실행하는 방법을 정리한 문서입니다.

기존 Streamlit 앱은 `app/`에서 실행하고, React 프론트엔드는 `frontend/`에서 별도로 실행합니다.

---

## 2. React의 requirements 파일

Python은 `requirements.txt`에 라이브러리를 기록하지만, React/Node.js 프로젝트는 다음 두 파일을 사용합니다.

- `frontend/package.json`: 필요한 라이브러리와 실행 명령을 선언합니다.
- `frontend/package-lock.json`: 실제 설치된 라이브러리의 정확한 버전을 고정합니다.

따라서 React용 `requirements.txt`를 별도로 만들지 않습니다.

다른 PC에서 프로젝트를 받은 사람은 `frontend` 폴더에서 `npm install`을 실행하면 `package.json`과 `package-lock.json`을 기준으로 필요한 라이브러리가 설치됩니다.

---

## 3. 개발 환경

- 운영체제: Windows
- Node.js 개발 확인 버전: v24.18.0
- 패키지 관리자: npm
- 프론트엔드: React + Vite
- 스타일: Tailwind CSS
- 라우팅: React Router
- 차트: Recharts

실제 설치 버전은 `frontend/package.json`과 `frontend/package-lock.json`을 기준으로 확인합니다.

---

## 4. 프로젝트 구조

```text
SKN34-2ND-5TEAM/
├─ app/                       # 기존 Streamlit 앱
├─ frontend/                  # React 프론트엔드
│  ├─ node_modules/           # npm install로 생성, Git에 올리지 않음
│  ├─ public/
│  ├─ src/
│  │  ├─ components/
│  │  ├─ mocks/
│  │  ├─ pages/
│  │  ├─ services/
│  │  ├─ App.jsx
│  │  ├─ index.css
│  │  └─ main.jsx
│  ├─ package.json
│  ├─ package-lock.json
│  └─ vite.config.js
├─ docs/                      # 프로젝트 설명 및 실행 문서
├─ requirements.txt           # Python 공통 라이브러리
└─ requirements-streamlit.txt # Streamlit 실행 라이브러리
```

---

## 5. React 최초 설치

프로젝트 최상위 폴더에서 터미널을 연 뒤 실행합니다.

```bash
cd frontend
npm install
```

`npm install`은 `package.json`과 `package-lock.json`에 기록된 라이브러리를 설치합니다.

`node_modules/` 폴더는 용량이 크므로 GitHub에 올리지 않습니다.

---

## 6. React 개발 서버 실행

```bash
cd frontend
npm run dev
```

터미널에 표시되는 주소로 접속합니다.

```text
http://localhost:5173
```

개발 서버를 종료할 때는 터미널에서 다음 키를 누릅니다.

```text
Ctrl + C
```

---

## 7. React 주요 페이지

```text
/                         운영 홈
/reviewers                리뷰어 관리
/reviewers/:reviewerId    Reviewer 360 상세
/playbook                 리텐션 플레이북
/regional                 콘텐츠 위험 지역 분석
/trust                    모델 신뢰·로드맵
```

예시:

```text
http://localhost:5173/reviewers/demo_reviewer_00001
```

---

## 8. 프로덕션 빌드 확인

개발이 끝난 뒤 배포 가능한 파일이 정상 생성되는지 확인합니다.

```bash
cd frontend
npm run build
```

성공하면 다음 폴더가 생성됩니다.

```text
frontend/dist/
```

빌드 결과를 로컬에서 확인하려면 실행합니다.

```bash
npm run preview
```

---

## 9. 코드 검사

```bash
cd frontend
npm run lint
```

ESLint 오류가 있으면 파일 경로와 줄 번호를 확인한 뒤 수정합니다.

---

## 10. 기존 Streamlit 앱 실행

React와 Streamlit은 서로 다른 터미널에서 실행합니다.

### PowerShell 가상환경 활성화

```powershell
.\venv\Scripts\Activate.ps1
```

### Python 라이브러리 설치

```powershell
python -m pip install -r requirements.txt -r requirements-streamlit.txt
```

### Streamlit 실행

```powershell
python -m streamlit run app/streamlit_app.py
```

기본 주소:

```text
http://localhost:8501
```

React는 별도 터미널에서 실행합니다.

```bash
cd frontend
npm run dev
```

기본 주소:

```text
http://localhost:5173
```

---

## 11. 주요 React 라이브러리

| 라이브러리 | 역할 |
|---|---|
| React | 화면 컴포넌트 구성 |
| React DOM | React 화면을 브라우저 DOM에 렌더링 |
| React Router | 페이지 주소와 화면 이동 관리 |
| Tailwind CSS | 화면 스타일 작성 |
| Recharts | 선 그래프와 막대그래프 작성 |
| Vite | React 개발 서버와 빌드 |
| ESLint | JavaScript/JSX 코드 검사 |

정확한 설치 버전은 `frontend/package.json`에서 확인합니다.

---

## 12. Git에 포함할 파일

다음 파일과 폴더는 GitHub에 포함합니다.

```text
frontend/src/
frontend/public/
frontend/package.json
frontend/package-lock.json
frontend/vite.config.js
frontend/eslint.config.js
frontend/index.html
docs/FRONTEND_RUN_GUIDE.md
```

다음 폴더는 포함하지 않습니다.

```text
frontend/node_modules/
frontend/dist/
```

루트 또는 `frontend/.gitignore`에 다음 항목이 있어야 합니다.

```gitignore
node_modules/
dist/
```

---

## 13. 자주 발생하는 오류

### `npm` 명령을 찾을 수 없음

Node.js 설치 후 VS Code를 완전히 종료했다가 다시 실행합니다.

```bash
node -v
npm -v
```

### `Failed to resolve import "recharts"`

```bash
cd frontend
npm install recharts
```

### `Failed to resolve import`

파일명, 폴더명, import 경로의 대소문자를 확인합니다.

### 화면이 수정 전 상태로 보임

파일 저장 후 브라우저에서 강력 새로고침합니다.

```text
Ctrl + F5
```

필요하면 개발 서버를 재시작합니다.

```text
Ctrl + C
```

```bash
npm run dev
```

---

## 14. 현재 개발 상태

- React 기본 환경 구성 완료
- Tailwind CSS 연결 완료
- 페이지 라우팅 완료
- 운영 홈 구현
- 리뷰어 관리 구현
- Reviewer 360 상세 구현
- 차트 구현
- 관리자 판단 로컬 저장 구현
- 리텐션 플레이북 구현
- 콘텐츠 위험 지역 분석 구현
- 모델 신뢰·로드맵 구현
- FastAPI 실제 데이터 연결 예정
- MySQL 운영 데이터 저장 예정

현재 화면의 수치와 일부 리뷰어 정보는 UI 검증을 위한 DEMO 데이터입니다.
