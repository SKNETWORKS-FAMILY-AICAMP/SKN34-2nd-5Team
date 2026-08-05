> **문서 상태: 역사 기록**
> 2026-07-28 React·Streamlit 패리티 작업 당시의 인수인계다.

> **경로 변경 안내(2026-07-28 이후)**: 이 문서는 작성 시점 기준 경로(`app/` = Streamlit,
> `frontend/` = React)로 쓰였다. 이후 `frontend/` → `app/`, 기존 `app/` →
> `archive/app_streamlit_v04/`로 이름이 바뀌었다. 아래 본문은 작성 당시 경로 그대로 둔다.

`C:\Users\playdata2\SKN34-2nd-5Team`에서 React/Streamlit v04 데이터 정합성 작업을 이어서 진행해줘.

## 배경

React 프론트엔드(`frontend/`)는 원래 합성 mock 데이터로 동작했는데, Streamlit 앱(`app/`, v04)은 `data/processed/predictions/final_test_retention_profiles_v04.parquet`(리뷰어 6,533명)의 실데이터를 읽고 있었다. 사용자가 이를 지적했다 — React도 Streamlit과 같은 실제 숫자를 보여줘야지, 지어낸 값을 쓰면 안 된다는 것. 그 이후 모든 작업은 두 앱을 브라우저에서 나란히 띄워 실제 화면에 표시되는 값을 직접 대조하며 검증했다(코드 리뷰만으로 끝낸 게 아님).

## 완료된 작업 (커밋 안 함 — 이번 세션에서 아무것도 커밋하지 않았음)

**데이터 파이프라인**: `scripts/export_frontend_data.py`는 Streamlit 앱 자체의 `app/core` 모듈(`load_app_data`, `risk_signals`, `strategy_for`, `DECISION_PLAYBOOKS`, `STATE_RECOMMENDATIONS`)을 그대로 재사용한다. React가 파생 로직을 JS로 다시 구현하지 않도록 하기 위해서다. 출력 파일:
- `frontend/src/data/{operations,trust,playbooks,strategies,regional,reviewers}.json` (번들, 총 약 6MB)
- `frontend/public/data/reviewer-details.json` (8.7MB, Reviewer 360 화면을 처음 열 때 지연 fetch, 번들에는 포함 안 됨)

모델/프로파일이 바뀌면 재실행:
    ./venv/Scripts/python.exe scripts/export_frontend_data.py

**리뷰어 6,533명 전체를 내보냄** (500명 서브셋이 아님 — 이건 이전에 과하게 조심해서 잘랐던 것으로, 사용자가 명시적으로 전체로 되돌리라고 요청함). 목록 페이지는 100명씩 표시하고 "더 보기 · 100명 추가" 버튼과 "전체 N명" 표시가 있음.

**실데이터로 재연결한 화면들, 각각 실행 중인 Streamlit(localhost:8501)과 대조 검증함**. `.claude/launch.json`에 두 서버가 모두 등록돼 있어 Browser 프리뷰 도구로 `preview_start({name: "frontend"})`(5173) / `preview_start({name: "streamlit"})`(8501)를 각각 열어 나란히 대조하면 됨:
- 운영 홈 — 실제 수치(6,533 / 1,307 / 87.4% / 28.9% / 1.45), 큐는 동적으로 구성
- 리뷰어 목록 — 100명씩 페이징, 실제 정렬 필드, CSV 내보내기, Streamlit과 동일한 필터
- 리뷰어 상세 — `reviewerId`로 key를 줘서 리뷰어 전환 시 컴포넌트가 깔끔하게 리마운트되도록 함(이 방식으로 기존에 있던 `set-state-in-effect` lint 에러 2건도 해결됨); `reviewer-details.json`을 지연 fetch; 근거 목록은 실제 심각도순 상위 3개 신호
- 신뢰 센터 — 실제 Macro F1/PR-AUC/ROC-AUC/Balanced Accuracy, 혼동 행렬, Top-K 커브, 피처 중요도 — Streamlit과 완전히 일치하는 것 확인함(0.552 / 0.579 / 0.756 / 56.5%)
- 플레이북 — 실제 `DECISION_PLAYBOOKS` 내용, 판단→결정 분포, 리뷰어 상세에서의 딥링크(`/playbook?reviewer=<id>`)가 해당 플레이북을 강조 표시
- 지역 위험 — **방금 새로 구성함**. state 단위("권역") 집계로 바꿈: 리뷰어의 권역 = 2017~2018 피처 윈도우에서 가장 많이 리뷰한 state, `data/interim/restaurant_reviews.parquet` ↔ `restaurant_businesses.parquet` 조인(조인 매칭률 100%, 코호트 커버리지 100%, 14개 권역, 최소 49명이라 30명 표본 기준에 걸려 숨겨지는 권역 없음). 이전에 "데이터 없음" 빈 상태였던 걸 대체함 — 데이터가 없었던 게 아니라 파생이 필요했던 것. 이전의 가짜 8개 도시 숫자는 제거함(실제 숫자를 계산해보니 전혀 안 맞았음).

mock 파일은 전부 삭제함(`frontend/src/mocks/*`, 그리고 이제 고아가 된 컴포넌트들 `PlaybookCard`, `PlaybookFilters`, `RegionalFilters`, `MonthlyActivityChart`, `ModelPerformanceChart`, `RoadmapTimeline`, `ValidationChecklist`).

`docs/05_ui_ux/REACT_V04_PARITY_PLAN.md`에 계획이 정리돼 있고, 화면별로 무엇을 왜 바꿨는지 섹션이 있음(지역 정의 근거 포함). 추가 작업 전에 꼭 읽어볼 것.

## 아직 처리 안 된 후속 사항

세션 종료 전에 사용자가 지적한 열린 질문 하나: 지역 데이터 export의 "리뷰 공급 변화" 값이 **모든 권역에서 예외 없이 +50%~+145% 증가**로 나온다(권역별로 합산한 2017년 baseline 리뷰 수 대비 2018년 recent 리뷰 수 비교). 이게 실제 지역별 신호라기보다, 코호트 전체에 적용되는 baseline/recent 윈도우 정의 자체에서 나오는 구조적 아티팩트일 가능성이 있는데 아직 조사 안 함. 이 컬럼을 UI에서 의미 있는 지표로 쓰기 전에, 이 패턴이 지역과 무관한 전체 집계에서도 나타나는지 확인 필요 — 만약 6,533명 전체가 코호트 차원에서 증가 추세라면, 이 지표 자체를 다시 생각해봐야 할 수 있음(예: CRM 대상 선정 기준 자체가 "중간에 더 활발해진" 리뷰어를 끌어당기는 방향으로 작동해서 생기는 결과일 수도 있음).

## 그 외 남은 것

- lint 통과 확인됨(`frontend/`에서 `npm run lint`), build 통과 확인됨(`npm run build`) — 추가 변경 후에는 다시 확인할 것
- 아무것도 커밋 안 함. 사용자가 커밋 전에 diff 리뷰를 원하거나, 아니면 바로 커밋을 요청할 수도 있음 — 범위를 임의로 가정하지 말고 먼저 `git status`, `git diff`로 확인할 것
- PR은 아직 안 열었음
