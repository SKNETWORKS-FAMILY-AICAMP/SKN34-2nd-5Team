import { useEffect, useState } from "react";

const decisionOptions = [
  "리뷰 다시 시작 유도",
  "리뷰 활동 늘리기",
  "변화 지켜보기",
  "이번엔 제외",
];

function DecisionPanel({
  savedDecision,
  recommendedDecision,
  onSave,
  onCancel,
}) {
  const [selectedDecision, setSelectedDecision] = useState(
    savedDecision ?? "",
  );

  const [message, setMessage] = useState("");

  useEffect(() => {
    setSelectedDecision(savedDecision ?? "");
    setMessage("");
  }, [savedDecision]);

  function handleSubmit(event) {
    event.preventDefault();

    if (!selectedDecision) {
      setMessage("검토 결과를 먼저 선택하세요.");
      return;
    }

    onSave(selectedDecision);
    setMessage(`${selectedDecision}으로 저장했습니다.`);
  }

  function handleCancel() {
    onCancel();
    setSelectedDecision("");
    setMessage("저장된 판단을 취소했습니다.");
  }

  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-5">
      <div>
        <h2 className="text-lg font-bold text-[#17211D]">
          관리자 판단
        </h2>

        <p className="mt-2 text-sm leading-6 text-[#68736D]">
          모델 판단과 활동 근거를 확인한 뒤 운영 결과를
          분류합니다.
        </p>
      </div>

      <div className="mt-4">
        {savedDecision ? (
          <div className="flex items-center justify-between gap-3">
            <span className="rounded-full bg-[#E3F1EA] px-3 py-1 text-xs font-bold text-[#137A5A]">
              판단 완료 · {savedDecision}
            </span>

            <button
              type="button"
              onClick={handleCancel}
              className="text-xs font-bold text-[#68736D] hover:text-[#E15D47]"
            >
              취소
            </button>
          </div>
        ) : (
          <span className="rounded-full bg-[#F1F4F1] px-3 py-1 text-xs text-[#68736D]">
            아직 판단 전 · 모델 추천 {recommendedDecision}
          </span>
        )}
      </div>

      <form
        onSubmit={handleSubmit}
        className="mt-5 space-y-2"
      >
        {decisionOptions.map((option) => (
          <label
            key={option}
            className={[
              "flex cursor-pointer items-center gap-3 rounded-lg border px-4 py-3 text-sm transition",
              selectedDecision === option
                ? "border-[#137A5A] bg-[#E3F1EA]"
                : "border-[#DDE4DF] hover:bg-[#F6F8F6]",
            ].join(" ")}
          >
            <input
              type="radio"
              name="manager-decision"
              value={option}
              checked={selectedDecision === option}
              onChange={(event) =>
                setSelectedDecision(event.target.value)
              }
              className="accent-[#137A5A]"
            />

            <span>{option}</span>
          </label>
        ))}

        <button
          type="submit"
          className="mt-4 min-h-11 w-full rounded-lg bg-[#137A5A] px-5 font-bold text-white transition hover:bg-[#185C46]"
        >
          관리자 판단 저장
        </button>
      </form>

      {message && (
        <p className="mt-3 text-xs font-semibold text-[#137A5A]">
          {message}
        </p>
      )}

      <p className="mt-5 border-t border-[#DDE4DF] pt-4 text-xs leading-5 text-[#68736D]">
        현재 판단은 React 화면 기능 검증을 위해 브라우저에
        저장됩니다. 담당자·CRM·감사 이력은 아직 연결되지
        않았습니다.
      </p>
    </div>
  );
}

export default DecisionPanel;