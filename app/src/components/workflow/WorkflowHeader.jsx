function WorkflowHeader({ eyebrow, title, description, steps = [], activeStep = 0, aside }) {
  return (
    <section>
      <div className="flex flex-wrap items-end justify-between gap-4 sm:flex-nowrap sm:gap-5">
        <div className="min-w-0 flex-1">
          {eyebrow && <p className="text-[10px] font-black tracking-[0.16em] text-[#137A5A]">운영 홈 <span className="mx-2 text-[#A1AAA5]">›</span> {eyebrow}</p>}
          <h1 className="mt-2 text-2xl font-black tracking-[-0.035em] text-[#17211D] md:text-[32px]">{title}</h1>
          {description && <p className="mt-1.5 max-w-3xl text-[13px] leading-5 text-[#626D67]">{description}</p>}
        </div>
        {aside && <div className="shrink-0 rounded-lg bg-white/70 px-2 py-1 text-right text-[11px] sm:bg-transparent sm:p-0">{aside}</div>}
      </div>

      {steps.length > 0 && (
        <ol className="mt-5 grid overflow-hidden rounded-xl border border-[#D7E0DA] bg-white shadow-[0_2px_8px_rgba(23,33,29,0.03)] md:grid-flow-col md:auto-cols-fr">
          {steps.map((step, index) => {
            const active = index === activeStep;
            const complete = index < activeStep;
            return (
              <li key={step} className={`relative flex min-h-12 items-center justify-center gap-2 border-b border-[#E5EAE6] px-4 text-xs font-bold last:border-b-0 md:border-r md:border-b-0 md:last:border-r-0 ${active ? "z-10 bg-[#075C45] text-white md:[clip-path:polygon(0_0,calc(100%_-_18px)_0,100%_50%,calc(100%_-_18px)_100%,0_100%,18px_50%)] md:first:[clip-path:polygon(0_0,calc(100%_-_18px)_0,100%_50%,calc(100%_-_18px)_100%,0_100%)]" : complete ? "bg-[#EDF6F1] text-[#075C45]" : "text-[#7A8580]"}`}>
                <span className={`grid h-5 w-5 shrink-0 place-items-center rounded-full text-[10px] ${active ? "bg-white text-[#075C45]" : complete ? "bg-[#075C45] text-white" : "bg-[#EEF1EF] text-[#7A8580]"}`}>{complete ? "✓" : index + 1}</span>
                <span className="whitespace-nowrap leading-4">{step}</span>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

export default WorkflowHeader;
