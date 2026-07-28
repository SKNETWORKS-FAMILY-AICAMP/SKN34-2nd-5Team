const scoreItems = [
  {
    key: "retained",
    label: "유지",
    color: "bg-[#137A5A]",
  },
  {
    key: "weakened",
    label: "약화",
    color: "bg-[#D48A43]",
  },
  {
    key: "stopped",
    label: "중단",
    color: "bg-[#E15D47]",
  },
];

function ReviewerScoreBars({ scores }) {
  return (
    <div className="mt-6 space-y-3 border-t border-[#DDE4DF] pt-5">
      {scoreItems.map((item) => {
        const value = Number(scores[item.key] ?? 0);
        const width = Math.max(2, value * 100);

        return (
          <div
            key={item.key}
            className="grid grid-cols-[55px_1fr_55px] items-center gap-3 text-sm"
          >
            <span className="text-[#68736D]">
              {item.label}
            </span>

            <div className="h-2 overflow-hidden rounded-full bg-[#F1F4F1]">
              <div
                className={`h-full rounded-full ${item.color}`}
                style={{ width: `${width}%` }}
              />
            </div>

            <strong className="text-right text-[#17211D]">
              {value.toFixed(3)}
            </strong>
          </div>
        );
      })}

      <p className="text-xs leading-5 text-[#68736D]">
        클래스 점수는 보정된 이탈 확률이 아니라 모델 간 상대
        비교를 위한 점수입니다.
      </p>
    </div>
  );
}

export default ReviewerScoreBars;