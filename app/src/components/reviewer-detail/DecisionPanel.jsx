import { useState } from "react";
import { Link } from "react-router";

const decisionOptions = [
  "리뷰 다시 시작 유도",
  "리뷰 활동 늘리기",
  "변화 지켜보기",
  "이번엔 제외",
];

// Switching reviewers remounts this panel (the detail page is keyed by
// reviewerId), so the initial state below is all the reset it needs — the save
// and cancel handlers keep local state in sync for the reviewer on screen.
function DecisionPanel({
  savedDecision,
  recommendedDecision,
  onSave,
  onCancel,
  previousReviewer,
  nextReviewer,
}) {
  const [selectedDecision, setSelectedDecision] = useState(
    savedDecision ?? "",
  );

  const [message, setMessage] = useState("");

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
        현재 판단은 <strong className="font-semibold">이 브라우저에만</strong>{" "}
        저장됩니다. Streamlit에 저장된 판단과는 별도 저장소이며 서로
        동기화되지 않습니다. 담당자·CRM·감사 이력은 아직 연결되지
        않았습니다.
      </p>

      <div className="mt-4 grid grid-cols-2 gap-3">
        {previousReviewer ? (
          <Link
            to={`/reviewers/${previousReviewer.userId}`}
            className="flex min-h-11 items-center justify-center rounded-lg border border-[#DDE4DF] px-3 text-sm font-bold text-[#137A5A] transition hover:border-[#137A5A] hover:bg-[#E3F1EA]"
          >
            ← 이전 리뷰어
          </Link>
        ) : (
          <span className="flex min-h-11 items-center justify-center rounded-lg border border-[#DDE4DF] px-3 text-sm font-bold text-[#B3BBB6]">
            ← 이전 리뷰어
          </span>
        )}

        {nextReviewer ? (
          <Link
            to={`/reviewers/${nextReviewer.userId}`}
            className="flex min-h-11 items-center justify-center rounded-lg border border-[#DDE4DF] px-3 text-sm font-bold text-[#137A5A] transition hover:border-[#137A5A] hover:bg-[#E3F1EA]"
          >
            다음 리뷰어 →
          </Link>
        ) : (
          <span className="flex min-h-11 items-center justify-center rounded-lg border border-[#DDE4DF] px-3 text-sm font-bold text-[#B3BBB6]">
            다음 리뷰어 →
          </span>
        )}
      </div>
    </div>
  );
}

export default DecisionPanel;