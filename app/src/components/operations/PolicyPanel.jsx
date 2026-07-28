function formatPercent(value) {
  return `${(value * 100).toFixed(1)}%`;
}

function PolicyRow({ label, value, good = false }) {
  return (
    <div className="flex items-baseline justify-between border-t border-[#DDE4DF] py-3">
      <span className="text-sm text-[#68736D]">
        {label}
      </span>

      <strong
        className={
          good
            ? "text-lg text-[#137A5A]"
            : "text-lg text-[#17211D]"
        }
      >
        {value}
      </strong>
    </div>
  );
}

function PolicyPanel({ summary }) {
  const liftWidth = Math.min(100, Math.max(5, summary.lift / 2 * 100));

  const recallCeiling = (summary.recallCeiling ?? 0) * 100;

  return (
    <aside className="rounded-xl border border-[#DDE4DF] bg-white p-6">
      <h2 className="text-lg font-bold text-[#17211D]">
        이 큐는 왜 우선인가
      </h2>

      <p className="mt-2 text-sm leading-6 text-[#68736D]">
        사후 Test 검증 결과이며, 무작위로 대상을 선택하는 것보다
        실제 활동 저하 대상을 더 많이 포함합니다.
      </p>

      <div className="mt-5">
        <PolicyRow
          label="검토 용량"
          value={`${summary.targetUsers.toLocaleString()}명`}
        />

        <PolicyRow
          label="상태 상실 포착"
          value={`${summary.capturedUsers.toLocaleString()}명`}
        />

        <PolicyRow
          label="정밀도"
          value={formatPercent(summary.precision)}
          good
        />

        <PolicyRow
          label="재현율"
          value={formatPercent(summary.recall)}
        />

        <p className="mt-1 text-xs leading-5 text-[#68736D]">
          한 번에 20%만 볼 수 있어 최대로 잡아도 {recallCeiling.toFixed(1)}%까지가
          한계입니다
        </p>
      </div>

      <div className="border-t border-[#DDE4DF] py-4">
        <div className="flex items-center justify-between text-sm">
          <span className="text-[#68736D]">
            무작위로 뽑을 때보다
          </span>

          <strong className="text-[#137A5A]">
            {summary.lift.toFixed(2)}배 정확
          </strong>
        </div>

        <div className="relative mt-3 h-1 rounded-full bg-[#F1F4F1]">
          <div
            className="absolute inset-y-0 left-0 rounded-full bg-[#137A5A]"
            style={{ width: `${liftWidth}%` }}
          />

          <div className="absolute inset-y-[-2px] left-1/2 w-[2px] bg-[#B8C0BB]" />
        </div>
      </div>

      <div className="flex justify-between border-t border-[#DDE4DF] pt-4 text-sm text-[#68736D]">
        <span>
          약화 우세 {summary.weakenedUsers.toLocaleString()}명
        </span>

        <span>
          중단 우세 {summary.stoppedUsers.toLocaleString()}명
        </span>
      </div>

      <p className="mt-5 rounded-lg bg-[#F1F4F1] px-4 py-3 text-xs leading-5 text-[#68736D]">
        현재 점수는 이탈 확률이 아니라 누구부터 검토할지를 정하는
        상대적 우선순위 점수입니다.
      </p>
    </aside>
  );
}

export default PolicyPanel;