# Yelp Power Reviewer Analytics Prototype

파워 리뷰어의 리뷰 활동 루틴과 이탈 가설을 탐색하는 Streamlit 분석 프로토타입입니다. 모델 예측 앱이 아니라, 데이터 검증 결과를 팀과 공유하기 위한 분석 화면입니다.

## 프로젝트에 적용

압축을 푼 뒤 `app/`, `.streamlit/`, `requirements.txt`, `run_app.bat`을 기존 `SKN34-2nd-5Team` 프로젝트 최상위에 복사합니다.

```text
SKN34-2nd-5Team/
├── .streamlit/
├── app/
├── configs/
├── data/
├── requirements.txt
└── reports/
```

프로젝트 가상환경에서 실행합니다.

```bash
pip install -r requirements.txt
streamlit run app/Home.py
```

Windows에서는 가상환경을 활성화한 상태로 `run_app.bat`을 더블클릭해도 됩니다.

## 자동으로 읽는 파일

- `data/interim/power_reviewer_cohort_v01.parquet`
- `data/interim/cohort_observation_reviews_v01.parquet`
- `data/interim/features/*_features_v01.parquet`
- `reports/tables/feature_feasibility_decisions_v01.csv`

실제 파일을 찾지 못하면 UI 확인용 데모 모드로 실행됩니다. 화면 상단에 `DEMO DATA`가 표시되면 경로 또는 파일명을 확인하세요.

## 화면

1. 홈: 프로젝트 핵심 수치와 검증 결론
2. 코호트 개요: 파워 리뷰어 선정 구조와 이탈 분포
3. 핵심 이탈 신호: 활동량·작성 주기·평점 비교
4. 가설 검증실: 채택·보조·제외 피처와 근거
5. 리뷰어 탐색기: 익명 사용자별 월간 추세와 활동 지도

## 주의

- `churn`은 2019년 실제 결과이며 모델 입력값이 아닙니다.
- `target_review_count`, `target_active_months`는 화면의 모델 입력 후보에서 제외합니다.
- `useful`, `cool`, `funny`는 반응 발생 시점을 알 수 없어 예측 피처로 사용하지 않습니다.
