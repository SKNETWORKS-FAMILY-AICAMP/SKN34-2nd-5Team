<div align="center">

# Yelp Reviewer Retention Ops

### 핵심 리뷰어의 활동 위험을 탐지하고, 운영자의 판단과 다음 행동까지 연결하는 리텐션 운영 서비스

Yelp 음식 리뷰 활동을 바탕으로 다음 연도의 **음식 리뷰 활동 유지·약화·중단**을 예측하고,<br>
권역 탐색부터 대상 선정, Reviewer 360 검토, 운영안 저장과 재검토 기록까지 하나의 운영 흐름으로 제공합니다.

<br>

![Model](https://img.shields.io/badge/Model-v05__05__dl-075C45?style=for-the-badge)
![Final Test](https://img.shields.io/badge/Final_Test-6%2C533명-075C45?style=for-the-badge)
![Technical Deployment](https://img.shields.io/badge/Technical_Deployment-COMPLETE-075C45?style=for-the-badge)
![Production Approval](https://img.shields.io/badge/Production_Approval-HOLD-E1513A?style=for-the-badge)

</div>

---

## 빠르게 보기

| 대상 | 추천 탐색 경로 |
|---|---|
| 발표·평가자 | [프로젝트 개요](#프로젝트-개요) → [핵심 결과](#핵심-결과) → [모델](#모델) → [화면 구성](#화면-구성) → [검증·배포 상태](#현재-검증배포-상태) |
| 개발자 | [프로젝트 구조](#프로젝트-구조) → [실행 가이드](#실행-가이드) → [모델 재생성](#모델-재생성) → [트러블슈팅](#트러블슈팅) |
| 운영·QA 담당자 | [요구사항](#요구사항-명세서-미리보기) → [업무 흐름](#업무-흐름) → [검증·배포 상태](#현재-검증배포-상태) → [범위와 한계](#범위와-한계) |

---

## 목차
0. [시연 영상](#시연-영상)
1. [팀 소개](#팀-소개)
2. [프로젝트 개요](#프로젝트-개요)
3. [기술 스택](#기술-스택)
4. [WBS & 개발 일정](#wbs--개발-일정)
5. [요구사항 명세서 미리보기](#요구사항-명세서-미리보기)
6. [프로젝트 구조](#프로젝트-구조)
7. [ERD](#erd)
8. [데이터 흐름 및 전처리](#데이터-흐름-및-전처리)
9. [모델](#모델)
10. [화면 구성](#화면-구성)
11. [업무 흐름](#업무-흐름)
12. [실행 가이드](#실행-가이드)
13. [모델 재현 파이프라인 실행 가이드](#모델-재현-파이프라인-실행-가이드)
14. [현재 검증·배포 상태](#현재-검증배포-상태)
15. [트러블슈팅](#트러블슈팅)
16. [향후 개선 방향](#향후-개선-방향)
17. [문서](#문서)
18. [범위와 한계](#범위와-한계)
19. [회고](#회고)

    
<br>

## 🎥 시연 영상

프로젝트의 전체 기능은 아래 시연 영상을 통해 확인하실 수 있습니다.

📺 **YouTube**
> https://www.youtube.com/watch?v=IwLZAr0SUvQ

<br>

---

<div align="center">

## 팀 소개

<table align="center" style="border: none; border-collapse: collapse;">
  <tr>
    <td align="center" valign="top" style="padding: 5px;">
      <!-- 김동섭 (ChatGPT) -->
      <table border="1" cellpadding="8" style="border-collapse: collapse; width: 220px;">
        <tr><td align="center" height="90"><img src="docs/assets/readme/introduce_dongseop.png" alt="김동섭" width="70"></td></tr>
        <tr><td align="center"><strong>김동섭</strong></td></tr>
        <tr><td align="center"><a href="https://github.com/20220348-kim"><img src="https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a></td></tr>
        <tr><td align="center"><small>Streamlit→React 전환<br>v05 DL 실험·Final Test<br>테스트시나리오 생성 및 QA</small></td></tr>
      </table>
    </td>
    <td align="center" valign="middle" style="padding: 0 10px;"><b>────</b></td>
    <td align="center" valign="top" style="padding: 5px;">
      <!-- 이홍규 팀장 (뇌) -->
      <table border="1" cellpadding="8" style="border-collapse: collapse; width: 220px;">
        <tr><td align="center" height="90"><img src="docs/assets/readme/introduce_honggyu.png" alt="이홍규 (팀장)" width="70"></td></tr>
        <tr><td align="center"><strong>이홍규 (팀장)</strong></td></tr>
        <tr><td align="center"><a href="https://github.com/4hglee-ops"><img src="https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a></td></tr>
        <tr><td align="center"><small>v04 프로토타입 설계·구현<br>공통 데이터 규격·서비스 통합<br>운영 UI·UX 및 제품 문서 체계화</small></td></tr>
      </table>
    </td>
    <td align="center" valign="middle" style="padding: 0 10px;"><b>────</b></td>
    <td align="center" valign="top" style="padding: 5px;">
      <!-- 김기호 (Gemini) -->
      <table border="1" cellpadding="8" style="border-collapse: collapse; width: 220px;">
        <tr><td align="center" height="90"><img src="docs/assets/readme/introduce_kiho.png" alt="김기호" width="70"></td></tr>
        <tr><td align="center"><strong>김기호</strong></td></tr>
        <tr><td align="center"><a href="https://github.com/kyo-135"><img src="https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a></td></tr>
        <tr><td align="center"><small>ML 피처 엔지니어링<br>데이터 전처리, 모델 학습 및 검증<br>데이터 전처리/모델 학습 결과서 작성</small></td></tr>
      </table>
    </td>
  </tr>
  <tr>
    <td colspan="2"></td>
    <td align="center" valign="middle"><b>│<br>│</b></td>
    <td colspan="2"></td>
  </tr>
  <tr>
    <td colspan="2"></td>
    <td align="center" valign="top" style="padding: 5px;">
      <!-- 최인영 (Claude) -->
      <table border="1" cellpadding="8" style="border-collapse: collapse; width: 220px;">
        <tr><td align="center" height="90"><img src="docs/assets/readme/introduce_inyoung.png" alt="최인영" width="70"></td></tr>
        <tr><td align="center"><strong>최인영</strong></td></tr>
        <tr><td align="center"><a href="https://github.com/inyoung9629"><img src="https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a></td></tr>
        <tr><td align="center"><small>AWS Lightsail MySQL 구축<br> 및 데이터 적재, 배포<br> 인프라 설계, 발표</small></td></tr>
      </table>
    </td>
    <td colspan="2"></td>
  </tr>
</table>

</div>

---

## 프로젝트 개요

핵심 리뷰어는 음식 콘텐츠 공급과 커뮤니티 활성화에 중요한 사용자입니다. 하지만 활동 감소를 사후에 발견하면 운영자가 적절한 시점에 대응하기 어렵습니다.

이 프로젝트는 Yelp 콘텐츠·커뮤니티 운영자와 리뷰어 CRM 담당자를 위한 관리자용 운영 제품으로, 다음 질문에 답하는 것을 목표로 합니다.

> 어느 지역의 리뷰 공급이 약해졌고, 누구를 먼저 검토하며, 어떤 근거로 무엇을 실행할 것인가?

| 운영 문제 | 프로젝트의 접근 |
|---|---|
| 활동 약화와 중단을 사후에 발견 | 시점 안전 피처로 다음 연도 유지·약화·중단 예측 |
| 검토 순서를 일관되게 정하기 어려움 | `risk_score` 기반 상대적 위험 순위와 상위 20% 검토 범위 제공 |
| 모델 결과만으로 이유를 설명하기 어려움 | Reviewer 360에서 활동량·작성 주기·탐색·반경 근거 제공 |
| 분석 결과와 운영 행동이 분리됨 | 관리자 판단, 대상 명단, 개인·권역 운영안과 재검토 기록을 서버에 저장 |

> `risk_score`는 보정된 이탈 확률이 아니라 **상대적인 위험 순위를 정하기 위한 모델 점수**입니다. 모델은 운영자의 결정을 대신하지 않습니다.

### 리뷰 공급 관리의 세 축

| 축 | 확인하는 질문 | 다음 단계 |
|---|---|---|
| 공급 변화 | 어느 권역·도시의 음식 리뷰 공급이 줄었나? | 우선 확인할 지역 선택 |
| 핵심 리뷰어 | 어떤 리뷰어의 활동이 약화·중단될 위험이 큰가? | Reviewer 360에서 근거 검토 |
| 신규 유입 | 신규 핵심 리뷰어 유입이 공급 감소를 보완하는가? | 우선 검토 대상과 지역 운영안 연결 |

세 축은 독립 지표가 아니라 `지역 → 원인 → 사람 → 행동` 순서로 연결됩니다. 일반 사용자를 위한 맛집·리뷰어 탐색 Consumer 서비스는 구현 기능이 아니며, 별도 검증과 승인이 필요한 향후 확장 방향입니다.

**Primary CRM 선정 흐름:** 세 개 seed에서 산출한 약화·중단 위험 점수를 평균해 `risk_score`를 생성합니다. Final Test 6,533명을 이 점수의 내림차순으로 정렬하고, 상위 20%인 1,307명을 Primary CRM 검토 대상으로 지정합니다.

### 핵심 결과

| 항목 | 결과 |
|---|---:|
| 최종 모델 | `v05_05_dl` Lifecycle Fusion H2 |
| 개발 코호트 | 선정 연도 2010~2017, 31,420건 |
| OOF 검증 | Expanding-Time 5-Fold × 3 seeds, 24,596건 |
| Final Test | 2018년 선정 코호트 6,533명 |
| OOF Macro F1 / Macro PR-AUC | **0.5763 / 0.5980** |
| OOF Precision@1000 | **90.60%** |
| Final Test Macro F1 / Macro PR-AUC | **0.5731 / 0.5962** |
| Final Test Precision@1000 | **89.90%** |
| Primary CRM 검토 범위 | 위험 순위 상위 20%, 1,307명 |
| Top 20% Precision / Lift | **89.29% / 1.48배** |
| 운영 서비스 | React → FastAPI → MySQL |

---

## 기술 스택

### Frontend

| 분류 | 기술 |
|---|---|
| 프레임워크 | ![React](https://img.shields.io/badge/React_19-61DAFB?style=flat-square&logo=react&logoColor=black) ![Vite](https://img.shields.io/badge/Vite_8-646CFF?style=flat-square&logo=vite&logoColor=white) |
| 스타일·시각화 | ![Tailwind](https://img.shields.io/badge/Tailwind_CSS_4-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white) `Recharts` `Leaflet` |

### Backend / Database

| 분류 | 기술 |
|---|---|
| API·인증 | ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white) `SQLAlchemy` `PyMySQL` `Argon2` |
| 데이터베이스 | ![MySQL](https://img.shields.io/badge/MySQL-2_Databases-4479A1?style=flat-square&logo=mysql&logoColor=white) `yelp_data` `reviewer_retention_auth` |
| 공통 도메인 로직 | `shared/retention/` |

### Data / ML·DL

| 분류 | 기술 |
|---|---|
| 데이터 처리 | ![Python](https://img.shields.io/badge/Python_3.12-3776AB?style=flat-square&logo=python&logoColor=white) `Pandas` `NumPy` `PyArrow` `DuckDB` |
| ML | `scikit-learn` `XGBoost` `LightGBM` |
| DL | ![PyTorch](https://img.shields.io/badge/PyTorch-v05__05__dl-EE4C2C?style=flat-square&logo=pytorch&logoColor=white) |

### Test / Collaboration

| 분류 | 기술·도구 |
|---|---|
| 정적·자동 검증 | `Pytest` `unittest` `ESLint` `Vite build` |
| 사용자 QA | 관리자 UI 135개 시나리오 |
| 협업 | ![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=github&logoColor=white) `Git` `Notion` `VS Code` `DBeaver` |

---

## WBS & 개발 일정

README의 WBS는 작업 수행과 최종 검증·승인을 분리해 표시합니다. 세부 담당자와 작업 간 의존 관계는 [전체 WBS](docs/01_business/WBS.md)를 기준으로 합니다.

| 단계 | 7/22~24 | 7/24~27 | 7/27~30 | 7/31~8/3 | 8/4~5 | 수행 상태 | 검증·승인 상태 |
|---|:---:|:---:|:---:|:---:|:---:|---|---|
| 기획·요구사항 | 🟩 | 🟩 |  |  | 🟩 | 완료 | 완료 |
| 데이터·전처리·DB | 🟩 | 🟩 | 🟩 | 🟩 | 🟩 | 완료 | 결과서 최종 검토 |
| 모델 개발·평가 |  | 🟩 | 🟩 | 🟩 | 🟩 | 완료 | 산출물 보관 정책 확인 필요 |
| React·API·DB 통합 |  | 🟩 | 🟩 | 🟩 | 🟩 | 완료 | 핵심 연결 확인 |
| 운영 기능 구현 |  |  | 🟩 | 🟩 | 🟩 | 완료 | 일부 QA 미통과 |
| 최종 문서화 |  |  |  |  | 🟩 | 완료 | README·필수 문서 반영 완료 |
| 배포·회귀 QA |  |  |  | 🟩 | 🟩 | 서비스 배포 | **최종 승인 보류** |

**범례:** 🟩 해당 기간 수행 · 빈칸 수행 기간 아님

> 핵심 개발과 서비스 연동은 완료됐지만 기능·보안 QA 미통과 항목이 남아 있어, 구현 완료와 배포 승인을 동일하게 표시하지 않습니다.

---

## 요구사항 명세서 미리보기

| ID | 핵심 요구사항 | 현재 상태 | 확인 근거 |
|---|---|---|---|
| BR-01 | 권역·도시별 리뷰 공급 변화 탐지 | 완료 | 지역 API·운영 홈 |
| BR-02 | 유지·약화·중단 3클래스 예측 | 완료 | `v05_05_dl` |
| BR-03 | 위험 순위 기반 CRM 우선 대상 선정 | 완료 | 상위 20% 1,307명 |
| BR-04 | Reviewer 360 활동 근거 제공 | 완료 | 관련 QA PASS |
| BR-05 | 관리자 판단·메모·접촉 저장 | 부분 완료 | 기본 저장 PASS, 스누즈 복원 FAIL |
| BR-06 | 개인·권역 운영안 설계·저장 | 부분 완료 | 저장 PASS, CSV·삭제 등 미충족 |
| BR-07 | 운영 결과·감사·알림 이력 추적 | 부분 완료 | 주요 이력 PASS, 일부 미실행 |

데이터·모델·기능·보안·비기능 요구사항과 수락 기준은 [프로젝트 요구사항 명세서](docs/01_business/project_requirements.md)에서 확인할 수 있습니다.

---

## 프로젝트 구조

### 핵심 실행 경로

| 구분 | 핵심 경로 | 역할 |
|---|---|---|
| 운영 데이터 | `app/` → `api/` → MySQL `yelp_data` | React 화면에서 예측·권역·운영 기록 조회 및 저장 |
| 인증·승인 | `app/` → `auth_service/` → MySQL `reviewer_retention_auth` | 로그인, 세션, 사용자 승인과 권한 관리 |
| 공통 판단 로직 | `shared/retention/` → `api/`·이전 앱·export | 위험 유형, 판단 근거, 운영안과 응답 정규화의 기준 구현 |
| 모델 재생성 | `pipeline/` → `models/`·`reports/` → DB/API | 피처 생성, 학습, 평가 및 운영 산출물 갱신 |
| 프로젝트 문서 | `docs/` | 요구사항, WBS, 결과서, QA, 의사결정과 실행 가이드 |

> 현재 React 서비스의 운영 데이터는 정적 JSON이 아니라 `app/` → `api/` → MySQL `yelp_data` 경로로 제공됩니다.

<details>
<summary><strong>전체 디렉터리 구조 보기</strong></summary>

```text
SKN34-2nd-5Team/
├─ app/                    # React 운영 서비스
├─ api/                    # 분석·운영 FastAPI
├─ auth_service/           # 로그인·회원가입·승인·세션 FastAPI
├─ shared/retention/       # 위험 근거·전략·정규화·직렬화 기준 구현
├─ pipeline/               # ML·DL 피처 생성, 학습, 평가
├─ database/               # MySQL DDL·적재·검증
├─ v05/                    # v05 운영 컨텍스트 파이프라인·DB 확장
├─ configs/                # 분석·코호트 설정
├─ data/                   # raw·interim·processed 데이터
├─ models/                 # 모델·메타데이터 로컬 산출물
├─ reports/                # 실험 결과·평가표
├─ docs/                   # 요구사항·WBS·결과서·가이드·QA
├─ tests/                  # 데이터·도메인·API 계약 테스트
└─ archive/                # 이전 Streamlit 프로토타입 보존
```

</details>

위험 유형·근거·전략 판단과 응답 정규화의 기준 구현은 `shared/retention/`입니다.

---

## ERD

분석·운영 DB인 `yelp_data`와 인증 DB인 `reviewer_retention_auth`를 분리해 구성했습니다.

### 데이터·모델 ERD

<p align="center">
  <img src="docs/assets/readme/04_erd_data_model.png" alt="yelp_data 데이터·모델 ERD" width="100%">
</p>

### 타깃 명단·운영 ERD

<p align="center">
  <img src="docs/assets/readme/05_erd_operations.png" alt="yelp_data 타깃 명단·운영 ERD" width="100%">
</p>

### 인증·승인 ERD

<p align="center">
  <img src="docs/assets/readme/06_erd_auth.png" alt="reviewer_retention_auth 인증·승인 ERD" width="100%">
</p>

---

## 데이터 흐름 및 전처리

### 전체 데이터 흐름

<p align="center">
  <img src="docs/assets/readme/01_data_flow.png" alt="Yelp Reviewer Retention Ops 데이터 흐름" width="100%">
</p>

Yelp 원천 데이터에서 음식 관련 범위를 확정하고, 시점 안전 피처와 검증·운영 산출물을 생성한 뒤 MySQL·FastAPI·React로 연결합니다. React에서 저장한 관리자 판단·대상 명단·운영안은 다시 MySQL에 기록됩니다.

### 데이터 범위와 시간 분할

<p align="center">
  <img src="docs/assets/readme/07_data_scope_and_cohort.svg" alt="데이터 범위와 개발·OOF·Final Test 코호트 구성" width="100%">
</p>

전체 37,953건은 개발 코호트 31,420건과 Final Test 6,533건으로 구성됩니다. OOF 24,596건은 별도 표본이 아니라 개발 코호트 중 2013~2017년 공통 평가 부분집합입니다.

| 버전 표기 | 역할 |
|---|---|
| 코호트 `v04` | 선정 기준·시간 구조와 분석 대상 정의 |
| 운영 모델 `v05_05_dl` | 현재 위험 상태·순위 산출에 사용하는 최종 모델 |
| DB `model_version` | 저장된 예측·판단의 모델 문맥을 식별하는 데이터 계약 값 |

세 표기는 서로 다른 대상을 설명하므로 숫자를 억지로 일치시키지 않습니다.

### Final Test 상태 분포

<p align="center">
  <img src="docs/assets/readme/08_final_test_distribution.svg" alt="Final Test 유지·약화·중단 상태 분포" width="100%">
</p>

### EDA·데이터 조건과 전처리 반영

<p align="center">
  <img src="docs/assets/readme/11_preprocessing_decisions.png" alt="EDA 데이터 조건과 전처리·검증 결정" width="72%">
</p>

시간 순서를 보존한 검증, 예측 시점 이후 정보 격리, 활동 변화 피처와 의미 기반 결측 처리를 적용했습니다. DL 입력은 월별 변화와 장기 이력을 결합할 수 있도록 `24개월 × Core4` 시퀀스와 Lifecycle 5개 정적 피처로 분리했습니다.

### 피처 상관관계 검토

<p align="center">
  <img src="docs/assets/readme/09_feature_correlation_review.png" alt="피처 그룹별 주요 고상관 변수와 최종 반영 판단" width="100%">
</p>

ML Core45에서는 고상관을 곧바로 제거 기준으로 사용하지 않고 OOF 성능·중요도·해석성을 함께 검토했습니다. 트리 기반 후보는 전체 피처를 유지해 비교했으며, 최종 DL은 이 검토와 별도로 `Monthly Core4 + Lifecycle 5개` 입력 구조를 사용합니다.

### 모델 입력 비교

<p align="center">
  <img src="docs/assets/readme/12_model_input_comparison.png" alt="ML 후보와 최종 DL 모델 입력 구조 비교" width="82%">
</p>

상세 피처와 처리 기준은 [데이터 전처리 결과서](docs/02_reports/01_data_preprocessing_report.md)를 참고하세요.

---

## 모델

### 문제 정의

선정 연도에 음식 관련 리뷰 10건 이상, 활동 월 3개월 이상인 핵심 리뷰어를 대상으로 다음 연도 상태를 분류합니다.

| 클래스 | 다음 연도 조건 |
|---|---|
| 유지 `retained` | 리뷰 10건 이상 AND 활동 월 3개월 이상 |
| 약화 `weakened` | 리뷰 1건 이상이며 유지 조건 미충족 |
| 중단 `stopped` | 음식 관련 리뷰 0건 |

### `v05_05_dl` 구조

<p align="center">
  <img src="docs/assets/readme/13_model_architecture.png" alt="v05_05_dl GRU·Lifecycle Fusion·Hierarchical H2 구조" width="82%">
</p>

GRU가 24개월 활동 시퀀스를, Lifecycle MLP가 장기 이력을 인코딩합니다. 결합 표현은 유지와 위험군을 먼저 구분한 뒤 위험군을 약화와 중단으로 나누며, seed 42·2026·3405의 모델 점수를 평균해 최종 위험 순위를 생성합니다.

### 후보 모델 비교

동일한 OOF 표본 24,596건에서 ML·DL 후보를 비교했습니다.

<p align="center">
  <img src="docs/assets/readme/14_model_candidate_performance.png" alt="ML·DL 후보의 OOF Macro F1과 Macro PR-AUC 비교" width="82%">
</p>

| 운영 지표 | `v05_05_dl` | `v05_06_dl` |
|---|---:|---:|
| Precision@1000 | **90.60%** | 90.04% |
| 중증 오분류 | **2.19% · 538건** | 2.64% · 650건 |

> 시계열 데이터의 시간 누수를 방지하기 위해 **2010~2017년 개발 코호트의 Expanding-Time OOF 검증**을 기반으로 모델을 평가하고 선정했습니다.

**모델 선정 기준:** 동일 OOF 표본에서 Macro F1을 우선 비교하고, 동등한 수준이면 Macro PR-AUC와 Precision@1000·중증 오분류 등 운영 지표를 함께 검토했습니다.
   
**OOF Macro F1과 OOF Macro PR-AUC가 모두 가장 우수하고 운영 지표의 균형도 확인된 `v05_05_dl`을 최종 모델로 선정했습니다.**

### OOF 수락 기준

| 평가 지표 | 수락 기준 | 결과 | 판정 |
|---|---:|---:|---|
| Macro F1 | 0.5700 이상 | **0.5763** | PASS |
| Macro PR-AUC | 0.5900 이상 | **0.5980** | PASS |
| Precision@1000 | 90.0% 이상 | **90.60%** | PASS |
| 중증 오분류 | 2.5% 이하 | **2.19% · 538건** | PASS |

### Final Test

Final Test는 모델 선정에 사용하지 않은 2018년 선정 코호트로 수행했습니다. 가중치와 임계값은 OOF 검증까지만 사용해 고정했으며, 사전에 Final Test 합격 임계값을 확정하지 않았으므로 OOF 기준을 소급 적용해 PASS·FAIL로 판정하지 않습니다.

> **용어 구분:** OOF는 개발 코호트 안에서 모델·임계값을 선택하는 검증 결과이고, Final Test는 선택이 끝난 모델을 별도의 미래 시점 코호트에서 평가한 결과입니다. Final Test를 모델 선택 근거로 사용하지 않습니다.

<p align="center">
  <img src="docs/assets/readme/10_oof_final_test_comparison.png" alt="OOF와 Final Test 주요 성능 비교" width="100%">
</p>

Macro F1과 Macro PR-AUC의 변화 폭은 작았지만, `Stopped Recall`은 43.25%에서 37.56%로 5.69%p 감소해 완전 중단 리뷰어 탐지에는 개선 여지가 있습니다. 중증 오분류율은 2.19%에서 1.81%로 낮아졌습니다.

| Final Test 운영 순위 지표 | 결과 |
|---|---:|
| Top 20% Precision | **89.29%** |
| Top 20% Recall | **29.55%** |
| Top 20% Lift | **1.48배** |

현재 `v05_05_dl`의 변수별 정량 중요도 산출물은 없습니다. 월별 시퀀스와 Lifecycle 특성은 모델 입력이지만 각 특성의 독립적인 인과 효과를 의미하지 않습니다.

---

## 화면 구성

<p align="center">
  <img src="docs/assets/readme/02_screen_flow.png" alt="Yelp Reviewer Retention Ops 화면 구성" width="100%">
</p>

| 단계 | 화면 | 운영 질문 | 주요 기능 |
|---:|---|---|---|
| 1 | 콘텐츠 공급 위험 | 어디의 공급이 줄었나? | 권역·도시별 공급·핵심·신규 비교와 우선 지역 탐색 |
| 2 | 핵심 리뷰어 관리 | 누구를 먼저 검토하나? | 위험 유형·우선순위·판단 상태 필터와 상세 이동 |
| 3 | Reviewer 360 | 어떤 활동이 변했나? | 활동량·작성 주기·탐색·반경 근거와 관리자 판단 |
| 4 | 운영안 설계 | 어떤 운영안을 저장할까? | 개인 특별 관리와 지역 활성화 운영안 저장 |
| 5 | 운영 결과·알림 | 언제 다시 확인할까? | 판단·명단·운영안·접촉·감사·재검토 이력 |

---

## 업무 흐름

<p align="center">
  <img src="docs/assets/readme/03_operations_flow.png" alt="Yelp Reviewer Retention Ops 업무 흐름" width="100%">
</p>

- **Track A · 개인 리뷰어 운영:** 핵심 리뷰어 선택 → Reviewer 360 근거·판단 → 개인 특별 관리안 저장
- **Track B · 지역 활성화 운영:** 권역·도시 선택 → CRM 후보·위험 신호 확인 → 추천 음식점·후원 후보 검토 → 지역 운영안 저장

저장된 판단, 대상 명단과 운영안은 운영 이력에서 다시 확인하며 수동 재검토를 통해 다음 운영 주기로 연결합니다. 외부 CRM 발송과 실제 성과 수집은 현재 연동하지 않습니다.

---

## 실행 가이드

> **주의:** DB/서비스 실행 전 모델 재현 파이프라인 실행이 선행되어야 합니다.

### 1. 사전 준비

- Python 3.12, Node.js, MySQL을 준비합니다.
- 분석·운영 DB `yelp_data`와 인증 DB `reviewer_retention_auth`를 분리해 구성합니다.
- `database/.env`와 `auth_service/.env`를 각 예시 파일에 맞춰 작성합니다.
- DB DDL·적재 절차는 [database/README.md](database/README.md)를 따릅니다.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r api\requirements.txt -r auth_service\requirements.txt

cd app
npm ci
cd ..
```

모델을 재학습하려면 DL 의존성을 추가로 설치합니다.

```powershell
python -m pip install -r requirements-dl.txt
```

### 2. 서비스 실행

각 명령을 프로젝트 루트의 별도 터미널에서 실행합니다.

```powershell
# 분석·운영 API — http://127.0.0.1:8000
python -m uvicorn api.main:app --reload --port 8000

# 인증 서비스 — http://127.0.0.1:8100
python -m uvicorn auth_service.main:app --reload --port 8100

# React — http://localhost:5173
cd app
npm run dev
```

Windows에서는 `RUN_LOCAL.cmd`로 로컬 서비스를 함께 시작할 수 있습니다. 최초 관리자 생성과 상세 환경 설정은 [로컬 실행 가이드](docs/04_architecture_and_guides/LOCAL_RUN_GUIDE.md)를 참고하세요.

### 3. 기본 검증

```powershell
python -m compileall -q api auth_service shared scripts
python -m unittest tests.test_demo_contract tests.test_historical_metric_loaders tests.test_reference_data_seed
python -m pytest api/tests auth_service/tests -q

cd app
npm run lint
npm run build
```

---

## 모델 재현 파이프라인 실행 가이드

### 원본 데이터 준비

* 원본 데이터셋 출처: [Yelp Open Dataset](https://business.yelp.com/data/resources/open-dataset/)  
* 다운로드받은 원본 데이터를 아래 디렉터리 구조로 배치합니다.

```python
data/
└── raw/
    ├── yelp_academic_dataset_business.json
    ├── yelp_academic_dataset_review.json
    └── yelp_academic_dataset_user.json
```

### v04 파이프라인 실행 (DB 적재 시 선행 필요)
```bash
python pipeline/v04
```

### 머신러닝 파이프라인 실행

```bash
python pipeline/v05_ml
```

#### 1\. 데이터 전처리 산출물 (`preprocessing.py`)

이 단계에서는 원본 JSON 파일들로부터 필터링, 추출, 병합, 피처 엔지니어링을 거쳐 모델 학습을 위한 최종 데이터셋이 만들어집니다.

| 단계 | 산출물 파일명 | 저장 경로 (프로젝트 루트 기준) | 설명 |
| :---- | :---- | :---- | :---- |
| **업체 필터링** | `restaurant_businesses.parquet` | `data/interim/` | 핵심 음식점(Restaurants) 카테고리 업체 데이터 |
|  | `additional_culinary_businesses_v02.parquet` | `data/interim/` | 추가 미식 방문형(카페, 디저트 등) 업체 데이터 |
| **리뷰 추출** | `restaurant_reviews.parquet` | `data/interim/` | 핵심 음식점의 전체 리뷰 데이터 |
|  | `additional_culinary_reviews_v02.parquet` | `data/interim/` | 추가 미식 방문형 업체의 전체 리뷰 데이터 |
| **코호트 생성** | `culinary_rolling_cohort_master_v*.parquet` | `data/interim/rolling/` | (설정 파일 경로 우선) 롤링 코호트 기준 유저, 라벨, 연도 매핑 마스터 데이터 |
| **데이터셋 결합** | `modeling_dataset_rolling_v05_ml.parquet` | `data/processed/` | **\[최종 결과물\]** 모델 학습에 즉시 투입할 수 있는 43개+ 피처 및 타겟 결합 데이터 |

#### 2\. 모델링 및 평가 산출물 (`modeling.py`)

전처리된 데이터셋을 기반으로 XGBoost 모델을 학습하고 하이퍼파라미터를 탐색한 뒤, 최종 평가 지표 및 리포트를 생성합니다.

| 분류 | 산출물 파일명 | 저장 경로 (프로젝트 루트 기준) | 설명 |
| :---- | :---- | :---- | :---- |
| **최종 모델** | `xgboost_final_core_multiclass_v05.joblib` | `models/` | 학습이 완료된 최종 XGBoost 모델 객체 |
| **메타데이터** | `xgboost_multiclass_metadata_v05.json` | `models/` | 모델 구성, 평가 지표(F1, AUC 등), 선택 파라미터 등을 저장한 JSON 메타데이터 |
| **CRM 프로필** | `xgboost_final_test_retention_profiles_v05_ml.parquet` | `data/processed/predictions/` | Test 데이터 유저별 예측 확률, 상태(유지/약화/중단) 및 마케팅 타겟팅 우선순위(Rank/Score) 데이터 |
| **마크다운 리포트** | `xgboost_multiclass_model_performance_v05.md` | `reports/modeling/` | 깃허브나 문서에 바로 활용 가능한 모델 성능 및 Top 20% 정책 요약 마크다운 리포트 |
| **분석 결과 표** | `xgboost_multiclass_model_candidates_v05.csv` | `reports/tables/` | Grid Search로 탐색한 모든 하이퍼파라미터 및 임계값 조합별 성능 기록 |
|  | `xgboost_multiclass_validation_results_v05.csv` | `reports/tables/` | Fold별 교차 검증(CV) 및 Test 데이터의 Base 평가 지표 결과 |
|  | `xgboost_multiclass_confusion_matrix_v05.csv` | `reports/tables/` | OOF 및 Test 데이터에 대한 혼동 행렬(Confusion Matrix) 상세 수치 |
|  | `xgboost_multiclass_top_k_performance_v05.csv` | `reports/tables/` | 상위 5% \~ 40% 타겟팅 비율(Top-K)에 따른 Precision, Recall, Lift 지표 산출 기록 |
|  | `xgboost_feature_importance_v05.csv` | `reports/tables/` | Permutation Importance 기법을 통해 산출된 피처별 중요도 및 순위 데이터 |

---

### 딥러닝 파이프라인 실행

```bash
python pipeline/v05_05_dl/preprocessing.py

python pipeline/v05_05_dl/build_features.py --user-json data/raw/yelp_academic_dataset_user.json --overwrite
python pipeline/v05_05_dl/train.py --overwrite

python pipeline/v05_05_dl/build_test_features.py --user-json data/raw/yelp_academic_dataset_user.json --overwrite
python pipeline/v05_05_dl/evaluate_test.py --overwrite
```

#### 1단계: 학습/검증 피처 생성 (`build_features.py`)

이 단계에서는 2010년\~2017년(Development) 데이터에 대한 시계열 시퀀스와 라이프사이클 피처를 생성합니다.

| 분류 | 산출물 파일명 | 저장 경로 | 설명 |
| :---- | :---- | :---- | :---- |
| **피처 데이터** | `lifecycle_features_v05_05.parquet` | `data/processed/experiments/` | 모델 학습용 유저 라이프사이클(Elite 이력, 가입 기간 등) 피처 |
|  | `monthly_core4_sequence_v05_05.parquet` | `data/processed/experiments/` | 모델 학습용 24개월 활동 시계열 시퀀스 피처 |
| **메타데이터** | `feature_build_metadata.json` | `reports/experiments/v05_05_dl/` | 피처 생성 과정의 행 개수, 컬럼 정보 및 해시값 기록 |

#### 2단계: 모델 학습 및 OOF 평가 (`train.py`)

생성된 피처를 바탕으로 PyTorch 딥러닝 모델(Lifecycle Fusion H2)을 학습하고, 교차 검증(OOF)을 통해 최적의 임계값(Threshold)을 탐색합니다.

| 분류 | 산출물 파일명 | 저장 경로 | 설명 |
| :---- | :---- | :---- | :---- |
| **저장 모델** | `preprocessing.joblib` | `models/experiments/v05_05_dl/` | 시퀀스 및 라이프사이클 스케일러(StandardScaler) 전처리 객체 |
|  | `seed_{seed}_state_dict.pt` | `models/experiments/v05_05_dl/` | 시드(seed)별로 학습된 PyTorch 모델 가중치(Weights) 파일들 |
| **정보/리포트** | `metadata.json` | `models/experiments/v05_05_dl/` | 최종 모델의 아키텍처, 검증 점수 등 전체 메타데이터 |
|  | `performance.md` | `reports/experiments/v05_05_dl/` | OOF 검증 결과 및 성능 비교 요약 마크다운 리포트 |
| **평가 결과** | `selected_oof_candidate.json` | `reports/experiments/v05_05_dl/` | Grid Search로 선택된 최적의 타겟팅 임계값 및 결과 |
|  | `oof_predictions.parquet` | `reports/experiments/v05_05_dl/` | 검증 데이터(OOF)에 대한 시드별 및 앙상블 예측 확률 결과 |
|  | `threshold_candidates.csv` | `reports/experiments/v05_05_dl/` | 모든 임계값 조합에 대한 F1, AUC 성능 탐색 결과표 |
|  | `oof_confusion.csv` | `reports/experiments/v05_05_dl/` | OOF 예측에 대한 혼동 행렬(Confusion Matrix) |
|  | `oof_top_k_by_year.csv` | `reports/experiments/v05_05_dl/` | 연도별 Top-K 타겟팅 정밀도(Precision), Lift 등 상세 지표 |
|  | `oof_top_k_summary.csv` | `reports/experiments/v05_05_dl/` | Top-K 타겟팅 성능 요약 표 |
|  | `oof_model_comparison.csv` | `reports/experiments/v05_05_dl/` | 이전 기준 모델(v05\_04 등)과의 OOF 성능 수치 비교 표 |
|  | `paired_bootstrap.csv` | `reports/experiments/v05_05_dl/` | 이전 모델과의 성능 차이에 대한 신뢰구간(Bootstrap) 기록 |

#### 3단계: 테스트 피처 생성 (`build_test_features.py`)

학습 시 전혀 사용되지 않은 2018년(Test) 코호트 유저들을 대상으로만 피처를 생성합니다.

| 분류 | 산출물 파일명 | 저장 경로 | 설명 |
| :---- | :---- | :---- | :---- |
| **피처 데이터** | `test_lifecycle_features_v05_05.parquet` | `data/processed/experiments/` | 최종 테스트용 유저 라이프사이클 피처 |
|  | `test_monthly_core4_sequence_v05_05.parquet` | `data/processed/experiments/` | 최종 테스트용 24개월 활동 시계열 시퀀스 피처 |
| **메타데이터** | `test_feature_build_metadata.json` | `reports/experiments/v05_05_dl/` | 테스트 피처 생성 설정 및 데이터 무결성(검증) 메타데이터 |

#### 4단계: 최종 테스트 셋 평가 (`evaluate_test.py`)

미리 고정된 딥러닝 모델 가중치와 최적화된 임계값을 Test 피처에 적용하여 2019년 결과를 예측하고, CRM용 프로필을 뽑아냅니다.

| 분류 | 산출물 파일명 | 저장 경로 | 설명 |
| :---- | :---- | :---- | :---- |
| **최종 결과** | `test_retention_profiles_v05_05_dl.parquet` | `data/processed/predictions/` | **\[최종 산출물\]** 마케팅팀 전달용 유저별 예측 상태 및 우선순위(Rank) 프로필 |
| **예측/결과** | `test_predictions.parquet` | `reports/experiments/v05_05_dl/` | 전체 Test 데이터에 대한 예측 확률 및 분류 상태 상세 기록 |
|  | `test_metrics.csv` | `reports/experiments/v05_05_dl/` | 최종 Test 셋 평가 지표 (F1, PR-AUC, Accuracy 등) 기록표 |
|  | `test_confusion.csv` | `reports/experiments/v05_05_dl/` | 최종 Test 예측 결과 혼동 행렬 |
|  | `test_top_k.csv` | `reports/experiments/v05_05_dl/` | Test 셋 대상의 Top-K (상위 마케팅 개입 대상) 성능 타겟팅 지표 |
| **정보/리포트** | `test_metrics.json` | `reports/experiments/v05_05_dl/` | 평가 지표 종합 및 OOF와의 성능 차이 등을 기록한 JSON |
|  | `test_performance.md` | `reports/experiments/v05_05_dl/` | 문서나 리드미에 바로 사용할 수 있는 딥러닝 테스트 결과 마크다운 리포트 |

```text
# 산출물 파일 구조도
├── data/
│   └── processed/
│       ├── modeling_dataset_rolling_v05_ml.parquet            # [입력] 롤링 코호트 결합 데이터
│       ├── experiments/
│       │   ├── lifecycle_features_v05_05.parquet              # [입력/DL] 2010-2017 라이프사이클 피처
│       │   └── monthly_core4_sequence_v05_05.parquet          # [입력/DL] 2010-2017 24개월 시퀀스 피처
│       └── predictions/
│           ├── xgboost_final_test_retention_profiles_v05_ml.parquet   # [ML 최종 산출] 2018 Test CRM 프로필
│           └── test_retention_profiles_v05_05_dl.parquet              # [DL 최종 산출] 2018 Test CRM 프로필
│
├── models/
│   ├── xgboost_final_core_multiclass_v05.joblib               # [ML Artifact] 최종 학습 모델
│   ├── xgboost_multiclass_metadata_v05.json                   # [ML Meta/SHA] 설정 및 model_sha256
│   └── experiments/
│       └── v05_05_dl/
│           ├── preprocessing.joblib                           # [DL Preprocessor] 스케일러 객체
│           ├── seed_42_state_dict.pt                          # [DL Weights] Seed 42 가중치
│           ├── seed_2026_state_dict.pt                        # [DL Weights] Seed 2026 가중치
│           ├── seed_3405_state_dict.pt                        # [DL Weights] Seed 3405 가중치
│           └── metadata.json                                  # [DL Meta/SHA] weight_sha256 & preproc_sha256
│
└── reports/
    ├── modeling/
    │   └── xgboost_multiclass_model_performance_v05.md        # [ML Report] XGBoost 최종 성능 리포트
    ├── tables/
    │   ├── xgboost_multiclass_model_candidates_v05.csv        # [ML Table] Grid Search 파라미터 탐색표
    │   ├── xgboost_multiclass_validation_results_v05.csv      # [ML Table] 5-Fold / OOF / Test 검증표
    │   ├── xgboost_multiclass_confusion_matrix_v05.csv        # [ML Table] OOF & Test 혼동행렬
    │   ├── xgboost_multiclass_top_k_performance_v05.csv       # [ML Table] Top-K 타깃팅 성능표
    │   └── xgboost_feature_importance_v05.csv                 # [ML Table] Permutation 중요도
    └── experiments/
        └── v05_05_dl/
            ├── performance.md                                 # [DL Report] OOF 검증 결과 리포트
            ├── selected_oof_candidate.json                    # [DL Meta] 최적 OOF 임계값 설정
            ├── oof_predictions.parquet                        # [DL OOF] Fold별/앙상블 예측값
            ├── threshold_candidates.csv                       # [DL Table] 임계값 조합 탐색표
            ├── oof_confusion.csv                              # [DL Table] OOF 혼동행렬
            ├── oof_top_k_by_year.csv                          # [DL Table] 연도별 Top-K 지표
            ├── oof_top_k_summary.csv                          # [DL Table] Top-K 요약표
            ├── oof_model_comparison.csv                       # [DL Table] v05_04 대비 성능 비교표
            └── paired_bootstrap.csv                           # [DL Table] 통계적 유의성 부트스트랩
```

---

## 현재 검증·배포 상태

HTTPS 서비스 접속과 `v05_05_dl` 연동은 확인됐지만, 역할별 실환경 검증과 앱 부분 장애 대응·최종 회귀가 남아 있어 최종 운영 승인은 보류 상태입니다.

| 검증 | 결과 |
|---|---|
| React lint / build | PASS |
| PR 차단 CI | PASS — Python·API/Auth·React artifact-free 검증 |
| 배포 워크플로 단위 테스트 | 9건 PASS |
| v05 운영 컨텍스트·UI·모델 로더 계약 | 19건 PASS |
| 운영 인증·HTTPS·Secure Cookie | PASS |
| 역할·권역 실제 계정 / 비허용 CORS | PARTIAL — 최종 회귀 필요 |
| Snooze·History / 부분 장애 대응 | PARTIAL·NOT RUN — A 영역 담당 작업 필요 |
| 관리자 UI 전체 QA | 135건 중 PASS 95 · FAIL 17 · PARTIAL 6 · NOT RUN 17 |
| 서비스 배포 | 완료 — 운영 주소 접속 가능 |
| v05 모델 서비스 연동 | 완료 — `v05_05_dl` 운영 표시 확인 |
| 최종 배포 승인 | **보류** |

미인증 Retention API 401, HTTPS 전환과 Secure Cookie는 최신 운영 검증에서 PASS했습니다. 남은 차단 항목은 실제 계정 기반 권역·CORS 검증, Snooze·History React 검산, 부분 장애 대응, 배포 식별자와 최종 회귀입니다. 과거 QA 결과는 당시 기록으로 보존하며 최신 판정은 [AWS HTTPS 재배포 보고서](docs/02_reports/04_aws_https_redeployment_report_2026-09-02.md)와 이후 Final Regression을 따릅니다.

---

## 트러블슈팅

| 증상 | 확인·해결 방법 |
|---|---|
| PowerShell에서 `npm` 실행 정책 오류 | `npm.cmd install`, `npm.cmd run dev`, `npm.cmd run build` 형태로 실행 |
| React 화면에 데이터가 표시되지 않음 | FastAPI `http://127.0.0.1:8000/health`와 MySQL 연결을 먼저 확인. 현재 React에는 API 실패 시 정적 JSON 자동 폴백이 없음 |
| 인증 후 다시 로그인 화면으로 이동 | 인증 서비스 8100 포트, 쿠키·CORS·CSRF 환경값과 프런트 API URL을 함께 확인 |
| MySQL 테이블 또는 데이터가 없음 | `database/README.md`의 DDL→적재→검증 순서를 다시 실행하고 DB 이름을 확인 |
| 모델 파일을 찾을 수 없음 | `models/`는 Git에 포함되지 않으므로 승인된 위치에서 받거나 모델 재생성 절차 수행 |
| 포트가 이미 사용 중임 | 5173·8000·8100 포트의 기존 프로세스를 확인한 후 종료하거나 실행 포트를 변경 |

상세 환경 변수와 실행 순서는 [로컬 실행 가이드](docs/04_architecture_and_guides/LOCAL_RUN_GUIDE.md)를 참고하세요.

### 팀 개발 트러블슈팅 미리보기

| 작성자 | 문제 상황 | 해결 방향 | 핵심 교훈 |
|---|---|---|---|
| 김기호 | 피처를 경량화한 XGBoost의 성능이 전체 피처 모델보다 하락 | 동일한 시간 분할에서 후보를 재평가하고 Core45 기반 `v05_2`를 ML 비교 모델로 유지 | 피처 제거는 단순 통계보다 상호작용과 검증 성과를 기준으로 결정 |
| 김동섭 | 피처를 81개로 확장했지만 주요 DL 성능이 하락 | Core43·확장 피처·24개월 GRU 결합 모델을 통제 비교 | 피처 개수보다 기존 정보와 다른 신호를 제공하는지가 중요 |
| 이홍규 | 월별 활동량이 모델 프로필보다 작게 집계 | 누락된 추가 음식 리뷰 원천을 결합하고 6,533명 전수 합계 검증 | 같은 지표도 원천과 집계 범위를 데이터 계약으로 맞춰야 함 |
| 최인영 | AWS 배포 후 React에서 `Failed to fetch` 발생 | React를 상대 경로 `/api`로 전환하고 Nginx가 FastAPI로 프록시하도록 구성 | 로컬·배포 주소 차이는 하드코딩보다 공개 경로 계약으로 관리 |

팀원별 문제 상황·원인·해결 방법·결과·회고 13건은 [팀 트러블슈팅 전체 기록](docs/07_history_and_handoff/TEAM_TROUBLESHOOTING.csv)에서 확인할 수 있습니다.

---

## 향후 개선 방향

![Yelp Reviewer Retention Ops 향후 로드맵](docs/assets/readme/15_future_roadmap.png)

현재는 기능 확장보다 운영 기준선을 안정화하는 작업을 우선합니다.

- 역할·권역 실제 계정, 비허용 CORS와 부분 장애 시나리오 검증
- Snooze·History React 복원 검산과 동일 배포본 기준 전체 QA 재실행
- 모델 가중치·메타데이터의 공식 보관 위치, 체크섬과 버전 정책 확정
- 모바일 `/trust` 가로 넘침과 접근 가능한 이름 등 반응형·접근성 보완

이후 실행·성과 데이터 계약, 월 단위 조기경보, 약화·중단 상태별 운영, 효과 실험과 지속 개선 순으로 확장합니다. Consumer용 맛집·리뷰어 탐색은 현재 관리자 서비스와 분리된 향후 후보이며 구현된 기능으로 보지 않습니다. 단계별 목표와 완료 기준은 [서비스 제품화 및 적용 로드맵](docs/08_future_roadmap/06_service_productization_and_application.md)에서 확인할 수 있습니다.

---

## 문서

| 문서 | 설명 |
|---|---|
| [프로젝트 요구사항 명세서](docs/01_business/project_requirements.md) | 범위, 요구사항, 수락 기준, QA·배포 게이트 |
| [WBS](docs/01_business/WBS.md) | 역할, 일정, 선행 관계, 산출물과 현재 상태 |
| [데이터 전처리 결과서](docs/02_reports/01_data_preprocessing_report.md) | 코호트·결측·피처·시간 분할·전처리 검증 |
| [모델 학습 결과서](docs/02_reports/02_model_training_report.md) | 후보 비교, `v05_05_dl`, OOF·Final Test, 산출물 계약 |
| [모델 배포·테스트 결과서](docs/02_reports/03_model_deployment_test_report.md) | 정적 검증, 운영 선택 재검증, 배포 게이트 판정 |
| [발표 후 개선 및 Finalization 기록](docs/02_reports/05_post_presentation_improvements.md) | 문제, 변경, 검증 근거와 팀·개인 범위 구분 |
| [비즈니스 시나리오](docs/01_business/business_scenarios.md) | 운영 문제와 활용 시나리오 |
| [로컬 실행 가이드](docs/04_architecture_and_guides/LOCAL_RUN_GUIDE.md) | MySQL·API·인증·React 실행 절차 |
| [AWS 배포 가이드](docs/04_architecture_and_guides/AWS_DEPLOYMENT.md) | 배포 구성과 운영 절차 |
| [QA 케이스](docs/qa/ADMIN_UI_QA_CASES.md) | 관리자 UI 135개 테스트 시나리오 |
| [QA 실행 결과](docs/qa/ADMIN_UI_QA_EXECUTION_2026-08-05.md) | PASS·FAIL·미실행 결과와 결함 |
| [의사결정 기록](docs/06_decisions/) | 데이터·코호트·모델·운영 정책 결정 |
| [팀 트러블슈팅 기록](docs/07_history_and_handoff/TEAM_TROUBLESHOOTING.csv) | 팀원별 문제 상황, 원인, 해결 방법, 결과와 회고 13건 |

---

## 범위와 한계

- 모델 점수는 확률이나 의학적 진단이 아닌 상대적 운영 우선순위입니다.
- 리뷰 활동 위치를 거주지·직장·실제 생활 반경으로 해석하지 않습니다.
- 운영안은 검증된 처방이 아니라 운영자가 검토할 가설입니다.
- 이메일·푸시·쿠폰·혜택 제공과 실제 CRM 발송은 구현 범위에서 제외합니다.
- 캠페인 성과는 실제 실행·성과 데이터가 없어 인과 효과를 보장하지 않습니다.
- 외부 CRM 발송·성과 수집 미연동 상태이므로 재검토는 현재 수동 운영입니다.
- v04 산출물과 이전 Streamlit 앱은 비교·롤백·이력 확인 목적으로만 보존합니다.

---

## 💬 회고

> **최인영** : AWS Lightsail 서비스를 처음 다뤄봤지만 DB 구축과 배포에 만족스럽게 성공하여 인프라에 대한 기초를 수월하게 학습할 수 있었습니다.
>
> **김기호** : AI 모델 개발에서 복잡한 구조나 튜닝보다 선행되어야 할 핵심은 '양질의 데이터'와 '도메인 기반의 정밀한 피처 엔지니어링'임을 깊이 체감한 프로젝트였습니다.
>
> **김동섭** : 핵심 리뷰어의 활동 변화를 정의하고, 시간 누수를 방지한 데이터 분할과 피처 설계를 통해 이탈 위험 예측 모델을 개발한 과정이 인상 깊었다. 모델 성능을 개선하는 것뿐만 아니라 예측 근거를 해석하고, 모델의 예측 결과를 실제 서비스 화면에 적용하는 경험을 쌓을 수 있었으며, 팀원들과 데이터·모델·서비스를 함께 검증하며 협업의 중요성을 배웠고, 향후에는 모델의 안정성과 실무 활용성을 더욱 높이고 싶습니다.
>
> **이홍규** :  모델 결과를 보여주는 데 그치지 않고, 공통 데이터 계약과 운영 UX를 정리해 탐지부터 재검토까지 이어지는 서비스 형태로 연결한 점이 가장 의미 있었습니다.
>서비스 범위가 빠르게 확장되면서 통합 QA와 보안·권한 검증, 모델 산출물 관리 기준을 충분히 앞당기지 못한 점은 아쉬움으로 남았습니다.
>다음 프로젝트에서는 수락 기준과 자동 테스트, 릴리스 체크리스트를 초기부터 연결해 구현 완료와 운영 준비를 함께 관리해보고 싶습니다.

---

<div align="center">

### 모델이 답을 대신하는 서비스가 아니라, 운영자가 더 좋은 판단을 내리게 하는 서비스

`데이터로 발견하고 · 근거로 판단하고 · 운영 기록으로 연결합니다.`

Yelp Open Dataset 기반 비상업 분석 프로젝트이며 Yelp의 공식 서비스가 아닙니다.

</div>
