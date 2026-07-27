import { Link } from "react-router";

import StatusBadge from "./StatusBadge";

function ReviewerTable({ reviewers }) {
  if (reviewers.length === 0) {
    return (
      <div className="rounded-xl bg-[#F1F4F1] px-6 py-10 text-center">
        <h2 className="font-bold text-[#17211D]">
          조건에 해당하는 리뷰어가 없습니다
        </h2>

        <p className="mt-2 text-sm text-[#68736D]">
          검색어나 필터 조건을 변경해 주세요.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-[#DDE4DF] bg-white">
      <div className="min-w-[1000px]">
        <div className="grid grid-cols-[70px_180px_100px_1fr_150px_150px_28px] gap-3 border-b border-[#DDE4DF] px-5 py-3 text-xs font-semibold text-[#68736D]">
          <span>순위</span>
          <span>리뷰어</span>
          <span>모델 판단</span>
          <span>핵심 변화</span>
          <span>위험 유형</span>
          <span>권장 검토</span>
          <span />
        </div>

        {reviewers.map((reviewer) => {
          const isCompleted = Boolean(reviewer.managerDecision);

          return (
            <Link
              key={reviewer.userId}
              to={`/reviewers/${reviewer.userId}`}
              className={[
                "grid grid-cols-[70px_180px_100px_1fr_150px_150px_28px] items-center gap-3 border-b border-[#DDE4DF] px-5 py-4 text-sm transition last:border-b-0 hover:bg-[#F6F8F6]",
                isCompleted
                  ? "border-l-4 border-l-[#137A5A] bg-[#137A5A]/[0.03] pl-4"
                  : "",
              ].join(" ")}
            >
              <span className="w-fit rounded-full bg-[#F1F4F1] px-3 py-1 text-xs text-[#68736D]">
                {reviewer.priorityRank}위
              </span>

              <span className="truncate text-[#68736D]">
                {reviewer.userId}
              </span>

              <StatusBadge judgment={reviewer.modelJudgment} />

              <span className="truncate text-[#68736D]">
                {reviewer.coreChange}
              </span>

              <span className="w-fit rounded bg-[#F1F4F1] px-2 py-1 text-xs text-[#68736D]">
                {reviewer.riskType}
              </span>

              {isCompleted ? (
                <span className="w-fit rounded bg-[#137A5A] px-2 py-1 text-xs font-bold text-white">
                  ✓ {reviewer.managerDecision}
                </span>
              ) : (
                <span className="w-fit rounded bg-[#F1F4F1] px-2 py-1 text-xs text-[#68736D]">
                  {reviewer.recommendedReview}
                </span>
              )}

              <span className="font-bold text-[#137A5A]">
                →
              </span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

export default ReviewerTable;