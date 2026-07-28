# React 프론트엔드 의존성 관리

## 핵심 안내

React 프로젝트에서는 Python의 `requirements.txt` 대신 다음 파일을 사용합니다.

```text
app/package.json
app/package-lock.json
```

- `package.json`: 필요한 라이브러리와 npm 실행 명령을 선언합니다.
- `package-lock.json`: 팀원 모두가 같은 의존성 버전을 설치하도록 정확한 버전을 고정합니다.

## 설치 명령

```bash
cd app
npm install
```

## 현재 사용 라이브러리

```text
react
react-dom
react-router
recharts
tailwindcss
@tailwindcss/vite
vite
@vitejs/plugin-react
eslint
```

정확한 버전은 현재 프로젝트의 `app/package.json`과 `app/package-lock.json`을 기준으로 합니다.

## Git 관리 원칙

Git에 포함:

```text
package.json
package-lock.json
```

Git에 제외:

```text
node_modules/
dist/
```
