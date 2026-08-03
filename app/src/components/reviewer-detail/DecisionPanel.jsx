import { useEffect, useState } from "react";
import { Link } from "react-router";
import { createInteraction, loadInteractions } from "../../services/decisionService";
import { useAuth } from "../../features/auth/auth-context";
import { canMutate } from "../../features/auth/rolePolicy";

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
  interventionHref,
  onSave,
  onCancel,
}) {
  const { user } = useAuth();
  const writable = canMutate(user?.access_role);
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
    <div className="overflow-hidden rounded-xl border border-[#AFCDBE] bg-white p-4 shadow-[0_8px_24px_rgba(23,33,29,0.07)]">
      <div className="flex items-start justify-between gap-3 border-b border-[#E2E7E3] pb-3">
        <div>
        <p className="text-[9px] font-black tracking-[0.14em] text-[#137A5A]">MANAGER DECISION</p>
        <h2 className="mt-0.5 text-base font-black text-[#17211D]">
          관리자 판단
        </h2>
        </div>
        <span className="rounded-full bg-[#F1F4F1] px-2.5 py-1 text-[10px] font-bold text-[#626D67]">근거 검토·판단</span>
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
        className="mt-4"
      >
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
        {decisionOptions.map((option) => (
          <label
            key={option}
            className={[
              "flex min-h-10 cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-xs transition",
              selectedDecision === option
                ? "border-[#075C45] bg-[#E3F1EA] font-bold text-[#075C45]"
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
              className="accent-[#075C45]"
            />

            <span>{option}</span>
          </label>
        ))}
        </div>

        <label className="mt-3 block text-xs font-medium text-[#626D67]">
          판단 메모
          <textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            rows={2}
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
          disabled={saving || !writable}
          className="mt-3 min-h-11 w-full rounded-xl bg-[#075C45] px-5 text-sm font-black text-white transition hover:bg-[#064936]"
        >
          {saving ? "저장 중…" : writable ? "관리자 판단 저장" : "조회 전용"}
        </button>

        <div className="mt-2 min-h-11">
          {savedRecord ? (
            <Link
              to={interventionHref}
              className="flex min-h-11 w-full items-center justify-center rounded-xl border border-[#075C45] bg-white px-5 text-sm font-black text-[#075C45] transition hover:bg-[#F0F7F3]"
            >
              개인 개입안 확인 →
            </Link>
          ) : (
            <p className="flex min-h-11 items-center justify-center rounded-xl bg-[#F4F6F4] px-4 text-center text-[10px] font-bold text-[#718078]">
              판단 저장 후 개인 개입안을 확인할 수 있습니다.
            </p>
          )}
        </div>
      </form>

      <p className="mt-3 min-h-4 text-xs font-semibold text-[#137A5A]">
        {message || "\u00a0"}
      </p>

      <p className="mt-3 border-t border-[#DDE4DF] pt-3 text-[10px] leading-4 text-[#626D67]">
        판단·메모·스누즈와 변경 이력은 서버에 저장됩니다. 담당자 선택은
        로그인 사용자 목록 연동 후 활성화됩니다.
      </p>

      <details className="mt-3 rounded-lg border border-[#E3E8E4] bg-[#F7F8F5] p-3">
        <summary className="cursor-pointer text-xs font-bold text-[#17211D]">접촉 이력 · {interactions.length}건</summary>
      <form onSubmit={handleInteraction} className="mt-3">
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
            disabled={interactionSaving || !writable}
            className="min-h-9 rounded bg-[#17211D] px-3 text-xs font-medium text-white disabled:opacity-50"
          >
            {writable ? "기록" : "조회"}
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
      </details>

      <div className="mt-3 rounded-lg border border-[#DDE4DF] bg-[#F7F9F7] p-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-[10px] font-black tracking-[0.1em] text-[#137A5A]">운영안 미리보기</p>
          <span className="text-[10px] text-[#626D67]">판단 저장 후 4단계에서 확정</span>
        </div>
        <p className="mt-2 text-xs font-bold text-[#17211D]">{selectedDecision || recommendedDecision}</p>
        <div className="mt-2 flex flex-wrap gap-1.5 text-[9px] font-bold text-[#4F5D56]">
          <span className="rounded-full border border-[#C7D8CF] bg-white px-2 py-1">개입 대상 확인</span>
          <span className="rounded-full border border-[#C7D8CF] bg-white px-2 py-1">메시지·혜택 설계</span>
          <span className="rounded-full border border-[#C7D8CF] bg-white px-2 py-1">30·60·90일 추적</span>
        </div>
      </div>
    </div>
  );
}

export default DecisionPanel;
