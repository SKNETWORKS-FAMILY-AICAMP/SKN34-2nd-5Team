function EvidenceList({ evidence, hoveredGroup, onHoverGroup }) {
  return (
    <div className="overflow-hidden rounded-xl border border-[#DDE4DF] bg-white">
      {evidence.map((item, index) => (
        <div
          key={item.title}
          onMouseEnter={() => onHoverGroup?.(item.group)}
          onMouseLeave={() => onHoverGroup?.(null)}
          className={[
            "flex gap-4 border-b border-[#DDE4DF] px-5 py-4 last:border-b-0 transition",
            hoveredGroup === item.group ? "bg-[#E3F1EA]" : "",
          ].join(" ")}
        >
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#F1F4F1] text-xs font-bold text-[#626D67]">
            {index + 1}
          </span>

          <div>
            <strong className="text-sm text-[#17211D]">
              {item.title}
            </strong>

            <p className="mt-1 text-sm leading-6 text-[#626D67]">
              {item.evidence}
            </p>

            <span className="mt-2 inline-flex rounded bg-[#F1F4F1] px-2 py-1 text-xs text-[#626D67]">
              {item.group}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

export default EvidenceList;