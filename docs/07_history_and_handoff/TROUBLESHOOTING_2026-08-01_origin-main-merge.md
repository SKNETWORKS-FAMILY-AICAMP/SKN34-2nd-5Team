# 트러블슈팅 — origin/main 병합 (2026-08-01)

대상: `af1787d`(로컬 시작점) → `3b6eae3`(v05 커밋) → `742b784`(병합 후 push)

## 1. 상황

로컬에서 v05 프런트 고도화 작업(F-5, H-1, QA, 번들 분할 등)을 커밋하지 않은 채
진행하던 중, `git fetch`로 원격에 2개 커밋이 먼저 올라와 있는 것을 확인했다.

- `983ed6f` — React 컨텍스트 훅 분리 + FastAPI·MySQL 문서 최신화
- `d20f577` — 독립 인증 서비스(`auth_service/`) 추가

두 브랜치가 같은 지점(`af1787d`)에서 갈라진 상태(diverged)였고, `983ed6f`가
건드린 파일이 로컬에서 미커밋 상태로 크게 수정 중이던 파일들과 대부분
겹쳤다(`OperationsContext.jsx`, `api/main.py`, 6개 페이지 컴포넌트 등).

## 2. 원인

**두 세션이 같은 파일을 다른 이유로 동시에 수정**했다.

| 대상 | 팀원 세션 | 이 세션 |
|---|---|---|
| `OperationsContext.jsx` | ESLint "Fast refresh" 경고 해소를 위해 훅 3개를 `operations-context.js`로 분리 | v05 화면 재구성 중 그대로 사용 |
| 6개 페이지 컴포넌트 | 훅 import 경로만 변경 | 컴포넌트 구조 자체를 대폭 재작성(SignalAtlas, DecisionRail 등 신규 컴포넌트 추가) |
| 판단 저장 로직 | 기존 `decisionStorage.js`(localStorage) 유지 | F-1 작업으로 서버(MySQL) 저장 전환, 키도 `sampleId` → `userId`로 변경 |
| `api/main.py` | `venv` → `.venv` 경로 오타 수정 | v05 라우터 4개 추가, CORS 쓰기 메서드 허용 |

이 상태에서 바로 `git pull`을 했다면 병합 충돌이 나거나(uncommitted
changes로 pull 자체가 거부됨), 최악의 경우 미커밋 상태에서 강제로 진행하다
작업을 잃을 위험이 있었다.

## 3. 대응 순서

### 3.1 진행 전 위험도 실측 (진짜 문제인지 먼저 확인)

무작정 겁먹고 병합을 피하거나, 반대로 무작정 pull하지 않고 **실제로 뭐가
겹치는지**를 커밋 diff와 파일 목록 교집합으로 먼저 쟀다.

```bash
git fetch --all
git log --oneline af1787d..origin/main      # 원격에 뭐가 있는지
git show <commit> --stat                     # 각 커밋이 뭘 건드리는지
git merge-base --is-ancestor HEAD origin/main # fast-forward 가능한지
```

`d20f577`(인증 서비스)는 `api/`, `app/`을 한 줄도 안 건드려서 충돌 위험이
없다는 걸 먼저 확인했고, 진짜 위험은 `983ed6f` 하나뿐이라는 걸 좁혔다.

### 3.2 먼저 내 작업을 커밋

미커밋 상태로 병합을 시도하면 실패하거나 변경사항이 뒤섞일 수 있어서,
v05 작업 전체를 하나의 커밋(`3b6eae3`)으로 먼저 남겼다. 스테이징은
`git add -A` 대신 `api/`, `app/`, `docs/`, `v05/` 경로를 명시해서, 실수로
엉뚱한 파일(예: `.env`)이 끼어드는 걸 원천 차단했다.

### 3.3 병합을 커밋 없이 시뮬레이션

```bash
git merge --no-commit --no-ff origin/main
# ... 결과 확인 ...
git merge --abort   # 문제없으면 나중에 다시 진행
```

`--no-commit`으로 실제 결과물을 열어보고 위험도를 확인한 뒤, 한 번
`--abort`로 되돌려서 사용자에게 먼저 보고했다. **자동 병합이 조용히
성공한 파일이 오히려 더 위험할 수 있다** — git이 "충돌 없음"으로 처리해도
로직이 깨질 수 있기 때문에, 자동 병합된 핵심 파일(`api/main.py`,
`OperationsContext.jsx`)도 직접 열어서 내용을 검증했다.

### 3.4 git이 잡아주지 않는 숨은 충돌 찾기

가장 중요한 단계였다. `983ed6f`는 **커밋 시점에 존재하던 파일**의 import
경로만 고쳤는데, 그 이후 이 세션에서 새로 만든 파일(`CommandPalette.jsx`,
`DecisionContext.jsx`)은 원격 커밋이 존재조차 몰랐던 파일이라 **git이
충돌로 표시하지 않는다.** 하지만 그 파일들은 여전히 옛 경로
(`context/OperationsContext`)에서 이제는 없어진 훅을 import하고 있어서,
병합이 "성공"해도 런타임에는 깨진다.

찾는 방법은 grep으로 전수 조사:

```bash
grep -rn "context/OperationsContext" app/src --include="*.jsx" --include="*.js"
```

이 방식으로 `CommandPalette.jsx`, `DecisionContext.jsx` 2개를 찾아 수동
수정했다.

### 3.5 충돌 해결 원칙

8곳의 실제 충돌(6개 파일)은 전부 같은 모양 — "팀원은 경로만 바꿈, 나는
같은 자리에 새 import를 추가함" — 이라 기계적으로 처리했다.

- 훅 import 경로: **팀원 방향**(`operations-context`)으로 통일
- 판단 저장 로직: **이쪽 방향**(서버 저장) 유지 — 의도된 아키텍처 변경이라
- 죽은 컴포넌트(`StatCard`/`SummaryCard`): **삭제 유지** — 사용처 0곳을
  먼저 grep으로 확인하고, `V05_WORK_SPEC.md`에 제거 근거가 있는 것도
  재확인한 뒤 결정

### 3.6 병합 후 남은 잠재 버그도 같이 정리

`OperationsPage.jsx`에만 `useMemo` 의존성 배열이 `[decisions]`로
남아있고 `eslint-disable`로 경고를 숨기고 있었다. 팀원이 다른 페이지
2곳에서 이미 고친 것과 동일한 버그(리뷰어 목록이 바뀌어도 재계산 안 됨)라,
같은 방식(`[decisions, reviewers]`)으로 맞추고 `eslint-disable` 주석도
제거했다.

### 3.7 검증

```bash
npm run lint    # 0 errors (팀원의 훅 분리로 기존 경고 3건도 함께 해소됨)
npm run build   # 코드 분할 유지, 진입 번들 242KB
```

+ 로컬 API 서버 재기동 후 v05 라우터 3개 응답 확인, 5개 화면(운영
홈/리뷰어 관리/Reviewer 360/플레이북/콘텐츠 위험/모델 신뢰) 전부 브라우저로
직접 열어 콘솔 오류 0건 확인.

## 4. 재발 방지 / 다음에 참고할 점

1. **작업을 오래 미커밋 상태로 두지 않는다.** 이번엔 커밋 없이 여러 세션
   분량의 변경이 쌓여있어서 원격과 겹치는 범위를 처음부터 정확히 가늠하기
   어려웠다. 기능 단위로 자주 커밋했다면 diff 검토가 훨씬 쉬웠을 것이다.
2. **`git merge --no-commit`으로 먼저 열어보고 판단한다.** 실제로 커밋하기
   전에 결과물을 검증할 수 있어, "일단 pull하고 문제 생기면 그때
   해결"보다 훨씬 안전했다.
3. **git 충돌 표시를 전적으로 믿지 않는다.** 두 브랜치가 각자 새로 만든
   파일이 서로의 리팩터링을 놓치는 경우, git은 충돌을 못 잡는다. 리팩터링성
   커밋(파일 이동/분리, 함수명 변경 등)을 받을 때는 전수 grep으로 옛 이름을
   찾아보는 습관이 필요하다.
4. **판단 저장 방식처럼 팀 전체에 영향 있는 설계 변경은 커밋 메시지에
   근거를 명시**하고 별도로 팀에 공유한다(`decisionStorage.js`가 이번
   병합으로 죽은 코드가 됐다는 점, 이 문서와 함께 전달 필요).

## 5. 관련 커밋

- `3b6eae3` — v05 프런트 고도화(병합 전 로컬 작업 커밋)
- `983ed6f` (origin) — React 컨텍스트 훅 분리
- `d20f577` (origin) — 독립 인증 서비스 추가
- `742b784` — 병합 커밋(push 완료)
