# 프로젝트 문서 안내

> **문서 상태: 현재 기준**
> 이 문서는 `docs/`의 탐색 순서와 문서 상태를 안내하는 색인이다.

## 문서 상태

| 상태 | 의미 |
|---|---|
| 현재 기준 | 현재 제품·데이터·모델·운영 판단에 적용 |
| 비교·롤백 기준 | 이전 구현의 재현, 정합성 검증, 롤백에 사용 |
| 역사 기록 | 당시 작업·회의·문제 해결 과정을 보존 |
| 후속 결정으로 대체됨 | 현재 판단에는 후속 의사결정이나 최신 문서를 적용 |
| 호환 안내 | 이전 링크를 최신 기준 문서로 연결 |

## 먼저 읽을 문서

1. [프로젝트 README](../README.md)
2. [프로젝트 요구사항](01_business/project_requirements.md)
3. [현재 인수인계](07_history_and_handoff/CODEX_HANDOFF.md)
4. [의사결정 기록](06_decisions/)
5. [관리자 UI QA 결과](qa/ADMIN_UI_QA_EXECUTION_2026-08-05.md)

## 폴더 안내

| 경로 | 내용 | 기준 문서 |
|---|---|---|
| `01_business/` | 비즈니스 시나리오, 요구사항, WBS | [요구사항](01_business/project_requirements.md) |
| `02_reports/` | 데이터 전처리·모델 학습·배포 결과서 | [모델 학습 결과서](02_reports/02_model_training_report.md) |
| `03_data_and_models/` | 데이터·피처 검증 상세 | [데이터 검증](03_data_and_models/data_validation_report.md) |
| `04_architecture_and_guides/` | 로컬 실행, 배포, 이전 데이터 계약 | [로컬 실행](04_architecture_and_guides/LOCAL_RUN_GUIDE.md) |
| `05_ui_ux/` | React·Streamlit UI 명세와 구현 이력 | [최종 UX 명세](05_ui_ux/V05_FINAL_PRODUCT_UX_SPEC.md) |
| `06_decisions/` | 승인 결정과 대체 관계 | [DEC-014](06_decisions/DEC-014_unified_operating_context.md) |
| `07_history_and_handoff/` | 현재 인수인계와 역사 기록 | [현재 인수인계](07_history_and_handoff/CODEX_HANDOFF.md) |
| `08_future_roadmap/` | 데이터·모델·서비스 고도화 방향 | [서비스 제품화 로드맵](08_future_roadmap/06_service_productization_and_application.md) |
| `qa/` | 테스트 계획·케이스·실행 결과 | [QA 안내](qa/README.md) |
| `assets/` | README와 문서용 시각 자료 | `assets/readme/` |

## 용어

- 최신 사용자 화면과 제품 문서에서는 `핵심 리뷰어`를 사용한다.
- 핵심 리뷰어는 Yelp `Elite`와 같은 뜻이 아니며, 승인된 리뷰 수·활동 월 기준으로
  정의한 분석 코호트다.
- 과거 결정 제목·파일명, 코드 변수, 데이터 컬럼의 `파워 리뷰어` 또는
  `power_reviewer`는 재현성과 이력 추적을 위해 유지할 수 있다.

## 저장소 밖 결과와 실험 기록

- 파이프라인 버전 관계: [pipeline/README.md](../pipeline/README.md)
- 모델·실험 결과 색인: [reports/README.md](../reports/README.md)
- DB 계약과 적재: [database/README.md](../database/README.md)
