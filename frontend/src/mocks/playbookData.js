export const playbookData = [
  {
    id: "reactivation",
    title: "복귀·재활성화",
    category: "중단 대응",
    judgments: ["중단 우세"],
    riskTypes: ["복합 위험형", "작성 주기 이완형"],
    summary:
      "장기간 리뷰 활동이 끊긴 리뷰어에게 부담이 적은 복귀 계기를 제공합니다.",
    signals: [
      "최근 리뷰 공백이 길어짐",
      "리뷰 수가 급격하게 감소함",
      "활동 월이 지속적으로 줄어듦",
    ],
    primaryAction: "개인 활동 리포트와 복귀 메시지 제공",
    secondaryActions: [
      "작성 부담이 낮은 짧은 리뷰 유도",
      "과거 관심 음식점 기반 콘텐츠 추천",
      "첫 복귀 활동에 대한 보상 검토",
    ],
    channels: ["앱 내 메시지", "이메일", "개인화 추천"],
    tone: "critical",
  },
  {
    id: "activity-recovery",
    title: "리뷰 활동 회복",
    category: "약화 대응",
    judgments: ["약화 우세"],
    riskTypes: ["활동량 붕괴형", "복합 위험형"],
    summary:
      "활동이 완전히 중단되기 전에 리뷰 작성 빈도와 활동 지속성을 회복시킵니다.",
    signals: [
      "이전보다 리뷰 수가 감소함",
      "활동한 월의 수가 줄어듦",
      "최근 활동이 불규칙해짐",
    ],
    primaryAction: "리뷰 작성 계기와 맞춤형 콘텐츠 제공",
    secondaryActions: [
      "최근 방문 가능성이 높은 음식점 추천",
      "월별 리뷰 활동 목표 제안",
      "활동 회복 진행 상황 안내",
    ],
    channels: ["추천 피드", "앱 내 알림", "활동 리포트"],
    tone: "warning",
  },
  {
    id: "exploration-expansion",
    title: "탐색 범위 회복",
    category: "탐색 대응",
    judgments: ["약화 우세"],
    riskTypes: ["탐색 활동 축소형"],
    summary:
      "새로운 음식점 탐색이 줄어든 리뷰어에게 새로운 방문 후보를 제공합니다.",
    signals: [
      "고유 음식점 수가 감소함",
      "방문 지역이 좁아짐",
      "비슷한 음식점만 반복적으로 리뷰함",
    ],
    primaryAction: "관심 지역의 신규 음식점 큐레이션 제공",
    secondaryActions: [
      "새로운 카테고리 음식점 추천",
      "가까운 지역의 탐색 코스 제안",
      "신규 음식점 리뷰 주제 제공",
    ],
    channels: ["지역 추천", "탐색 피드", "지도 콘텐츠"],
    tone: "watch",
  },
  {
    id: "interval-recovery",
    title: "작성 주기 회복",
    category: "주기 대응",
    judgments: ["약화 우세", "중단 우세"],
    riskTypes: ["작성 주기 이완형"],
    summary:
      "리뷰 작성 간격이 길어진 사용자에게 자연스러운 재작성 시점을 제공합니다.",
    signals: [
      "평균 리뷰 간격이 증가함",
      "마지막 리뷰 공백이 길어짐",
      "월별 리뷰 활동이 간헐적으로 바뀜",
    ],
    primaryAction: "최근 방문 경험을 떠올릴 수 있는 작성 알림 제공",
    secondaryActions: [
      "저장한 음식점 기반 리뷰 요청",
      "간단한 질문 형식의 리뷰 작성 지원",
      "반복 알림 대신 적절한 시점에 한 번 안내",
    ],
    channels: ["앱 내 알림", "저장 목록", "방문 기록"],
    tone: "warning",
  },
  {
    id: "monitoring",
    title: "관찰 유지",
    category: "유지 관리",
    judgments: ["유지 우세"],
    riskTypes: ["일반 모니터링형"],
    summary:
      "현재 활동이 유지되는 리뷰어는 즉시 개입하지 않고 변화 여부를 관찰합니다.",
    signals: [
      "리뷰 활동이 일정하게 유지됨",
      "최근 리뷰 공백이 짧음",
      "활동량의 급격한 감소가 없음",
    ],
    primaryAction: "추가 개입 없이 우선순위 변화 관찰",
    secondaryActions: [
      "정기적으로 위험 점수 재계산",
      "활동량 급감 여부 확인",
      "과도한 메시지 발송 방지",
    ],
    channels: ["운영 모니터링", "정기 리포트"],
    tone: "positive",
  },
];