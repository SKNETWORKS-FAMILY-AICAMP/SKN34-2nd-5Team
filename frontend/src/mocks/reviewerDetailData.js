function getScoreSet(modelJudgment) {
  if (modelJudgment.includes("중단")) {
    return {
      retained: 0.08,
      weakened: 0.24,
      stopped: 0.68,
    };
  }

  if (modelJudgment.includes("약화")) {
    return {
      retained: 0.18,
      weakened: 0.62,
      stopped: 0.2,
    };
  }

  return {
    retained: 0.67,
    weakened: 0.22,
    stopped: 0.11,
  };
}

function getDeclineRate(modelJudgment) {
  if (modelJudgment.includes("중단")) {
    return 0.78;
  }

  if (modelJudgment.includes("약화")) {
    return 0.47;
  }

  return 0.08;
}

function getStrategy(reviewer) {
  if (reviewer.modelJudgment.includes("중단")) {
    return {
      title: "복귀·재활성화 검토",
      description:
        "리뷰 활동 중단 점수가 우세합니다. 장기 공백과 최근 활동을 확인한 뒤 복귀 전략을 검토합니다.",
      secondary: "개인 활동 리포트와 저부담 리뷰 작성 계기 제공",
      channel: "운영자 검토 · 앱 내 메시지",
    };
  }

  if (reviewer.modelJudgment.includes("약화")) {
    return {
      title: "활동 회복 검토",
      description:
        "파워 지위 약화 점수가 우세합니다. 활동 지속성을 회복할 수 있는 개입을 검토합니다.",
      secondary: "탐색 콘텐츠 또는 리뷰 작성 계기 제공",
      channel: "추천 피드 · 앱 내 메시지",
    };
  }

  return {
    title: "관찰 유지",
    description:
      "유지 점수가 우세합니다. 급격한 행동 변화가 추가로 나타나는지만 확인합니다.",
    secondary: "추가 개입 없이 우선순위 변화 관찰",
    channel: "즉시 실행 채널 없음",
  };
}

function getActualState(reviewer) {
  if ([1, 2, 5, 9, 12].includes(reviewer.priorityRank)) {
    return "리뷰 활동 중단";
  }

  if ([3, 4, 6, 8, 11].includes(reviewer.priorityRank)) {
    return "파워 지위 약화";
  }

  return "파워 지위 유지";
}

function buildMonthlyActivity(reviewer) {
  const months = [
    "1월",
    "2월",
    "3월",
    "4월",
    "5월",
    "6월",
    "7월",
    "8월",
    "9월",
    "10월",
    "11월",
    "12월",
  ];

  let declineRate = 0.08;

  if (reviewer.modelJudgment.includes("중단")) {
    declineRate = 0.7;
  } else if (reviewer.modelJudgment.includes("약화")) {
    declineRate = 0.42;
  }

  const baseReviewCount =
    7 + (reviewer.priorityRank % 3);

  const monthlyVariation = [
    0,
    1,
    0,
    -1,
    1,
    0,
    -1,
    0,
    1,
    -1,
    0,
    -1,
  ];

  return months.map((month, index) => {
    const progress = index / (months.length - 1);

    const reviewCount = Math.max(
      0,
      Math.round(
        baseReviewCount *
          (1 - declineRate * progress) +
          monthlyVariation[index],
      ),
    );

    return {
      month,
      reviewCount,
    };
  });
}

export function buildReviewerDetail(reviewer) {
  const declineRate = getDeclineRate(reviewer.modelJudgment);
  const scores = getScoreSet(reviewer.modelJudgment);

  const baselineReviewCount = 28 + reviewer.priorityRank;
  const recentReviewCount = Math.max(
    1,
    Math.round(baselineReviewCount * (1 - declineRate)),
  );

  const baselineActiveMonths = 10;
  const recentActiveMonths = Math.max(
    1,
    Math.round(baselineActiveMonths * (1 - declineRate * 0.75)),
  );

  const baselineBusinessCount = 23 + (reviewer.priorityRank % 4);
  const recentBusinessCount = Math.max(
    1,
    Math.round(baselineBusinessCount * (1 - declineRate * 0.82)),
  );

  const baselineRecencyDays = 21 + reviewer.priorityRank;
  const recentRecencyDays =
    reviewer.recentRecencyDays ??
    Math.round(baselineRecencyDays + declineRate * 180);

  const recencyIncreaseDays =
    recentRecencyDays - baselineRecencyDays;

  const baselineMeanIntervalDays = 14 + (reviewer.priorityRank % 5);
  const recentMeanIntervalDays = Math.round(
    baselineMeanIntervalDays + declineRate * 48,
  );

  const reviewDeclinePercent = Math.round(
    (1 - recentReviewCount / baselineReviewCount) * 100,
  );

  const activeMonthDeclinePercent = Math.round(
    (1 - recentActiveMonths / baselineActiveMonths) * 100,
  );

  const businessDeclinePercent = Math.round(
    (1 - recentBusinessCount / baselineBusinessCount) * 100,
  );

  const strategy = getStrategy(reviewer);

  return {
    ...reviewer,

    totalReviewers: 4157,
    selectionYear: 2017,
    observationYear: 2018,
    targetYear: 2019,

    scores,

    metrics: {
      baselineReviewCount,
      recentReviewCount,
      baselineActiveMonths,
      recentActiveMonths,
      baselineBusinessCount,
      recentBusinessCount,
      baselineRecencyDays,
      recentRecencyDays,
      baselineMeanIntervalDays,
      recentMeanIntervalDays,
    },

    monthlyActivity: buildMonthlyActivity(reviewer),

    intervalComparison: [
      {
        label: "평균 작성 간격",
        before: baselineMeanIntervalDays,
        after: recentMeanIntervalDays,
      },
      {
        label: "마지막 리뷰 공백",
        before: baselineRecencyDays,
        after: recentRecencyDays,
      },
    ],

    changes: [
      {
        label: "리뷰 수",
        before: `${baselineReviewCount}건`,
        after: `${recentReviewCount}건`,
        delta: `${reviewDeclinePercent}% 감소`,
        tone: reviewDeclinePercent >= 20 ? "warning" : "positive",
      },
      {
        label: "활동 월",
        before: `${baselineActiveMonths}개월`,
        after: `${recentActiveMonths}개월`,
        delta: `${activeMonthDeclinePercent}% 감소`,
        tone:
          activeMonthDeclinePercent >= 20
            ? "warning"
            : "positive",
      },
      {
        label: "고유 음식점",
        before: `${baselineBusinessCount}곳`,
        after: `${recentBusinessCount}곳`,
        delta: `${businessDeclinePercent}% 감소`,
        tone:
          businessDeclinePercent >= 20
            ? "warning"
            : "positive",
      },
      {
        label: "리뷰 공백",
        before: `${baselineRecencyDays}일`,
        after: `${recentRecencyDays}일`,
        delta: `+${recencyIncreaseDays}일`,
        tone: recencyIncreaseDays > 20 ? "warning" : "positive",
      },
    ],

    evidence: [
      {
        title: "최근 활동 지속성",
        evidence: `최근 활동 ${recentActiveMonths}개월 · 이전 ${baselineActiveMonths}개월`,
        group: "활동량",
      },
      {
        title: "리뷰 생산량",
        evidence: `최근 ${recentReviewCount}건 · 이전 대비 ${reviewDeclinePercent}% 감소`,
        group: "활동량",
      },
      {
        title: "마지막 리뷰 공백",
        evidence: `최근 공백 ${recentRecencyDays}일 · 이전보다 ${recencyIncreaseDays}일 증가`,
        group: "작성 간격",
      },
      {
        title: "음식점 탐색량",
        evidence: `고유 음식점 수 ${businessDeclinePercent}% 감소`,
        group: "음식점 탐색",
      },
    ],

    strategy,

    actual: {
      state: getActualState(reviewer),
      targetReviewCount: Math.max(
        0,
        Math.round(recentReviewCount * 0.5),
      ),
      targetActiveMonths: Math.max(
        0,
        Math.round(recentActiveMonths * 0.6),
      ),
    },
  };
}