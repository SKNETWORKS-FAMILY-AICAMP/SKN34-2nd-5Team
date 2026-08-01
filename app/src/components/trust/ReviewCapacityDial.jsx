import { useState } from "react";

function percent(value, digits = 1) {
  return `${(value * 100).toFixed(digits)}%`;
}

// Walks the real topK evaluation points (not a recomputation) so an
// operator can see why 20% is the policy — a slider over stored evidence,
// not a live simulation of a different model.
function ReviewCapacityDial({ topK, currentTargetRate }) {
  const currentIndex = topK.findIndex(
    (point) => Math.abs(point.targetRate - currentTargetRate) < 0.001,
  );
  const [index, setIndex] = useState(currentIndex >= 0 ? currentIndex : 0);
  const point = topK[index];

  return (
    <div className="rounded-lg border border-[#137A5A] bg-white p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-medium text-[#137A5A]">
          검토 용량 다이얼 · 왜 상위 {percent(currentTargetRate, 0)}인가
        </p>
        <span className="rounded bg-[#F1F4F1] px-2 py-0.5 text-[10px] text-[#626D67]">
          시뮬레이션 · 저장된 평가 지점 기준, 정책을 바꾸지 않습니다
        </span>
      </div>

      <input
        type="range"
        min={0}
        max={topK.length - 1}
        step={1}
        value={index}
        onChange={(event) => setIndex(Number(event.target.value))}
        className="mt-5 w-full accent-[#137A5A]"
      />

      <div className="mt-1 flex justify-between text-[10px] text-[#626D67]">
        {topK.map((p, i) => (
          <span
            key={p.targetRate}
            className={i === index ? "font-medium text-[#137A5A]" : ""}
          >
            {percent(p.targetRate, 0)}
            {i === currentIndex ? " · 정책" : ""}
          </span>
        ))}
      </div>

      <div className="mt-5 grid grid-cols-5 gap-3">
        <Metric label="검토 대상" value={`${point.targetUsers.toLocaleString()}명`} />
        <Metric label="지위 상실 포착" value={`${point.captured.toLocaleString()}명`} good />
        <Metric label="정밀도" value={percent(point.precision)} />
        <Metric label="재현율" value={percent(point.recall)} />
        <Metric label="Lift" value={`${point.lift.toFixed(2)}배`} />
      </div>

      <p className="mt-3 text-xs leading-5 text-[#626D67]">
        클래스 점수는 보정 확률이 아닙니다. 슬라이더는 실제 운영팀 검토
        용량 범위에서만 탐색합니다.
      </p>
    </div>
  );
}

function Metric({ label, value, good = false }) {
  return (
    <div>
      <p className="text-[11px] text-[#626D67]">{label}</p>
      <p className={`mt-0.5 text-base font-medium ${good ? "text-[#137A5A]" : "text-[#17211D]"}`}>
        {value}
      </p>
    </div>
  );
}

export default ReviewCapacityDial;
