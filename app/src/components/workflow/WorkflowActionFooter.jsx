function WorkflowActionFooter({ summary, detail, secondaryAction, primaryAction, sticky = true }) {
  return (
    <div className={`${sticky ? "sticky bottom-2 z-20 bg-white/96 shadow-[0_14px_36px_rgba(23,33,29,0.14)] backdrop-blur sm:bottom-3" : "relative bg-white shadow-[0_8px_22px_rgba(23,33,29,0.07)]"} mt-5 flex flex-wrap items-center gap-3 rounded-xl border border-[#AFCDBE] px-4 py-3 sm:px-5`}>
      <div className="min-w-0 flex-1">
        <p className="text-[13px] font-black text-[#17211D]">{summary}</p>
        {detail && <p className="mt-0.5 truncate text-[11px] text-[#626D67]">{detail}</p>}
      </div>
      <div className="flex w-full flex-wrap gap-2 sm:w-auto sm:flex-nowrap">
        {secondaryAction && <div className="min-w-0 flex-1 [&>*]:w-full [&>*]:justify-center sm:flex-none sm:[&>*]:w-auto">{secondaryAction}</div>}
        {primaryAction && <div className="min-w-0 flex-[1.25] [&>*]:w-full [&>*]:justify-center sm:flex-none sm:[&>*]:w-auto">{primaryAction}</div>}
      </div>
    </div>
  );
}

export default WorkflowActionFooter;
