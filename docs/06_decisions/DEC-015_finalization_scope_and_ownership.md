# DEC-015. Finalization 범위와 소유권

> **문서 상태: 현재 기준**
> Team Final Release의 작업 범위, 담당, 완료 조건과 대상 PR에 적용한다.

## 문서 정보

| 항목 | 내용 |
|---|---|
| 상태 | 승인 |
| 승인일 | 2026-09-03 |
| 기준 브랜치 | `release/finalization` |
| 원본 결정표 | [Yelp Reviewer Retention Ops 최종 의사결정표 v1](https://app.notion.com/p/3c2e94b44d078021a9f4e4351e4f04f4) |
| 최신 상태 근거 | [AWS HTTPS 재배포 보고서](../02_reports/04_aws_https_redeployment_report_2026-09-02.md) |
| 실행 절차 | [FINALIZATION_EXECUTION_PLAN](../07_history_and_handoff/FINALIZATION_EXECUTION_PLAN.md) |

## 1. 결정

현재 Team Final Release에서는 아래 표의 `필수` 항목만 수행한다. `고도화`,
`제외`, `안 해도 됨` 항목은 구현하지 않는다. 조건부 항목은 명시된 조건이 충족될
때만 별도 승인을 받아 수행한다.

제품의 세 축은 다음과 같다.

1. 지역별 리뷰 공급 변화 및 이상 탐지
2. 기존 핵심 리뷰어의 활동 약화·중단 예측과 우선 검토
3. 신규 핵심 리뷰어 유입 변화 관찰 및 우선 검토 대상 연결

Consumer 서비스, 실제 개입 효과 측정, 신규 데이터 재학습, 추가 모델 경쟁은 이번
릴리스 범위가 아니다. 실제 데이터 없이 효과 수치나 모델 결과를 만들지 않는다.

## 2. 상태 판정 원칙

- Notion 원본은 2026-08-21의 범위 결정 근거로 보존한다.
- 현재 상태는 저장소의 테스트·QA·배포 보고서 중 더 최신인 근거로 갱신한다.
- `구현 완료`와 `검증 완료`를 구분한다. 실환경 검증이 남으면 `부분 완료`다.
- 과거 QA 보고서는 당시 결과이므로 수정하지 않는다.
- 담당자가 `공동`인 항목도 한 PR에서 한 명이 파일을 선점해 순차 수정한다.

## 3. A — 안정성·보안·실제 오류

| ID | 작업 | 분류 | 현재 상태 | 담당 | 완료 근거/조건 | 대상 PR |
|---|---|---|---|---|---|---|
| A01 | Retention 조회 API 인증 적용 | 필수 | 검증 완료 | 김동섭 | 운영 HTTPS 미인증 조회 401 | 완료 근거 유지 |
| A02 | OPERATOR 담당 권역 서버 강제 | 필수 | 부분 완료 | 김동섭 | 실제 OPERATOR 담당 권역 성공·타 권역 403, VIEWER 403, ADMIN 전체 권역 확인 | `fix/a-app-resilience` |
| A03 | HTTPS 적용 | 필수 | 검증 완료 | 김동섭 | 443·유효 인증서·HTTP redirect·자동 갱신 확인 | 완료 근거 유지 |
| A04 | Secure Cookie 설정 | 필수 | 검증 완료 | 김동섭 | production health와 실제 로그인 쿠키 확인 | 완료 근거 유지 |
| A05 | Production CORS 설정 정리 | 필수 | 부분 완료 | 김동섭 | 비허용 cross-origin 응답에 허용 헤더가 없음을 운영 환경에서 확인 | `fix/a-app-resilience` |
| A06 | Snooze 저장·복원 오류 재현 및 수정 | 필수 | 부분 완료 | 김동섭 | 새로고침·재로그인 뒤 저장값 복원 PASS | `fix/a-app-resilience` |
| A07 | History에 메모·Snooze·담당자 변경 내역 제공 | 필수 | 부분 완료 | 김동섭 | React 상세 UI에서 실제 API 필드와 변경 전후 확인 | `fix/a-app-resilience` |
| A08 | Operations API 실패 시 전체 앱 차단 제거 | 필수 | 미실행 | 김동섭 | 장애 중 독립 화면 사용 및 부분 오류 안내 PASS | `fix/a-app-resilience` |
| A09 | Decision API 실패 시 전체 앱 차단 제거 | 필수 | 미실행 | 김동섭 | 조회 화면 유지·쓰기 기능 오류 안내·복구 PASS | `fix/a-app-resilience` |
| A10 | 사진·지도·일부 데이터 오류 시 부분 fallback | 필수 | 미실행 | 김동섭 | 실패한 블록만 대체되고 핵심 업무 흐름 유지 | `fix/a-app-resilience` |
| A11 | 발표 때 발생한 오류 재현·확인 | 필수 | 부분 완료 | 김동섭 중심·공동 QA | 재현 절차와 수정 후 PASS 증거 기록 | `test/final-regression` |
| A12 | 기존 QA FAIL 17건 최신 배포본 재검증 | 필수 | 미실행 | 김동섭 중심·공동 QA | 17건 최신 판정과 근거 기록 | `test/final-regression` |
| A13 | DB/API 장애·5xx 핵심 시나리오 QA | 필수 | 미실행 | 김동섭 중심·공동 QA | 핵심 장애 시나리오 결과 기록 | `test/final-regression` |
| A14 | Slow network 중복 저장 검증 | 고도화 | 백엔드 부분 검증 | 개인 고도화 | 실제 slow-network E2E 증거 | 현재 범위 제외 |

A01·A03·A04는 2026-09-02 AWS 검증으로 완료됐다. 이 결과를 다시 구현하지 않는다.
A02·A05·A06·A07은 코드 또는 백엔드 검증만으로 완료 처리하지 않는다.

## 4. B — 제품 방향·Home·핵심 UX

| ID | 작업 | 분류 | 현재 상태 | 담당 | 완료 조건 | 대상 PR |
|---|---|---|---|---|---|---|
| B01 | Home에서 `공급 변화 / 핵심 리뷰어 / 신규 유입` 3축 명확화 | 필수 | 검증 필요 | 이홍규 | 첫 화면에서 세 축과 우선 조치가 구분됨 | `feat/core-product-ux` |
| B02 | `지역 → 원인 → 사람 → 행동` 흐름 강화 | 필수 | 검증 필요 | 이홍규 | 주요 CTA로 문맥을 유지하며 다음 단계 이동 | `feat/core-product-ux` |
| B03 | 공급 감소 지역의 원인 설명 강화 | 필수 | 검증 필요 | 이홍규 | 실제 공급·활동·신규 유입 근거만 표시 | `feat/core-product-ux` |
| B04 | 지역 → 핵심 리뷰어 관리 CTA 연결 | 필수 | 검증 필요 | 이홍규 | 선택 지역을 유지한 검토 큐 이동 PASS | `feat/core-product-ux` |
| B05 | 지역 → 신규 리뷰어 분석 CTA 연결 | 필수 | 검증 필요 | 이홍규 | 선택 지역의 신규 유입 대상 연결 PASS | `feat/core-product-ux` |
| B06 | Reviewer 위험 근거 → 추천 행동 연결 | 필수 | 검증 필요 | 이홍규 | 행동마다 실제 활동 근거가 연결됨 | `feat/core-product-ux` |
| B07 | 활동 반경 변화 → 추천 근거 연결 | 고도화 | 미착수 | 개인 고도화 | 별도 승인 필요 | 현재 범위 제외 |
| B08 | 위험 음식점 변화 근거 표시 | 고도화 | 미착수 | 개인 고도화 | 별도 승인 필요 | 현재 범위 제외 |
| B09 | 지역 캠페인 분류 문구 수정 | 필수 | 검증 필요 | 이홍규 | 데이터·정책과 문구가 일치 | `feat/core-product-ux` |
| B10 | Queue → Reviewer 360 지역·필터 context 유지 | 필수 | 미해결 | 이홍규·김동섭 협의 | 이동·뒤로가기·새로고침 문맥 복원 PASS | `feat/core-product-ux` |
| B11 | 권한별 CTA 비활성 또는 숨김 처리 | 필수 | 부분 완료 | 김동섭 우선 | VIEWER 쓰기 UI 차단과 서버 403 일치 | `fix/a-app-resilience` |
| B12 | Home의 작동하지 않는 순위 버튼 등 회귀 오류 | 필수 | 재현 필요 | 이홍규 | 재현된 오류 수정 후 브라우저 PASS | `feat/core-product-ux` |
| B13 | Trust 모바일 overflow | 고도화 | 미해결 | 개인 고도화 | 별도 승인 필요 | 현재 범위 제외 |
| B14 | 접근성 전면 개선 | 고도화 | 부분 검증 | 개인 고도화 | 별도 승인 필요 | 현재 범위 제외 |
| B15 | 최소 온보딩·사용 가이드 | 필수 | 미착수 | 이홍규 | 첫 사용자가 제품·용어·업무 순서를 확인 | `feat/core-product-ux` |
| B16 | 화면 정보량·기능 복잡성 정리 | 필수 | 검증 필요 | 이홍규 | 세 축과 핵심 업무를 유지하며 불필요 요소 축소 | `feat/core-product-ux` |
| B17 | 중복·legacy 화면 정리 | 고도화 | 후보만 존재 | 개인 고도화 | 사용 여부 확인 후 별도 승인 | 현재 범위 제외 |

## 5. C — ML·DL·평가 정합성

| ID | 작업 | 분류 | 현재 상태 | 담당 | 완료 근거/조건 | 대상 PR |
|---|---|---|---|---|---|---|
| C01 | pooled Expanding-Time OOF 모델 선택 방식 확인 | 필수 | 검증 완료 | 모델 담당 | 승인된 OOF 비교와 최종 모델 선택 근거 보존 | 완료 근거 유지 |
| C02 | 2018 평가의 `Final Test` 명칭 재검토 | 필수 | 변경 불필요·검증 완료 | 모델 담당 | 모델 선정에 쓰지 않은 분리 평가임을 문서에서 명시 | 완료 근거 유지 |
| C03 | OOF / Holdout / Test 용어 통일 | 필수 | 문서 보완 필요 | 이홍규·모델 담당 확인 | README와 최종 문서에서 정의 일치 | `docs/final-product-story` |
| C04 | `risk_score ≠ 이탈확률` UI·문서 명시 | 필수 | 완료 | 이홍규 | 현재 경고 문구와 표현 원칙 유지 | 완료 근거 유지 |
| C05 | F1 외 Top-K·Lift 운영 지표 강조 | 필수 | 문서 보완 필요 | 이홍규 | README에서 모델 성능과 운영 용량 연결 | `docs/final-product-story` |
| C06 | 모델·코호트·DB 버전 역할 구분 | 필수 | 문서 보완 필요 | 이홍규·모델 담당 확인 | `코호트 v04`, `운영 모델 v05_05_dl`, DB `model_version` 역할을 구분하며 억지로 동일화하지 않음 | `docs/final-product-story` |
| C07 | 최종 모델 artifact·SHA·생성 위치 정리 | 필수 | 완료 | 모델 담당 | 기존 체크섬·재생성 경로 유지 | 완료 근거 유지 |
| C08 | 모델 재현 pipeline 최종 실행 | 필수 | 완료 | 모델 담당 | 기존 재현 결과 유지 | 완료 근거 유지 |
| C09 | 성능 지표 재계산 결과 확인 | 필수 | 완료 | 모델 담당 | 기존 검산 결과와 수치 유지 | 완료 근거 유지 |
| C10 | 새로운 모델 추가 실험 | 안 해도 됨 | 미착수 | — | 수행하지 않음 | 현재 범위 제외 |
| C11 | F1 1~2% 향상 목적 Optuna 재탐색 | 안 해도 됨 | 미착수 | — | 수행하지 않음 | 현재 범위 제외 |
| C12 | Calibration 후 확률 서비스 | 고도화 | 미착수 | 개인·팀 | 확률 의사결정 필요와 calibration 검증 후 재논의 | 현재 범위 제외 |
| C13 | 새로운 완전 미사용 미래 Holdout 확보 | 고도화 | 데이터 없음 | 팀 협의 | 신규 미래 데이터 확보 후 재논의 | 현재 범위 제외 |

C 영역의 모델 구조, 코호트, 시간 분할, 성능 수치와 산출물은 변경하지 않는다.
문서 정합성 수정만 모델 담당 확인을 거쳐 별도 PR에서 수행한다.

## 6. D — 운영 결과·효과 측정·재학습

| ID | 작업 | 분류 | 현재 상태 | 담당 | 재검토 조건 | 대상 PR |
|---|---|---|---|---|---|---|
| D01 | 실제 실행 운영안 기록 | 고도화 | 실제 운영 데이터 없음 | 개인 설계 | 실제 운영 시작 | 현재 범위 제외 |
| D02 | 개입 실행일 저장 | 고도화 | 미착수 | 개인 | 실제 운영 시작 | 현재 범위 제외 |
| D03 | 30일 Outcome | 고도화 | 데이터 없음 | 개인 설계 | 30일 사후 데이터 확보 | 현재 범위 제외 |
| D04 | 60일 Outcome | 고도화 | 데이터 없음 | 개인 설계 | 60일 사후 데이터 확보 | 현재 범위 제외 |
| D05 | 90일 Outcome | 고도화 | 데이터 없음 | 개인 설계 | 90일 사후 데이터 확보 | 현재 범위 제외 |
| D06 | 리뷰 수 회복 측정 | 고도화 | 데이터 없음 | 실제 데이터 필요 | 개입 전후 데이터 확보 | 현재 범위 제외 |
| D07 | 리뷰 재개율 측정 | 고도화 | 데이터 없음 | 실제 데이터 필요 | 실제 개입 데이터 확보 | 현재 범위 제외 |
| D08 | 지역 리뷰 공급 회복률 측정 | 고도화 | 데이터 없음 | 실제 데이터 필요 | 실제 운영 데이터 확보 | 현재 범위 제외 |
| D09 | Treatment / Control 설계 | 고도화 | 미착수 | 실제 실험 필요 | 실험 승인·표본 확보 | 현재 범위 제외 |
| D10 | 운영안별 효과 비율 계산 | 고도화 | 계산 불가 | 실제 실험 필요 | 인과효과 검증 데이터 확보 | 현재 범위 제외 |
| D11 | Outcome dataset 생성 | 고도화 | 선행 데이터 없음 | 개인·팀 | D01~D10 근거 확보 | 현재 범위 제외 |
| D12 | 신규 데이터 재학습 | 고도화 | 신규 데이터 없음 | 팀 | 신규 실제 데이터 확보 | 현재 범위 제외 |
| D13 | Data / Prediction drift | 고도화 | 운영 기간 데이터 없음 | 팀 | 운영 기간 데이터 확보 | 현재 범위 제외 |
| D14 | Challenger 모델 운영 | 고도화 | 미착수 | 팀 | 실서비스 운영 단계 | 현재 범위 제외 |
| D15 | 자동 재학습 | 안 해도 됨 | 미착수 | — | 현재 수행하지 않음 | 현재 범위 제외 |

## 7. E — 일반 사용자 서비스

E01~E12는 강사 피드백을 반영한 개인 고도화 후보이며 Team Final Release에서
구현하지 않는다.

| ID | 작업 | 분류 | 현재 상태 | 담당 | 재검토 조건 | 대상 PR |
|---|---|---|---|---|---|---|
| E01 | 일반 사용자용 핵심 리뷰어 탐색 화면 | 고도화 | 미착수 | 개인 | Team Final Release 이후 | 현재 범위 제외 |
| E02 | 지역별 핵심 리뷰어 검색 | 고도화 | 미착수 | 개인 | Consumer MVP 승인 | 현재 범위 제외 |
| E03 | 음식 카테고리별 핵심 리뷰어 탐색 | 고도화 | 미착수 | 개인 | Consumer MVP 승인 | 현재 범위 제외 |
| E04 | 일반 사용자용 Reviewer Profile | 고도화 | 미착수 | 개인 | Consumer MVP 승인 | 현재 범위 제외 |
| E05 | 해당 리뷰어가 리뷰한 맛집 제공 | 고도화 | 미착수 | 개인 | Consumer MVP 승인 | 현재 범위 제외 |
| E06 | 리뷰어가 높게 평가한 맛집 제공 | 고도화 | 미착수 | 개인 | Consumer MVP 승인 | 현재 범위 제외 |
| E07 | 리뷰어의 주요 활동 지역 시각화 | 고도화 | 미착수 | 개인 | Consumer MVP 승인 | 현재 범위 제외 |
| E08 | 추천 맛집 지도 탐색 | 고도화 | 미착수 | 개인 | Consumer MVP 승인 | 현재 범위 제외 |
| E09 | Reviewer Follow / Save | 고도화 | 미착수 | 개인 | 사용자·저장 데이터 확보 | 현재 범위 제외 |
| E10 | 취향이 비슷한 리뷰어 추천 | 고도화 | 미착수 | 개인 | 추천 검증 데이터 확보 | 현재 범위 제외 |
| E11 | 일반 리뷰어 → 신규 핵심 리뷰어 성장 구조 | 고도화 | 미착수 | 개인 | 성장 정책·데이터 확보 | 현재 범위 제외 |
| E12 | Admin과 Consumer 데이터를 연결한 양면 서비스 | 고도화 | 미착수 | 개인 | Consumer MVP 이후 | 현재 범위 제외 |

## 8. F — 기능 유지·축소 결정

| ID | 기능 | 결정 | 현재 상태 | 담당 | 완료 조건 | 대상 PR |
|---|---|---|---|---|---|---|
| F01 | Trust Center 전체 | 유지하되 축소 | 구현됨 | 이홍규 | 핵심 모델 신뢰 근거는 유지하고 B16 범위 밖 개편은 하지 않음 | B16 범위에서만 |
| F02 | Trust Capacity Slider | 안 해도 됨 | 미구현 | — | 구현하지 않고 고정 Top 20% 정책 설명 | 현재 범위 제외 |
| F03 | Target List CSV Export | 안 해도 됨 | 미구현 | — | 현재 요구사항에서 제외 상태 명시 | 현재 범위 제외 |
| F04 | Target List Delete UI | 고도화 | 미구현 | 개인 | 별도 승인 필요 | 현재 범위 제외 |
| F05 | Sponsorship Management | 안 해도 됨·노출 축소 후보 | 구현됨 | 개인 고도화 | 별도 승인 없이 기능을 추가·삭제하지 않음 | 현재 범위 제외 |
| F06 | 복잡한 관리자 설정 | 유지 최소화 | 구현됨 | 김동섭 우선 | Auth·Role 핵심을 유지하고 A 영역 밖 개편은 하지 않음 | A 영역 범위에서만 |
| F07 | Reviewer 360 | 필수 유지 | 구현됨 | 이홍규 | 핵심 검토 흐름 유지·회귀 PASS | `feat/core-product-ux` |
| F08 | Regional Analysis | 필수 유지 | 구현됨 | 이홍규 | 지역 공급 축 유지·회귀 PASS | `feat/core-product-ux` |
| F09 | New Reviewer Analysis | 필수 유지 | 구현됨 | 이홍규 | 신규 유입 축 유지·회귀 PASS | `feat/core-product-ux` |
| F10 | Playbook | 필수 유지 | 구현됨 | 이홍규 | 분석→행동 흐름 유지·회귀 PASS | `feat/core-product-ux` |
| F11 | Operations History | 필수 유지 | 구현됨 | 김동섭 우선 | A07 및 핵심 이력 회귀 PASS | `fix/a-app-resilience` |
| F12 | 실제 이메일·문자 발송 | 안 해도 됨 | 미구현 | — | 구현하지 않음 | 현재 범위 제외 |

## 9. G — CI·테스트·코드 품질

| ID | 작업 | 분류 | 현재 상태 | 담당 | 완료 조건 | 대상 PR |
|---|---|---|---|---|---|---|
| G01 | PR / main CI 생성 | 필수 | 미구현 | 이홍규 | PR 차단 CI가 test·lint·build를 실패 허용 없이 실행 | `chore/final-ci` |
| G02 | Python 테스트 CI 연결 | 필수 | 범위 설계 필요 | 이홍규 | Artifact-free 검사는 PR CI, 전체 검사는 Release Regression으로 분리 | `chore/final-ci` |
| G03 | React unit / component test 도입 | 고도화 | 미구현 | 개인·팀 | 별도 승인 필요 | 현재 범위 제외 |
| G04 | 핵심 E2E 테스트 | 필수 | 미구현 | 공동 QA | Login→Home→Reviewer→Save 핵심 흐름 증거 | `test/final-regression` |
| G05 | npm audit 재확인 | 필수 | 재검증 필요 | 이홍규 | 현재 lockfile 기준 결과와 처리 판단 기록 | `chore/final-ci` |
| G06 | React ErrorBoundary | 필수 | 미구현 | 김동섭 | 런타임 오류가 전체 앱을 무응답으로 만들지 않음 | `fix/a-app-resilience` |
| G07 | 거대한 React Page 전면 리팩터링 | 고도화 | 미착수 | 개인 | 별도 승인 필요 | 현재 범위 제외 |
| G08 | dead / legacy code 제거 | 고도화 | 후보만 존재 | 개인 | 사용 여부 검증 후 별도 승인 | 현재 범위 제외 |
| G09 | 구조화 Logging | 고도화 | 미착수 | 개인 | 실서비스 운영 필요 발생 | 현재 범위 제외 |
| G10 | 완전한 Observability | 안 해도 됨 | 미착수 | — | 수행하지 않음 | 현재 범위 제외 |
| G11 | Kubernetes 등 추가 인프라 | 안 해도 됨 | 미착수 | — | 수행하지 않음 | 현재 범위 제외 |

PR 차단 CI는 GitHub 기본 환경에서 준비 가능한 검사만 실행한다. DB·모델 artifact와
실제 AWS 환경이 필요한 전체 검증은 실패 허용으로 숨기지 않고 Release Regression에서
별도 실행한다.

## 10. H — README·문서·포트폴리오

| ID | 작업 | 분류 | 현재 상태 | 담당 | 완료 조건 | 대상 PR |
|---|---|---|---|---|---|---|
| H01 | README 프로젝트 정의 수정 | 필수 | 보완 필요 | 이홍규 | 관리자용 리뷰 공급 운영 서비스 정의 반영 | `docs/final-product-story` |
| H02 | 리뷰 공급 관리 3축 그림·설명 | 필수 | 부분 반영 | 이홍규 | 세 축과 연결 흐름을 한눈에 확인 | `docs/final-product-story` |
| H03 | 관리자용 서비스임을 명확히 | 필수 | 부분 반영 | 이홍규 | Consumer 서비스와 혼동되지 않음 | `docs/final-product-story` |
| H04 | 강사 Consumer 확장 피드백 기록 | 필수 | 미반영 | 이홍규 | 구현 기능이 아닌 향후 방향으로 기록 | `docs/final-product-story` |
| H05 | 모델 선택 과정 명확화 | 필수 | 보완 필요 | 이홍규·모델 담당 확인 | OOF 기반 선택 근거가 명확함 | `docs/final-product-story` |
| H06 | Test / Holdout 용어 정리 | 필수 | 보완 필요 | 이홍규·모델 담당 확인 | C02·C03 기준과 문서 표현 일치 | `docs/final-product-story` |
| H07 | 실제 한계 공개 | 필수 | 부분 반영 | 이홍규 | 데이터·모델·운영 한계 명시 | `docs/final-product-story` |
| H08 | 행동 효과 미검증 명시 | 필수 | 부분 반영 | 이홍규 | 효과·ROI를 확정 수치로 표현하지 않음 | `docs/final-product-story` |
| H09 | 실행 가이드 최종 확인 | 필수 | 재검증 필요 | 공동 | 문서 명령으로 실제 실행 가능 | `docs/final-product-story` |
| H10 | DB / Model 버전 문서 정합성 | 필수 | 보완 필요 | 이홍규·모델 담당 확인 | C06의 버전 역할 구분 적용 | `docs/final-product-story` |
| H11 | 서비스 Architecture 최신화 | 필수 | 부분 반영 | 이홍규 | React→FastAPI/Auth→MySQL 현재 구조 일치 | `docs/final-product-story` |
| H12 | 상세 기술문서 전체 재작성 | 안 해도 됨 | 미착수 | — | 수행하지 않음 | 현재 범위 제외 |
| H13 | 발표 후 개선 사항 문서 | 필수 | 미작성 | 이홍규 | 문제·변경·검증 근거 기록 | `docs/final-product-story` |
| H14 | 개인 고도화와 팀 결과물 구분 | 필수 | 미작성 | 이홍규 | Team Final Release와 후속 개인 기여 구분 | `docs/final-product-story` |

## 11. I — 최종 배포·Release

| ID | 작업 | 분류 | 현재 상태 | 담당 | 완료 조건 | 대상 PR |
|---|---|---|---|---|---|---|
| I01 | 실제 배포 화면 최종 Smoke Test | 필수 | 재실행 필요 | 공동 | 최종 커밋 배포본 핵심 역할·경로 PASS | `test/final-regression` |
| I02 | 현재 배포 Commit ID 확인 | 필수 | 미구현 | 김동섭·공동 | 배포본에서 정확한 SHA 확인 | `test/final-regression` |
| I03 | Model Version 확인 | 필수 | 부분 구현 | 공동 | 화면 또는 API에서 `v05_05_dl` 확인 | `test/final-regression` |
| I04 | Build date / version 제공 | 고도화 | 미구현 | 개인 | 별도 승인 필요 | 현재 범위 제외 |
| I05 | Final Regression Report | 필수 | 미작성 | 공동 | 필수 항목 결과와 증거 기록 | `test/final-regression` |
| I06 | 기존 FAIL 결과 갱신 | 필수 | 미실행 | 공동 | 이전 결과를 덮지 않고 최신 판정 추가 | `test/final-regression` |
| I07 | Production Approval HOLD 해제 기준 정의 | 필수 | 기존 기준 보완 필요 | 전원 | 필수 게이트와 판정 책임 확정 | `test/final-regression` |
| I08 | 기준 충족 시 HOLD → PASS 변경 | 필수 | HOLD | 전원 | 모든 필수 게이트 증거 충족 시에만 변경 | Final Release PR |
| I09 | Final Git Tag | 필수 | 미생성 | 공동 | 승인된 main 커밋에 태그 | Final Release 이후 |
| I10 | GitHub Release 작성 | 필수 | 미작성 | 이홍규·공동 | 태그·변경·한계·검증 결과 게시 | Final Release 이후 |
| I11 | Demo 영상 재촬영 | 조건부 필수 | 판단 필요 | 이홍규 | 기존 영상에서 최종 오류가 크게 보일 때만 수행 | 별도 승인 |
| I12 | 새로운 발표 PPT 제작 | 안 해도 됨 | 미착수 | — | 수행하지 않음 | 현재 범위 제외 |

## 12. 공용 파일 소유권

| 영역 | 선행 소유 PR | 후행 규칙 |
|---|---|---|
| `app/src/App.jsx`, `app/src/context/**` | `fix/a-app-resilience` | 머지 후 제품 UX 수정 가능 |
| `app/src/services/decisionService.js` | `fix/a-app-resilience` | A06·A07·A09 완료 전 병렬 수정 금지 |
| `app/src/components/common/Error*` | `fix/a-app-resilience` | 장애 처리 공통 계약 우선 |
| 그 외 `app/src/services/**`, `components/common/**`, `components/layout/**` | PR별 선점 | PR 설명에 파일을 적고 동시 수정 금지 |
| `HomePage`, Reviewer, Playbook 관련 파일 | `feat/core-product-ux` | A-App 머지 후 시작 |
| `app/src/App.css`, `app/src/index.css` | `feat/core-product-ux` | A-App은 컴포넌트 로컬 스타일 우선 |
| `app/package.json`, lockfile | `chore/final-ci` | CI PR 머지 전 다른 PR 수정 금지 |
| 기존 공용 테스트 | 먼저 시작한 단일 PR | 같은 파일 병렬 수정 금지 |
| 신규 기능별 테스트 | 해당 기능 PR | 가능하면 새 테스트 파일 사용 |

공용 파일 변경이 불가피하면 후행 브랜치는 선행 PR 머지 후 최신
`release/finalization`을 반영한 다음 작업한다.
