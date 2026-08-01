import { Link } from "react-router";

// Four stages with deliberately different visual weight: observed evidence
// (neutral), model judgment (outline — reference only), manager decision
// (filled — the actual decision), playbook (active only after a decision
// exists). The point is to make "model informs, person decides" visible at
// a glance, not just say it in a footer.
function DecisionRail({ coreChange, modelJudgment, riskType, savedDecision, reviewerId }) {
  return (
    <div className="rounded-lg border border-[#DDE4DF] bg-white p-4">
      <p className="text-xs text-[#626D67]">
        판단 경로 · 확인 순서이며 인과관계를 의미하지 않습니다
      </p>

      <div className="mt-2 grid grid-cols-[1fr_20px_1fr_20px_1fr_20px_1fr] items-stretch">
        <Stage tone="neutral" label="관찰된 변화" value={coreChange} />
        <Arrow />
        <Stage tone="outline" label="모델 판단 · 참고" value={modelJudgment} />
        <Arrow />
        <Stage
          tone={savedDecision ? "filled" : "pending"}
          label="관리자 판단 · 결정"
          value={savedDecision ?? "미정"}
        />
        <Arrow />
        {savedDecision ? (
          <Link
            to={`/playbook?reviewer=${encodeURIComponent(reviewerId)}`}
            className="flex flex-col justify-center gap-1 rounded-md border border-[#137A5A] bg-[#E3F1EA] p-3 transition hover:bg-[#D5EBE1]"
          >
            <span className="text-[10px] font-medium tracking-wide text-[#137A5A]">
              플레이북
            </span>
            <span className="text-xs font-medium text-[#137A5A]">
              확인하기 →
            </span>
          </Link>
        ) : (
          <div className="flex flex-col justify-center gap-1 rounded-md border border-dashed border-[#DDE4DF] p-3 opacity-60">
            <span className="text-[10px] font-medium tracking-wide text-[#626D67]">
              플레이북
            </span>
            <span className="text-xs text-[#B3BBB6]">판단 후 활성화</span>
          </div>
        )}
      </div>

      <p className="mt-2 text-[11px] text-[#626D67]">
        위험 유형 · {riskType}
      </p>
    </div>
  );
}

function Stage({ tone, label, value }) {
  const styles = {
    neutral: "bg-[#F1F4F1] text-[#17211D]",
    outline: "border border-[#B3BBB6] bg-white text-[#17211D]",
    filled: "bg-[#137A5A] text-white",
    pending: "border border-dashed border-[#DDE4DF] text-[#B3BBB6]",
  };

  const labelStyles = {
    neutral: "text-[#626D67]",
    outline: "text-[#5F6EA6]",
    filled: "text-[#CFE7DC]",
    pending: "text-[#B3BBB6]",
  };

  return (
    <div className={`flex flex-col justify-center gap-1 rounded-md p-3 ${styles[tone]}`}>
      <span className={`text-[10px] font-medium tracking-wide ${labelStyles[tone]}`}>
        {label}
      </span>
      <span className="text-xs font-medium">{value}</span>
    </div>
  );
}

function Arrow() {
  return (
    <div className="flex items-center justify-center text-[#B3BBB6]">→</div>
  );
}

export default DecisionRail;
