function StatusBadge({ judgment }) {
  let className = "bg-[#E3F1EA] text-[#137A5A]";

  if (judgment.includes("중단")) {
    className = "bg-[#F7E8E5] text-[#E15D47]";
  } else if (judgment.includes("약화")) {
    className = "bg-[#FAEFD9] text-[#A66A18]";
  }

  return (
    <span
      className={`inline-flex whitespace-nowrap rounded px-2 py-1 text-xs font-bold ${className}`}
    >
      {judgment}
    </span>
  );
}

export default StatusBadge;