import { Link } from "react-router";

function getJudgmentStyle(modelJudgment) {
  if (modelJudgment.includes("중단")) {
    return {
      rank: "bg-[#E15D47]",
      badge: "bg-[#F7E8E5] text-[#BF3620]",
    };
  }

  if (modelJudgment.includes("약화")) {
    return {
      rank: "bg-[#A66A18]",
      badge: "bg-[#FAEFD9] text-[#A66A18]",
    };
  }

  return {
    rank: "bg-[#137A5A]",
    badge: "bg-[#E3F1EA] text-[#137A5A]",
  };
}

function PriorityQueue({ reviewers }) {
  return (
    <div className="overflow-hidden rounded-xl border border-[#DDE4DF] bg-white">
      {reviewers.map((reviewer) => {
        const style = getJudgmentStyle(reviewer.modelJudgment);

        const isTopRank = reviewer.rank <= 2;

        return (
          <Link
            key={reviewer.userId}
            to={`/reviewers/${reviewer.userId}`}
            className="grid gap-3 border-b border-[#DDE4DF] px-5 py-4 transition last:border-b-0 hover:bg-[#F6F8F6] md:grid-cols-[40px_1.1fr_110px_1.5fr_1fr_24px] md:items-center"
          >
            <span
              className={[
                "flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold text-white",
                style.rank,
                isTopRank ? "ring-2 ring-offset-1 ring-[#17211D]/20" : "opacity-80",
              ].join(" ")}
            >
              {reviewer.rank}
            </span>

            <span
              className="truncate text-sm font-semibold text-[#17211D]"
              title={reviewer.userId}
            >
              {reviewer.userId}
            </span>

            <span
              className={`w-fit rounded px-2 py-1 text-xs font-bold ${style.badge}`}
            >
              {reviewer.modelJudgment}
            </span>

            <span className="text-sm text-[#626D67]">
              {reviewer.changeText}
            </span>

            <span className="text-sm text-[#17211D]">
              {reviewer.action}
            </span>

            <span className="text-right font-bold text-[#137A5A]">
              →
            </span>
          </Link>
        );
      })}
    </div>
  );
}

export default PriorityQueue;