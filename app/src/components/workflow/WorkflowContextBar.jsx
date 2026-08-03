function WorkflowContextBar({ label, title, metrics = [], action }) {
  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-3 rounded-xl border border-[#B7D8C8] bg-[#EFF7F3] px-4 py-3">
      <div className="min-w-0">
        <p className="text-[10px] font-black tracking-[0.12em] text-[#137A5A]">{label}</p>
        <p className="truncate text-sm font-bold text-[#17211D]">{title}</p>
      </div>
      <div className="flex flex-1 flex-wrap items-center gap-x-5 gap-y-1">
        {metrics.map((metric) => <span key={`${metric.label}-${metric.value}`} className="text-xs text-[#4B665B]"><span className="text-[#718078]">{metric.label}</span> <strong className="ml-1 text-[#17211D]">{metric.value}</strong></span>)}
      </div>
      {action && <div className="w-full shrink-0 [&>*]:w-full [&>*]:justify-center sm:w-auto sm:[&>*]:w-auto">{action}</div>}
    </div>
  );
}

export default WorkflowContextBar;
