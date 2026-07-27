export const trustSummary = {
  modelVersion: "v03",
  validationPeriod: "Test 2019",
  dataMode: "DEMO",

  totalReviewers: 4157,
  selectedReviewers: 832,
  capturedReviewers: 773,

  precision: 0.9291,
  recall: 0.2953,
  lift: 1.4753,
  selectionRate: 0.2,
};

export const modelPerformanceData = [
  {
    model: "Baseline",
    precision: 0.63,
    recall: 0.24,
    f1Score: 0.35,
    lift: 1.0,
  },
  {
    model: "Logistic",
    precision: 0.79,
    recall: 0.27,
    f1Score: 0.4,
    lift: 1.24,
  },
  {
    model: "Random Forest",
    precision: 0.87,
    recall: 0.29,
    f1Score: 0.44,
    lift: 1.38,
  },
  {
    model: "Selected Model",
    precision: 0.9291,
    recall: 0.2953,
    f1Score: 0.448,
    lift: 1.4753,
  },
];

export const validationChecks = [
  {
    id: "time-split",
    title: "시간 분리 검증",
    description:
      "과거 관찰 기간으로 피처를 만들고 이후 기간의 활동 상태를 검증합니다.",
    status: "완료",
  },
  {
    id: "leakage",
    title: "미래 정보 누수 점검",
    description:
      "타깃 기간 이후에 생성된 정보가 모델 입력에 포함되지 않도록 확인합니다.",
    status: "완료",
  },
  {
    id: "class-balance",
    title: "클래스 불균형 평가",
    description:
      "정확도만 사용하지 않고 정밀도, 재현율, F1, Lift를 함께 확인합니다.",
    status: "완료",
  },
  {
    id: "probability-calibration",
    title: "확률 보정",
    description:
      "현재 클래스 점수는 운영 우선순위이며 실제 이탈 확률로 보정되지 않았습니다.",
    status: "진행 예정",
  },
  {
    id: "external-validation",
    title: "외부 기간 검증",
    description:
      "다른 연도 또는 다른 지역에서도 동일한 성능이 유지되는지 검증해야 합니다.",
    status: "진행 예정",
  },
  {
    id: "ab-test",
    title: "개입 효과 실험",
    description:
      "플레이북 실행 후 리뷰 활동이 실제로 회복되는지 비교 실험이 필요합니다.",
    status: "진행 예정",
  },
];

export const featureGroups = [
  {
    title: "활동량",
    features: [
      "관찰 기간 리뷰 수",
      "최근 리뷰 수 변화율",
      "활동 월 수",
      "월별 리뷰 수 변동",
    ],
  },
  {
    title: "작성 간격",
    features: [
      "평균 리뷰 작성 간격",
      "마지막 리뷰 이후 경과일",
      "리뷰 간격 증가율",
    ],
  },
  {
    title: "음식점 탐색",
    features: [
      "고유 음식점 수",
      "신규 음식점 비율",
      "카테고리 다양성",
      "방문 지역 수",
    ],
  },
  {
    title: "반응과 품질",
    features: [
      "평균 별점 변화",
      "Useful 반응 변화",
      "Funny·Cool 반응 변화",
    ],
  },
];

export const roadmapData = [
  {
    stage: 1,
    title: "데이터·라벨 정의",
    description:
      "파워 리뷰어 기준, 관찰 기간, 예측 기간과 활동 중단 기준을 확정합니다.",
    status: "완료",
  },
  {
    stage: 2,
    title: "Streamlit 프로토타입",
    description:
      "운영 홈, 워크리스트, Reviewer 360과 신뢰 화면을 구현합니다.",
    status: "완료",
  },
  {
    stage: 3,
    title: "React 프론트엔드",
    description:
      "운영 화면을 컴포넌트 기반 React 구조로 전환합니다.",
    status: "진행 중",
  },
  {
    stage: 4,
    title: "FastAPI 연결",
    description:
      "React 화면에서 실제 리뷰어 데이터와 모델 결과를 API로 조회합니다.",
    status: "예정",
  },
  {
    stage: 5,
    title: "MySQL 운영 저장소",
    description:
      "관리자 판단, 검토 이력과 사용자 상태를 데이터베이스에 저장합니다.",
    status: "예정",
  },
  {
    stage: 6,
    title: "효과 검증과 배포",
    description:
      "개입 효과를 검증하고 인증, 모니터링과 배포 환경을 구성합니다.",
    status: "예정",
  },
];