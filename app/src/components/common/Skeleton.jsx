// Same-shape placeholder rows so the layout doesn't jump when real data
// arrives — replaces the old plain "불러오는 중…" text screens.
function Skeleton({ rows = 5, columns = 4, className = "" }) {
  return (
    <div
      className={`overflow-hidden rounded-lg border border-[#DDE4DF] bg-white ${className}`}
      role="status"
      aria-label="불러오는 중"
    >
      {Array.from({ length: rows }, (_, rowIndex) => (
        <div
          key={rowIndex}
          className="grid gap-3 border-b border-[#F1F4F1] px-4 py-2 last:border-b-0"
          style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
        >
          {Array.from({ length: columns }, (_, colIndex) => (
            <div
              key={colIndex}
              className="h-2.5 animate-pulse rounded bg-[#EDF0EE]"
              style={{ width: colIndex === 0 ? "40%" : "80%" }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

export default Skeleton;
