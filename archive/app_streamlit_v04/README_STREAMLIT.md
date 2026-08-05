# Yelp Reviewer Retention Operations v0.4

Yelp 파워 리뷰어의 리뷰 활동 루틴 변화를 이용해 다음 연도 이탈 위험을
선별하고, 운영자가 관리 대상과 리텐션 전략을 결정할 수 있도록 만든
서비스형 Streamlit 프로토타입이다.

기존 분석용 `app_data_prototype/`과 별개로 프로젝트 루트의 `app/`에서
실행하도록 설계했다.

v0.4는 기존 운영 화면 구조를 유지하면서 2018년 파워 리뷰어 후보의
2019년 실제 상태를 검증하는 데이터 묶음으로 전환한 버전이다.

기존 디자인은 고정 사이드바를 제거하고,
운영자의 `상황 파악 → 대상 선택 → 근거 확인 → 개입 결정` 흐름을 중심으로
정보 구조와 디자인 시스템을 재설계한 버전이다.

## 주요 화면

| 화면 | 목적 | 상태 |
|---|---|---|
| 운영 홈 | 오늘의 관리 대상과 핵심 운영 KPI | 현재 구현 |
| 위험 리뷰어 관리 | 필터·검색·다운로드·빠른 진단 | 현재 구현 |
| 리뷰어 360 | 리뷰어 관리에서 진입하는 활동 변화·위험 근거·전략 판단서 | 현재 구현 |
| 리텐션 플레이북 | 위험 유형별 개입 전략 | 규칙 기반 |
| 지역 콘텐츠 위험 | 지역별 리뷰 공급 위험 | 1차 고도화 예정 |
| 모델 신뢰 센터 | Test 성능·Top-K·모델 근거 | 현재 구현 |
| 제품 상태·로드맵 | 모델 신뢰 센터 안에서 데이터 준비도와 활성화 조건 관리 | 고도화 안내 |

## v0.4 화면 원칙

- 상단 업무 내비게이션을 사용하고 전역 고정 사이드바를 두지 않는다.
- 운영 홈에서 `1,307명 검토 → 지위 상실 1,142명 포착 → 28.92% Recall → 1.45배 Lift`와 우선 검토 큐가 연결된다.
- 리뷰어 관리에서 검색·필터·정렬·다중 비교·CSV 다운로드 후 Reviewer 360으로 진입한다.
- Reviewer 360에서는 활동 변화·위험 근거·리텐션 제안과 사후 검증 결과를 분리한다.
- 같은 카드 레이아웃을 반복하지 않고 표, 차트, 구분선 목록, 행동 레일을 목적에 맞게 사용한다.
- 데이터가 없는 기능은 목적, 필요 데이터, 활성화 조건을 표시하며 가짜 수치를 사용하지 않는다.

## 프로젝트에 적용

ZIP 파일의 내용을 `SKN34-2nd-5Team` 프로젝트 루트에 압축 해제한다.

```text
SKN34-2nd-5Team/
├─ app/
│  ├─ streamlit_app.py
│  ├─ core/
│  └─ views/
├─ app_data_prototype/       # 기존 분석 앱, 그대로 유지
├─ data/
├─ reports/
├─ models/
├─ .streamlit/
├─ requirements-streamlit.txt
├─ run_app.bat
└─ run_app.ps1
```

동일한 이름의 `app/`이 이미 있다면 먼저 백업한 후 적용한다.

## 설치

프로젝트 가상환경을 활성화한다.

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements-streamlit.txt
```

프로젝트의 기존 `requirements.txt`에 pandas, numpy, pyarrow가 이미
고정되어 있다면 다음 패키지만 추가해도 된다.

```powershell
python -m pip install streamlit==1.60.0 plotly==5.24.1
```

## 실행

```powershell
python -m streamlit run app\streamlit_app.py
```

또는 프로젝트 루트의 `run_app.bat`을 실행한다.

## 실제 데이터 자동 연결

앱은 프로젝트 루트를 탐색해 다음 v04 핵심 묶음을 함께 읽는다.

```text
data/processed/predictions/final_test_retention_profiles_v04.parquet
models/final_core_logistic_multiclass_metadata_v04.json
reports/tables/multiclass_validation_results_v04.csv
reports/tables/multiclass_top_k_performance_v04.csv
reports/tables/multiclass_confusion_matrix_v04.csv
reports/tables/final_feature_importance_v04.csv
reports/tables/final_feature_group_importance_v04.csv
```

프로젝트 밖에서 실행해야 한다면 환경 변수로 루트를 지정한다.

```powershell
$env:YELP_PROJECT_ROOT = "C:\Users\playdata2\SKN34-2nd-5Team"
python -m streamlit run app\streamlit_app.py
```

## 데모 모드

위험 프로필 파일이 없으면 앱은 자동으로 익명 데모 데이터로 실행된다.
데모 데이터는 v04 최종 Test 결과와 동일한 익명 집계를 재현한다.

- 분석 리뷰어 6,533명
- 통합 상위 20% 검토 대상 1,307명
- 실제 지위 상실 포착 1,142명
- 유지 우세 2,332명
- 약화 우세 3,038명
- 중단 우세 1,163명
- 2017년 비교 활동 없음 1,692명

화면 상단에 `DEMO`가 표시되므로 프로젝트 데이터와 혼동하지 않는다.

## 고도화 파일

다음 파일이 추가되면 기존 화면을 수정하지 않고 기능이 활성화된다.

```text
data/processed/predictions/reviewer_monthly_activity_v01.parquet
reports/tables/regional_risk_summary_v01.csv
```

정확한 컬럼은 [STREAMLIT_DATA_CONTRACT.md](../../docs/04_architecture_and_guides/STREAMLIT_DATA_CONTRACT.md)를
확인한다.

## 표현 원칙

- 위험 점수는 보정된 이탈 확률이 아니다.
- 실제 이탈 결과는 분석 검증 모드에서만 표시한다.
- 2017년 비교 활동이 없으면 전년도 대비 변화율을 0으로 표시하지 않는다.
- 피처 중요도는 사후 Permutation 해석이며 확률이나 영향 비율이 아니다.
- 지역은 거주지나 생활권이 아닌 대표 리뷰 활동 지역으로 표현한다.
- 데이터가 없는 고도화 기능에는 가짜 수치나 실행 기록을 만들지 않는다.
- CRM 실행 버튼은 실제 연동 데이터가 준비되기 전까지 비활성화한다.

## 빠른 검증

```powershell
python -m unittest discover -s tests -p "test_*.py"
python -m compileall app
```
