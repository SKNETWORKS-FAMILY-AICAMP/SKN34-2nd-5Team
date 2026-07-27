export const operationsSummary = {
  modelVersion: "v03",
  snapshot: "Test 2019",
  dataMode: "DEMO",

  totalReviewers: 4157,
  targetUsers: 832,
  completedUsers: 0,

  capturedUsers: 773,
  precision: 0.9291,
  recall: 0.2953,
  lift: 1.4753,

  weakenedUsers: 1757,
  stoppedUsers: 1000,
};

export const priorityReviewers = [
  {
    rank: 1,
    userId: "demo_reviewer_00001",
    modelJudgment: "중단 우세",
    changeText: "리뷰 수 35건 → 4건 · 88.6% 감소",
    action: "복귀·재활성화 검토",
  },
  {
    rank: 2,
    userId: "demo_reviewer_00002",
    modelJudgment: "중단 우세",
    changeText: "리뷰 수 27건 → 3건 · 88.9% 감소",
    action: "복귀·재활성화 검토",
  },
  {
    rank: 3,
    userId: "demo_reviewer_00003",
    modelJudgment: "약화 우세",
    changeText: "리뷰 수 22건 → 8건 · 63.6% 감소",
    action: "활동 회복 검토",
  },
  {
    rank: 4,
    userId: "demo_reviewer_00004",
    modelJudgment: "약화 우세",
    changeText: "활동 월 9개월 → 4개월 · 55.6% 감소",
    action: "활동 회복 검토",
  },
  {
    rank: 5,
    userId: "demo_reviewer_00005",
    modelJudgment: "중단 우세",
    changeText: "최근 리뷰 공백 184일",
    action: "복귀·재활성화 검토",
  },
];