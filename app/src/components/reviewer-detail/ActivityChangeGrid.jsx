function ActivityChangeGrid({ changes }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {changes.map((change) => (
        <div
          key={change.label}
          className="rounded-xl bg-[#F1F4F1] p-4"
        >
          <p className="text-xs font-semibold text-[#68736D]">
            {change.label}
          </p>

          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-sm text-[#68736D] line-through">
              {change.before}
            </span>

            <span className="text-[#137A5A]">
              →
            </span>

            <strong className="text-lg text-[#17211D]">
              {change.after}
            </strong>
          </div>

          <p
            className={[
              "mt-2 text-sm font-bold",
              change.tone === "positive"
                ? "text-[#137A5A]"
                : change.tone === "muted"
                  ? "text-[#68736D]"
                  : "text-[#E15D47]",
            ].join(" ")}
          >
            {change.delta}
          </p>
        </div>
      ))}
    </div>
  );
}

export default ActivityChangeGrid;