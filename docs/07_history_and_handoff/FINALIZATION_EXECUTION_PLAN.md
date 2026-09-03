# Finalization 실행 계획

> **문서 상태: 현재 기준**
> 최종 갱신: 2026-09-03
> 범위·담당·완료 조건은 [DEC-015](../06_decisions/DEC-015_finalization_scope_and_ownership.md)를 따른다.

## 1. 목표

Team Final Release는 새 기능을 넓히는 작업이 아니라, 승인된 필수 항목을 통해 현재
관리자용 리뷰 공급 운영 서비스의 정확성·안정성·설명 가능성을 마무리하는 작업이다.

```text
공급 변화 감지
→ 원인과 핵심 리뷰어 확인
→ 개인 또는 지역 운영안 결정
→ 이력과 검증 결과 기록
```

## 2. 브랜치 계약

- 통합 브랜치: `release/finalization`
- 중간 PR base: `release/finalization`
- `main` 직접 commit·push 금지
- 모든 작업 브랜치는 생성 시점의 최신 `release/finalization`에서 시작
- 선행 PR이 머지되면 후행 브랜치는 작업 전에 최신 통합 브랜치를 반영
- `fix/a-app-resilience`에서 다른 작업 브랜치를 파생하지 않음

## 3. 실행 순서

| 순서 | 브랜치 / PR | 목적 | 선행 조건 |
|---:|---|---|---|
| 1 | `docs/finalization-contract` | DEC-015·현재 상태·실행 계약 확정 | 없음 |
| 2 | `chore/final-ci` | Artifact-free PR 차단 CI | 1 머지 |
| 3 | `fix/a-app-resilience` | A 영역 앱 안정성·권한·부분 장애 대응 | 1 반영, 공용 파일은 2와 충돌 금지 |
| 4 | `feat/core-product-ux` | B 영역 3축·업무 흐름·온보딩 정리 | 3 머지 |
| 5 | `docs/final-product-story` | README·모델 용어·한계·기여 구분 | 2~4 결과 확정 |
| 6 | `test/final-regression` | 기능 수정 없이 최종 검증과 판정 기록 | 2~5 머지 |
| 7 | `fix/regression-*` | 회귀에서 발견한 결함만 수정 | 6의 결함별 별도 PR |
| 8 | `release/finalization` → `main` | Final Release | 필수 게이트 충족·전원 승인 |

계약 PR 이전에 만들어진 브랜치는 계약 PR 머지 후 최신
`release/finalization`을 merge 또는 rebase하고 충돌을 확인한다.

## 4. PR별 완료 조건

### 4.1 문서 계약

- DEC-015에 A01~I12의 분류·상태·담당·근거·완료 조건·대상 PR이 있음
- Handoff와 요구사항이 2026-09-02 AWS 결과와 모순되지 않음
- 현재 UI가 React이며 archive Streamlit은 수정 금지임을 명시
- Markdown 재검토와 `git diff --check` 통과

### 4.2 PR 차단 CI

GitHub 기본 환경에서 준비 가능한 검사만 실패 허용 없이 실행한다.

- Python compile
- API/Auth의 독립 실행 가능한 자동 테스트
- 외부 artifact가 필요 없는 계약 테스트
- React `npm ci`, lint, production build
- CI는 배포하지 않음

전체 Python suite, 실제 MySQL, 모델·데이터 artifact, 브라우저 E2E와 AWS smoke는
Release Regression으로 분리한다. 실행하지 못한 검사를 `continue-on-error`로 통과한
것처럼 표시하지 않는다.

### 4.3 A-App

- A02·A05·A06~A10 완료 조건 충족
- 공용 App·Context·Error 영역 변경에 대응하는 검증 수행
- A01·A03·A04의 기존 완료 결과를 훼손하지 않음
- 변경한 장애 시나리오의 재현 전·후 증거 기록

### 4.4 제품 UX

- B 필수 항목만 구현
- `공급 변화 / 핵심 리뷰어 / 신규 유입` 세 축 유지
- `지역 → 원인 → 사람 → 행동` 문맥 연결
- 실제 데이터에 없는 수치·효과·사용자 상태를 만들지 않음
- A-App 머지 결과를 기준으로 lint·build·브라우저 검증

### 4.5 최종 제품 설명

- 관리자용 서비스와 Consumer 고도화 방향을 구분
- OOF와 Final Test를 섞지 않음
- `risk_score`를 확률로 표현하지 않음
- 코호트·모델·DB 버전의 역할을 구분
- 실제 개입 효과·ROI·재학습 미구현을 명시

### 4.6 최종 회귀

- 이 PR에서 기능을 수정하지 않음
- 기존 FAIL 17건과 핵심 NOT RUN·장애 시나리오를 최신 배포본에서 판정
- 역할별 Smoke Test, CORS, Snooze·History 복원, 부분 장애 대응 확인
- 배포 commit·모델 버전과 실행 환경 기록
- 버그는 항목별 `fix/regression-*` PR로 분리

## 5. 수정 금지와 중단 조건

다음 상황에서는 작업을 중단하고 사용자 또는 담당자 확인을 받는다.

- DEC-015의 분류나 담당을 바꿔야 하는 경우
- 모델·코호트·시간 분할·성능 수치·산출물 변경이 필요한 경우
- 실제 데이터가 없는 결과 또는 효과 수치를 요구하는 경우
- 현재 PR이 소유하지 않은 공용 파일 수정이 필요한 경우
- 선행 PR과 같은 파일에 충돌하는 변경이 필요한 경우
- 과거 QA·배포 결과서를 덮어써야 하는 경우

현재 Finalization에서 수정하지 않는 영역:

```text
archive/app_streamlit_v04/**
archive/app_streamlit_v01_prototype/**
Consumer 구현
실제 효과 측정
자동 재학습
추가 모델 실험
```

## 6. 검증과 보고 형식

각 PR은 다음을 남긴다.

1. 변경 파일
2. 해결한 DEC-015 ID
3. 주요 변경 내용
4. 실행한 검증과 결과
5. 미실행 검증과 이유
6. 발견한 충돌·잔여 위험
7. 다음 PR이 반영해야 할 사항

## 7. Final Release 게이트

다음 조건을 모두 충족하기 전에는 `release/finalization`을 `main`에 머지하거나
Production Approval을 PASS로 변경하지 않는다.

- DEC-015 필수 항목에 완료 근거가 있음
- P0 결함 0건
- 역할·권역·인증·HTTPS·Secure Cookie 검증 통과
- Snooze·History와 핵심 저장·복원 검증 통과
- 부분 장애 시 핵심 업무 유지 확인
- PR 차단 CI 통과
- Release Regression 완료
- 정확한 배포 commit과 모델 버전 확인
- 전원 승인

승인 후 순서는 `main` 머지 → AWS 재배포 → 최종 Smoke Test → Git tag → GitHub
Release다.
