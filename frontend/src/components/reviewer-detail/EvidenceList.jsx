function EvidenceList({ evidence }) {
  return (
    <div className="overflow-hidden rounded-xl border border-[#DDE4DF] bg-white">
      {evidence.map((item, index) => (
        <div
          key={item.title}
          className="flex gap-4 border-b border-[#DDE4DF] px-5 py-4 last:border-b-0"
        >
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#F1F4F1] text-xs font-bold text-[#68736D]">
            {index + 1}
          </span>

          <div>
            <strong className="text-sm text-[#17211D]">
              {item.title}
            </strong>

            <p className="mt-1 text-sm leading-6 text-[#68736D]">
              {item.evidence}
            </p>

            <span className="mt-2 inline-flex rounded bg-[#F1F4F1] px-2 py-1 text-xs text-[#68736D]">
              {item.group}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

export default EvidenceList;