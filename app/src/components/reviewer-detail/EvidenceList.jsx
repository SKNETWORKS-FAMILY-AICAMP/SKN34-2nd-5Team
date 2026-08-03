function EvidenceList({ evidence, hoveredGroup, onHoverGroup, compact = false }) {
  return (
    <div className={`grid overflow-hidden rounded-xl border border-[#DDE4DF] bg-white ${compact ? "grid-cols-1" : "md:grid-cols-2"}`}>
      {evidence.map((item, index) => (
        <div
          key={item.title}
          onMouseEnter={() => onHoverGroup?.(item.group)}
          onMouseLeave={() => onHoverGroup?.(null)}
          className={[
            compact
              ? "flex gap-2.5 border-b border-[#DDE4DF] px-3 py-2.5 transition last:border-b-0"
              : "flex gap-3 border-b border-[#DDE4DF] px-4 py-3 transition md:border-r md:[&:nth-child(even)]:border-r-0 md:[&:nth-last-child(-n+2)]:border-b-0",
            hoveredGroup === item.group ? "bg-[#E3F1EA]" : "",
          ].join(" ")}
        >
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#F1F4F1] text-[10px] font-bold text-[#626D67]">
            {index + 1}
          </span>

          <div>
            <strong className="text-xs text-[#17211D]">
              {item.title}
            </strong>

            <p className={`${compact ? "mt-0.5 line-clamp-2 text-[10px] leading-4" : "mt-1 text-[11px] leading-5"} text-[#626D67]`}>
              {item.evidence}
            </p>

            {!compact && <span className="mt-1.5 inline-flex rounded bg-[#F1F4F1] px-2 py-0.5 text-[10px] text-[#626D67]">{item.group}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

export default EvidenceList;
