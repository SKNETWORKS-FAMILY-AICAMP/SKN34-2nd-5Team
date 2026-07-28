# React ↔ Streamlit v04 화면 통합 계획

## 목적

`app/` (v04 Streamlit)을 기준(source of truth)으로 `frontend/` (React)의 화면 구성·수치·문구·인터랙션을 맞춘다.

이번 작업은 "화면을 Streamlit v04와 동일하게 맞추는 것"이 목표이며, 아래 유지 항목은 예외로 둔다.

## 데이터 연결 방식 (2026-07-28 변경)

당초 React는 합성 mock으로 동작했으나, Streamlit v04는 DB 없이도 `data/processed/predictions/final_test_retention_profiles_v04.parquet`에서 **실데이터**를 읽고 있다. mock 숫자를 손으로 맞추면 모델이 갱신될 때마다 어긋나므로, 실데이터를 JSON으로 내보내 React가 읽도록 바꿨다.

- 내보내기 스크립트: `scripts/export_frontend_data.py`
- 출력: `frontend/src/data/{operations,reviewers,trust,playbooks}.json`
- 모델·프로파일이 갱신되면 재실행한다:

```bash
./venv/Scripts/python.exe scripts/export_frontend_data.py
```

이 스크립트는 로직을 JS로 재구현하지 않고 **Streamlit의 `app/core` 모듈을 그대로 호출**한다(`load_app_data`, `risk_signals`, `strategy_for`, `DECISION_PLAYBOOKS` 등). 두 앱이 서로 다른 구현으로 갈라지는 것을 막기 위해서다.

`frontend/src/mocks/`는 제거했다. FastAPI가 붙으면 `frontend/src/data/index.js`만 API 호출로 교체하면 된다.

작성 배경: 2026-07-28, 팀원이 만든 React 초안을 v04 Streamlit(PROJECT 모드, `http://localhost:8501`)과 나란히 띄워 화면별로 대조한 뒤 정리한 계획.

---

## 0. 절대 건드리면 안 되는 것

React가 Streamlit보다 나은 부분이라 스트림릿에 맞춰 되돌리지 않는다.

1. **관리자 판단 저장 방식** — `frontend/src/services/decisionStorage.js`의 `localStorage` 방식 유지. (Streamlit은 서버 로컬 JSON 공유 저장이지만, 이 프로젝트는 지금 단계에서 브라우저별 가벼운 저장을 의도적으로 유지하기로 함. DB 연동은 고도화 단계에서 처리.)
2. **리뷰어 상세 화면의 탭 전환 UI** — Streamlit의 "항상 펼침" 구조로 되돌리지 않는다. 탭 구성 자체는 3번 항목대로 4탭으로 조정한다.
3. **운영 홈 상단 3열 요약 카드** (전체 리뷰어 / 우선 검토 대상 / 판단 완료) 유지.
4. **리뷰어 관리 목록의 필터 배치 방식** (검색+필터를 한 줄 그리드로 보여주는 레이아웃) 유지. 필터 "옵션 종류"는 아래 지시대로 스트림릿 수준으로 채운다.
5. **플레이북의 카드 리스트 브라우징 방식** 유지. Streamlit에만 있는 "현재 리뷰어에게 추천" 딥링크 기능은 카드 리스트 위에 강조 표시를 얹는 방식으로 추가한다(단일 뷰로 되돌리지 않는다).
6. **전체 화면 색상 토큰**(`#137A5A`, `#17211D`, `#68736D`, `#DDE4DF` 등)과 반응형 그리드 패턴 유지.

---

## 1. 전역 수정 — 완료

- `modelVersion`, 표본 수, 정밀도·재현율·Lift를 하드코딩하지 않고 `operations.json`에서 읽는다. 실행 중인 Streamlit PROJECT 모드와 값이 일치함을 확인했다(6,533명 / 1,307명 / 87.4% / 28.9% / 1.45).
- 데이터 모드 배지는 `dataMode`를 그대로 반영해 "PROJECT"로 표시한다.

## 2. 운영 홈 (`frontend/src/pages/OperationsPage.jsx`)

- 정책 패널에 재현율 한계 캡션 추가: "한 번에 20%만 볼 수 있어 최대로 잡아도 {recall_ceiling}%까지가 한계입니다" (`app/core/components.py:166` 로직 참고).
- 우선 검토 큐(`PriorityQueue`)를 decisionStorage와 연동 — 이미 판단이 저장된 리뷰어는 큐에서 제외하고, 미검토 리뷰어 중 우선순위 상위 5명만 동적으로 노출 (지금은 mocks 고정 5명이라 판단을 저장해도 큐가 안 바뀜, `app/views/operation_home.py:35-39` 로직 참고).
- 큐 항목 순위 배지에 1~2위 strong / 나머지 soft 톤 구분 추가.

## 3. 리뷰어 관리 목록 (`frontend/src/pages/ReviewerListPage.jsx`, `ReviewerFilters.jsx`)

- eyebrow 문구의 하드코딩된 "REACT" 텍스트 제거, `model_version` 동적 표시로 교체.
- 모델 판단 필터를 다중선택으로 변경, 기본값을 `["약화 우세", "중단 우세"]`로 설정 (`app/views/risk_queue.py:80-86`).
- 위험 유형 빠른 필터(단일 선택) + 핵심 행동 신호 다중선택을 별도로 추가(AND 조건).
- "통합 검토 범위" 필터(통합 상위 20% / 전체 / 상위 20% 제외) 추가.
- 정렬 옵션을 5종으로 확장: 통합 우선순위, 중단 점수 높은 순, 약화 점수 높은 순, 활동 감소순, 리뷰 공백순 (기존 "최근 활동 월 적은 순"은 원본에 없는 항목이라 제거 검토).
- CSV 다운로드 버튼 추가.
- 위험 유형 컬럼에 `SIGNAL_LABELS` 매핑 적용 (`app/core/insights.py:52-58` 참고).

## 4. 리뷰어 상세 (`frontend/src/pages/ReviewerDetailPage.jsx`)

- 연도 라벨 수정: 비교(2017) · 선정·피처 마감(2018) · 실제 상태 검증(2019). 지금 mock은 선정 연도를 2017로 잘못 표기하고 있음 (`reviewerDetailData.js`).
- 헤더 배지에 CRM 대상 여부("통합 상위 20% 검토 대상" / "일반 모니터링") 추가(위험 유형 배지는 유지하되 병기).
- "전체 n명 중 rank위" 뒤에 "상위 X.X%" 퍼센타일 표기 추가.
- 하단 탭 구조를 4개로 재구성한다(React의 탭 UI는 유지, 내용만 재배치):

  | 탭 | 내용 | 데이터 |
  |---|---|---|
  | 활동 변화 | 그룹 막대 차트: 리뷰수/활동월/고유음식점, 비교연도 vs 선정연도 (Streamlit `profile_activity`와 동일 로직) | v04 mock에 이미 있는 `baseline_*`/`recent_*` 필드로 구현 가능 |
  | 작성 주기 | 지금 "활동 변화"로 잘못 이름 붙은 기존 interval 차트 — 라벨만 "작성 주기"로 정정 | 이미 구현되어 있음 |
  | 월별 타임라인 | 라인 차트 자리는 유지하되, `reviewer_monthly_activity` 소스 데이터 파일이 저장소에 없으므로(Streamlit도 동일) **빈 상태/대기 화면**으로 표현: "월별 활동 타임라인 — 데이터 연결 필요" + 필요 데이터 설명("리뷰 작성 월, 월별 리뷰 수, 월별 고유 음식점 수") + 활성화 조건("`reviewer_monthly_activity_v01.parquet` 계약 검증 완료") | `app/views/reviewer_360.py:286-298` empty_state 문구 그대로 이식 |
  | 사후 검증 | 기존 그대로 유지 | 이미 구현되어 있음 |

  참고: "활동 변화" 탭 차트는 탭 위에 항상 떠 있는 `ActivityChangeGrid` 타일과 같은 숫자를 다시 보여주는 것(Streamlit 원본도 동일하게 중복 표시함) — 의도된 중복이니 그대로 둔다.

- "왜 우선 검토 대상인가" 근거를 고정 4개가 아니라, `risk_signals` 로직처럼 심각도 순 상위 3개를 동적으로 선정하도록 변경 (`app/core/insights.py`의 신호 후보 목록에 "평균 작성 간격" 근거도 추가).
- "플레이북에서 전략 확인" 클릭 시 리뷰어 컨텍스트(`sample_id`, `risk_type`, `priority_rank` 등)를 state 또는 query param으로 전달하고, 플레이북 페이지가 이를 받아 "현재 리뷰어에게 추천" 강조 표시를 하도록 연결.
- "CRM 캠페인 배정" future_integration 카드(비활성 상태로) 추가.
- 판단 저장 후 "다음 리뷰어로" 바로가기 버튼 추가.
- 비교 연도 활동 없음 엣지 케이스("{comparison_year}년 비교 활동 없음 · 전년도 대비 변화율 계산 불가") 표현 추가.

## 5. 리텐션 플레이북 (`frontend/src/pages/PlaybookPage.jsx`)

- "현재 리뷰어에게 추천" 모드 추가 (4번 항목에서 전달받은 컨텍스트로 해당 카드를 상단 강조 또는 필터링).
- "판단별 규모" 분포 바 차트 추가 (실제 `manager_decision` 분포 기반).
- "이 판단에 해당하는 리뷰어" 테이블(상위 10명) 추가.
- "캠페인 실행과 성과 추적" 섹션 추가: capability grid(대상 배정/접촉 이력/복귀 관찰/성과 비교, 전부 "정의·데이터 필요" 상태) + 비활성화된 캠페인 생성 폼(담당자/채널, disabled).
- "개입 효과가 검증된 처방이 아니며, 의학적 상태를 의미하지 않습니다" 경고 문구 추가.

## 6. 콘텐츠 위험 / 지역 분석 — 권역 기준으로 연결 완료 (2026-07-28)

Streamlit이 기다리던 `regional_risk_summary_v01.csv`는 없지만, 원천 데이터로 직접 집계할 수 있음을 확인해 연결했다.

- **지역 정의(권역)**: 리뷰어가 관찰 구간(2017~2018)에 **가장 많이 리뷰한 state**. `restaurant_reviews.parquet` ↔ `restaurant_businesses.parquet` 조인(매칭률 100%). city 단위는 208개로 잘게 쪼개져 교외가 metro에서 분리되므로 state로 묶고, 각 권역은 대표 도시명을 함께 표시한다. 거주지·직장·생활 반경은 추론하지 않는다.
- **표본 기준**: 30명. 14개 권역 전부 30명 이상이라 현재 숨겨지는 권역은 없고, 미만이면 배지로 표시만 한다.
- **커버리지**: 6,533명 100%, 14개 권역(PA 1,433 … DE 49).
- 집계는 `export_regional()`이 담당하고 결과는 `frontend/src/data/regional.json`.

이전 초안의 8개 도시 가짜 수치는 제거했다(실제 값과 전부 달랐다 — 예: Philadelphia 824명/49% → 실제 1,433명/58.8%).

### 리뷰 공급 변화 지표 제거 (2026-07-28)

`reviewSupplyChange`(권역별 baseline→recent 리뷰 수 합계 변화율)를 UI에서 뺐다. 원인 조사 결과, 실제 지역 신호가 아니라 코호트 정의 자체의 구조적 아티팩트였다.

- 코호트 자격 조건(`pipeline/v04/preprocessing.py:328`)이 "recent"가 되는 선정 연도에만 `review_count >= 10 AND active_months >= 3`을 요구하고, "baseline"이 되는 전년도에는 하한이 없다(0도 허용).
- 그 결과 전체 6,533명 집계에서도 baseline 77,334 → recent 131,860(+70.5%)로 항상 증가하며, 76%가 recent > baseline이다. 권역별 편차(+50%~+145%)는 이 구조적 하한 주변의 표본 노이즈일 뿐이다.
- 원래 이 지표는 Streamlit `regional_risk.py`의 "데이터 연결 대기" 화면에서부터 **"선택"** 항목으로 예고돼 있었고, 목적은 "음식점 리뷰 감소 지역 탐지"였다. 그런데 위 구조적 하한 때문에 이 지표로는 감소를 원리상 절대 탐지할 수 없다 — 목적을 달성 불가능한 지표였다.
- 조치: `scripts/export_frontend_data.py`의 `export_regional()`에서 계산 제거, `RegionalRiskPage.jsx`/`RegionalRiskTable.jsx`에서 컬럼·정렬옵션 제거. capability grid의 "리뷰 공급 변화" 항목은 "데이터 연결 필요" 상태로 되돌리고 "지표 재설계 필요" 캡션을 추가했다(완전 삭제하지 않은 이유: 원본 v01 데이터 계약에 예고된 항목이라 실제 지역 집계 파일이 연결되면 다시 검토할 자리를 남겨둠).

### 참고 · 데이터가 없어 보류했던 당시 기록

Streamlit(PROJECT 모드 포함)도 실제 지역 집계 데이터 파일(`reports/tables/regional_risk_summary_v01.csv`, `data/processed/regional_risk_summary_v01.parquet`)이 저장소에 없어 지금은 대기 화면만 보여준다(2026-07-28 직접 확인).

- 현재 8개 도시의 지어낸 위험률/순위 데이터(`regionalRiskData.js`)를 **전부 제거**한다.
- Streamlit과 동일하게 **"데이터 연결 대기" 빈 상태 화면**으로 교체한다:
  - 상단: "콘텐츠 공급 위험을 지역 단위로 준비합니다" + "정의·데이터 필요" 배지
  - "이 화면은 v04 모델 결과가 아닙니다..." 출처 안내 문구
  - 좌측: "지역별 위험 집계 연결 대기" 빈 상태 카드 — "지도나 순위표에 임의 수치를 넣지 않습니다" 문구 + 필요 필드 설명(활동 리뷰어/고위험 리뷰어/고위험 비율/리뷰 공급 변화)
  - 우측: "해석 원칙" — "거주지, 직장, 실제 생활 반경을 추론하지 않습니다"
  - "활성화 순서" 3단계 (지역 정의 → 표본 기준 → 데이터 연결)
  - 하단: "연결 후 운영 기능" 4항목 capability grid
  - (`app/views/regional_risk.py:21-121` 문구를 그대로 이식)
- 기존 필터/차트/테이블 컴포넌트(`RegionalFilters`, `RegionalRiskChart`, `RegionalRiskTable`)는 삭제하지 말고, 실제 지역 데이터가 연결된 이후를 위해 보존만 해두고 화면에서는 숨긴다.

## 7. 신뢰 센터 (`frontend/src/pages/TrustCenterPage.jsx`)

- 탭 구성을 4개로 맞춘다: 성능과 Top-K / 시간 분할·누수 방지 / 피처 근거 / 제품 상태·로드맵 (지금의 "검증 체크" 탭은 유지할지 별도로 검토 — 있으면 유용하지만 원본엔 없음).
- "성능과 Top-K" 탭에 실제 지표(Macro F1/PR-AUC/ROC-AUC/Balanced Accuracy), 클래스별 성능 막대, 혼동행렬, Top-K 커브를 추가 (`mocks/trustCenterData.js` 확장).
- "시간 분할·누수 방지" 탭 추가: 비교/선정/검증 3단계 타임라인 + 누수 방지 원칙 4항목.
- "피처 근거" 탭에 실제 permutation importance 수치·차트 추가(정적 체크리스트만으로는 부족). "반응과 품질"(별점/Useful/Funny·Cool) 그룹은 원본 근거가 없으므로 실제 피처 중요도 데이터 확인 후 유지 여부 결정.
- "제품 로드맵" 탭 주제를 "제품이 사용자에게 제공하는 기능 로드맵"(운영 홈/검토 큐, 위험 유형 플레이북, 월별 활동 타임라인, 지역 콘텐츠 위험, 캠페인 성과 추적, 개인별 SHAP·보정 확률)으로 재정의. 현재의 "개발 프로젝트 진행 단계" 로드맵은 별도 섹션으로 옮기거나 제거.

---

## 작업 순서 제안

1. 전역 mock 상수(`model_version`, 표본 수) 동기화 — 가장 쉽고 전체 화면에 영향.
2. 콘텐츠 위험 화면을 빈 상태로 교체 (원칙 위반 해소가 최우선).
3. 리뷰어 상세 4탭 재구성 + 연도 라벨 수정.
4. 리뷰어 관리 목록 필터/정렬/CSV 보강.
5. 운영 홈 큐-decisionStorage 연동.
6. 플레이북 재구성.
7. 신뢰 센터 실데이터 반영.

## 완료 기준

- 각 화면 수정 후 `npm run dev`로 브라우저에서 직접 확인한다(`npm test`/`lint` 통과만으로 완료 판단하지 않는다).
- 콘텐츠 위험/월별 타임라인은 "빈 상태 화면 문구가 Streamlit과 동일한지"를 기준으로 검증한다.
- 나머지 화면은 Streamlit PROJECT 모드(v04 실데이터, `http://localhost:8501`)와 나란히 띄워 놓고 항목별로 대조한다.
