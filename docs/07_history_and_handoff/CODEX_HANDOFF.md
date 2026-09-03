# Codex Project Handoff

> **문서 상태: 현재 기준**
> 최종 갱신: 2026-09-03
> 제품 방향은 [DEC-012](../06_decisions/DEC-012_review_supply_recovery_operating_flow.md),
> 운영 컨텍스트는 [DEC-014](../06_decisions/DEC-014_unified_operating_context.md),
> Finalization 범위는 [DEC-015](../06_decisions/DEC-015_finalization_scope_and_ownership.md),
> 화면 명세는 [V05_FINAL_PRODUCT_UX_SPEC](../05_ui_ux/V05_FINAL_PRODUCT_UX_SPEC.md)를
> 따른다.

## 1. 프로젝트 정의

Yelp 음식 리뷰 공급을 지역 공급 변화, 기존 핵심 리뷰어, 신규 핵심 리뷰어 유입의
세 축으로 관찰하고 관리자 판단과 개인·지역 운영안으로 연결하는 운영 서비스다.

```text
지역별 리뷰 공급 변화 및 이상 탐지
→ 기존 핵심 리뷰어의 활동 약화·중단 예측과 우선 검토
→ 신규 핵심 리뷰어 유입 변화 관찰과 우선 검토 대상 연결
→ 개인 특별 관리 또는 지역 활성화 운영안
→ 판단·대상·접촉·재검토 이력 관리
```

최신 사용자 화면과 제품 문서에서는 `핵심 리뷰어`를 사용한다. 과거 DEC 제목,
코드 변수와 데이터 컬럼의 `파워 리뷰어`·`power_reviewer`는 재현성과 이력 추적을
위해 유지할 수 있다. 핵심 리뷰어를 Yelp `Elite`와 동일시하지 않는다.

## 2. 현재 운영 구조

```text
React app/
  → FastAPI api/
  → MySQL yelp_data

React app/
  → FastAPI auth_service/
  → MySQL reviewer_retention_auth
```

- 현재 운영 화면은 `app/` React다.
- 분석·운영 API는 `api/`, 인증·사용자 관리는 `auth_service/`가 담당한다.
- 위험 유형·근거·전략·프로필 정규화의 공통 기준 구현은 `shared/retention/`이다.
- `app/src/data/*.json`은 API 정합성 확인·복구용 정적 산출물이며 런타임 자동 폴백이 아니다.
- 이전 Streamlit 앱은 `archive/app_streamlit_v04/`에 비교·롤백 기준으로 보존한다.
- 운영 컨텍스트 확장 DDL·파생·적재는 `v05/`에 분리돼 있다.

## 3. 데이터와 코호트

- 음식 관련 범위: Restaurants + DEC-007의 선별 미식 방문형 업체
- 업체: 58,156개
- 리뷰: 4,950,264건
- 핵심 리뷰어 선정 기준: 선정 연도 음식 관련 리뷰 10건 이상, 활동 월 3개월 이상
- 개발 코호트: 선정 연도 2010~2017, 31,420건
- 공통 OOF 평가: 선정 연도 2013~2017, 24,596건
- Final Test: 비교 2017 → 선정·피처 마감 2018 → 실제 상태 검증 2019
- Final Test 표본: 6,533명
- 현재 코호트 설정: `configs/analysis_config_v04.yaml`
- `configs/analysis_config.yaml`은 이전 v01 비교 설정

상태 라벨은 다음과 같다.

| 코드 | 상태 | 타깃 연도 조건 |
|---:|---|---|
| 0 | 핵심 리뷰어 지위 유지 | 리뷰 10건 이상 AND 활동 월 3개월 이상 |
| 1 | 리뷰 활동 약화 | 리뷰 1건 이상이며 리뷰 10건 미만 OR 활동 월 3개월 미만 |
| 2 | 리뷰 활동 중단 | 음식 관련 리뷰 0건 |

리뷰 활동 중단을 서비스 완전 이탈이나 실제 방문 중단으로 확대 해석하지 않는다.

## 4. 현재 최종 모델

현재 운영 모델은 `v05_05_dl` Lifecycle Fusion H2다.

```text
Core4 × 24개월 → GRU(hidden=64) ─────┐
                                      ├→ Risk head + conditional Stopped head
Lifecycle 5개 → MLP(hidden=16) ──────┘
```

| 지표 | 결과 |
|---|---:|
| OOF Macro F1 / Macro PR-AUC | 0.5763 / 0.5980 |
| OOF Precision@1000 | 90.60% |
| Final Test Macro F1 / Macro PR-AUC | 0.5731 / 0.5962 |
| Final Test Precision@1000 | 89.90% |
| Top 20% 대상 | 1,307명 |
| Top 20% Precision / Recall / Lift | 89.29% / 29.55% / 1.48배 |

`risk_score`와 클래스 점수는 보정된 확률이 아니라 상대적인 검토 순위를 정하는
모델 점수다. `v05_06_dl`은 개발 후보로 검증됐지만 현재 모델을 교체하지 않았다.

재현 경로와 버전 관계는 [pipeline/README](../../pipeline/README.md), 원본 결과 위치는
[reports/README](../../reports/README.md)를 따른다.

## 5. 현재 기능 범위

- 권역·도시별 리뷰 공급과 원인 탐색
- 핵심 리뷰어 우선 검토 큐와 URL 필터
- Reviewer 360 활동 변화·월별 활동·작성 간격·리뷰 활동 반경
- 모델 근거와 관리자 판단 분리
- 개인 추천 음식점과 지역 캠페인 후보
- 판단·메모·스누즈·접촉·감사 이력 서버 저장
- 대상 명단과 개인·지역 운영안 서버 저장
- 운영 이력·재검토 알림 화면
- 사용자 승인·거절·역할·권역·상태 관리
- Trust Center의 운영 모델·비교 모델·Top-K·시간 구조 표시

담당자 선택은 서버 필드가 준비돼 있으나 로그인 사용자 목록과의 선택 UI 연결이
완료되지 않았다.

## 6. 검증과 배포 상태

- 2026-08-05 관리자 UI QA: 총 135건
- PASS 95 / FAIL 17 / PARTIAL 6 / NOT RUN 17
- React lint·프로덕션 빌드와 주요 자동 검증은 수행됨
- 운영 서비스와 `v05_05_dl` 연결은 확인됨
- 2026-09-02 AWS 운영 환경에서 HTTPS·HTTP redirect·Secure Cookie를 확인함
- 같은 환경에서 미인증 Retention 조회 API의 401 응답을 확인함
- 최종 배포 승인은 **보류**

2026-09-02 기준 완료된 A 영역:

1. A01 Retention 조회 API 인증
2. A03 HTTPS와 HTTP→HTTPS redirect
3. A04 Secure Cookie

남은 필수 검증·미해결 항목:

1. A02 실제 VIEWER·OPERATOR·ADMIN 역할·권역 Smoke Test
2. A05 비허용 cross-origin CORS 검증
3. A06 Snooze 새로고침·재로그인 복원
4. A07 History 상세 React UI 연결·검증
5. A08~A10 React 부분 장애 대응
6. A11~A13 발표 오류·기존 FAIL·장애 시나리오 회귀
7. B10 큐에서 Reviewer 360 이동 시 지역·필터 문맥 유지
8. I02 실제 배포 commit 식별

결함 상태를 임의로 완료 처리하지 않는다. 최신 근거는
[QA 실행 결과](../qa/ADMIN_UI_QA_EXECUTION_2026-08-05.md)와
[A 영역 실행 결과](../qa/A_SECURITY_EXECUTION_2026-08-24.md),
[AWS HTTPS 재배포 보고서](../02_reports/04_aws_https_redeployment_report_2026-09-02.md)를
시간순으로 적용한다.

## 7. Finalization 범위

- 현재는 [DEC-015](../06_decisions/DEC-015_finalization_scope_and_ownership.md)의
  `필수` 항목만 수행한다.
- A 영역 앱 안정성·보안 후속 작업은 김동섭 담당 브랜치를 우선한다.
- 이홍규는 A-App 머지 후 B 영역 제품 UX, CI, 최종 제품 문서와 회귀 기록을 진행한다.
- C 영역은 모델 구조와 수치를 변경하지 않는다. 용어·버전 역할 문서 정합성만 모델
  담당 확인 후 별도 PR에서 보완한다.
- Consumer 구현, 실제 효과 측정, 재학습과 추가 모델 실험은 이번 범위가 아니다.
- 구체적인 순서는
  [FINALIZATION_EXECUTION_PLAN](FINALIZATION_EXECUTION_PLAN.md)을 따른다.

## 8. 변경 보호 원칙

- 모델·코호트·시간 분할·기존 성능 수치를 임의로 바꾸지 않는다.
- 미래 타깃 연도 정보를 입력 피처에 포함하지 않는다.
- 실제 데이터가 있으면 합성 데이터보다 우선한다.
- 구현되지 않은 기능을 작동하는 것처럼 표현하지 않는다.
- 권역·도시·반경을 거주지, 직장, 생활 반경 또는 실제 이동 경로로 표현하지 않는다.
- 운영 효과와 ROI는 실제 실행·성과 데이터 없이 수치로 만들지 않는다.

## 9. 문서 기준

1. [AGENTS.md](../../AGENTS.md)
2. [의사결정 기록](../06_decisions/) — Finalization은 DEC-015 우선
3. 이 문서
4. [프로젝트 요구사항](../01_business/project_requirements.md)
5. 기타 명세·보고서·역사 문서

문서 탐색은 [docs/README](../README.md)를 사용한다.
