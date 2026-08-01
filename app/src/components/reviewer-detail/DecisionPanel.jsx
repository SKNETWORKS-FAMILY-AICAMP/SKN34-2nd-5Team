import { useEffect, useState } from "react";
import { Link } from "react-router";

import { createInteraction, loadInteractions } from "../../services/decisionService";

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
  reviewer,
  modelVersion,
  savedRecord,
  recommendedDecision,
  onSave,
  onCancel,
  previousReviewer,
  nextReviewer,
}) {
  const [selectedDecision, setSelectedDecision] = useState(
    savedRecord?.decision ?? "",
  );
  const [note, setNote] = useState(savedRecord?.note ?? "");
  const [snoozeUntil, setSnoozeUntil] = useState(
    savedRecord?.snoozeUntil?.slice(0, 16) ?? "",
  );
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const [interactions, setInteractions] = useState([]);
  const [interactionChannel, setInteractionChannel] = useState("app");
  const [interactionNote, setInteractionNote] = useState("");
  const [interactionSaving, setInteractionSaving] = useState(false);

  useEffect(() => {
    let active = true;
    loadInteractions(reviewer.userId)
      .then(({ items }) => {
        if (active) setInteractions(items);
      })
      .catch(() => {
        if (active) setInteractions([]);
      });
    return () => {
      active = false;
    };
  }, [reviewer.userId]);

  async function handleSubmit(event) {
    event.preventDefault();

    if (!selectedDecision) {
      setMessage("검토 결과를 먼저 선택하세요.");
      return;
    }

    setSaving(true);
    try {
      await onSave({
        decision: selectedDecision,
        note: note.trim() || null,
        snoozeUntil: snoozeUntil || null,
      });
      setMessage(`${selectedDecision}으로 서버에 저장했습니다.`);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleCancel() {
    setSaving(true);
    try {
      await onCancel();
      setSelectedDecision("");
      setNote("");
      setSnoozeUntil("");
      setMessage("판단을 삭제하고 감사 이력을 남겼습니다.");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleInteraction(event) {
    event.preventDefault();
    setInteractionSaving(true);
    try {
      const saved = await createInteraction(reviewer.userId, {
        modelVersion,
        sampleId: reviewer.sampleId,
        channel: interactionChannel,
        contactedAt: new Date().toISOString(),
        note: interactionNote.trim() || null,
      });
      setInteractions((current) => [saved, ...current]);
      setInteractionNote("");
      setMessage("접촉 이력을 저장했습니다.");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setInteractionSaving(false);
    }
  }

  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-5">
      <div>
        <h2 className="text-lg font-bold text-[#17211D]">
          관리자 판단
        </h2>

        <p className="mt-2 text-sm leading-6 text-[#626D67]">
          모델 판단과 활동 근거를 확인한 뒤 운영 결과를
          분류합니다.
        </p>
      </div>

      <div className="mt-4">
        {savedRecord ? (
          <div className="flex items-center justify-between gap-3">
            <span className="rounded-full bg-[#E3F1EA] px-3 py-1 text-xs font-bold text-[#137A5A]">
              판단 완료 · {savedRecord.decision}
            </span>

            <button
              type="button"
              onClick={handleCancel}
              disabled={saving}
              className="text-xs font-bold text-[#626D67] hover:text-[#BF3620]"
            >
              취소
            </button>
          </div>
        ) : (
          <span className="rounded-full bg-[#F1F4F1] px-3 py-1 text-xs text-[#626D67]">
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

        <label className="block pt-2 text-xs font-medium text-[#626D67]">
          판단 메모
          <textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            rows={3}
            maxLength={5000}
            placeholder="판단 근거나 후속 확인 사항을 남기세요"
            className="mt-1.5 w-full resize-y rounded-lg border border-[#DDE4DF] bg-white px-3 py-2 text-sm text-[#17211D] outline-none focus:border-[#137A5A]"
          />
        </label>

        <label className="block text-xs font-medium text-[#626D67]">
          재검토 시점(스누즈)
          <input
            type="datetime-local"
            value={snoozeUntil}
            onChange={(event) => setSnoozeUntil(event.target.value)}
            className="mt-1.5 min-h-10 w-full rounded-lg border border-[#DDE4DF] bg-white px-3 text-sm text-[#17211D] outline-none focus:border-[#137A5A]"
          />
        </label>

        <button
          type="submit"
          disabled={saving}
          className="mt-4 min-h-11 w-full rounded-lg bg-[#137A5A] px-5 font-bold text-white transition hover:bg-[#185C46]"
        >
          {saving ? "저장 중…" : "관리자 판단 저장"}
        </button>
      </form>

      {message && (
        <p className="mt-3 text-xs font-semibold text-[#137A5A]">
          {message}
        </p>
      )}

      <p className="mt-5 border-t border-[#DDE4DF] pt-4 text-xs leading-5 text-[#626D67]">
        판단·메모·스누즈와 변경 이력은 서버에 저장됩니다. 담당자 선택은
        로그인 사용자 목록 연동 후 활성화됩니다.
      </p>

      <form onSubmit={handleInteraction} className="mt-4 rounded-lg bg-[#F7F8F5] p-3">
        <p className="text-xs font-medium text-[#17211D]">접촉 이력</p>
        <div className="mt-2 flex gap-2">
          <select
            value={interactionChannel}
            onChange={(event) => setInteractionChannel(event.target.value)}
            className="min-h-9 rounded border border-[#DDE4DF] bg-white px-2 text-xs"
          >
            <option value="app">앱 메시지</option>
            <option value="email">이메일</option>
            <option value="push">푸시</option>
            <option value="phone">전화</option>
            <option value="other">기타</option>
          </select>
          <input
            value={interactionNote}
            onChange={(event) => setInteractionNote(event.target.value)}
            maxLength={5000}
            placeholder="접촉 내용 또는 결과"
            className="min-h-9 min-w-0 flex-1 rounded border border-[#DDE4DF] bg-white px-2 text-xs"
          />
          <button
            type="submit"
            disabled={interactionSaving}
            className="min-h-9 rounded bg-[#17211D] px-3 text-xs font-medium text-white disabled:opacity-50"
          >
            기록
          </button>
        </div>
        {interactions.length > 0 && (
          <ul className="mt-2 space-y-1 text-[11px] text-[#626D67]">
            {interactions.slice(0, 3).map((item) => (
              <li key={item.interactionId}>
                {new Date(item.contactedAt).toLocaleString("ko-KR")} · {item.channel}
                {item.note ? ` · ${item.note}` : ""}
              </li>
            ))}
          </ul>
        )}
      </form>

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
