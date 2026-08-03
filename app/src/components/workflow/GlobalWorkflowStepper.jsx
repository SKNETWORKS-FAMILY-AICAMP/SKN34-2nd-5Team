import { Link } from "react-router";

function GlobalWorkflowStepper({ steps, currentStep }) {
  return (
    <nav aria-label="운영 진행 단계" className="overflow-x-auto rounded-lg border border-[#DDE4DF] bg-white">
      <ol className="flex min-w-[760px]">
        {steps.map((step, index) => {
          const stepNumber = index + 1;
          const current = stepNumber === currentStep;
          const previous = stepNumber < currentStep;
          const available = Boolean(step.href) && !current;
          const locked = !current && !available;
          const tone = current
            ? "bg-[#075C45] text-white"
            : previous
              ? "bg-[#EDF6F1] text-[#075C45]"
              : available
                ? "bg-white text-[#075C45]"
                : "bg-white text-[#8A948F]";
          const content = (
            <>
              <span className={`grid h-5 w-5 shrink-0 place-items-center rounded-full border text-[10px] font-black ${current ? "border-white bg-white text-[#075C45]" : previous || available ? "border-[#75B59A] bg-white text-[#075C45]" : "border-[#DDE4DF] bg-[#F1F3F2] text-[#8A948F]"}`}>
                {stepNumber}
              </span>
              <span className="whitespace-nowrap">{step.label}</span>
            </>
          );

          return (
            <li key={step.label} className={`flex min-h-10 min-w-0 flex-1 border-r border-[#E6EBE8] last:border-r-0 ${tone}`}>
              {available ? (
                <Link
                  to={step.href}
                  aria-label={`${step.label}으로 이동`}
                  className="flex min-h-10 w-full items-center justify-center gap-2 px-3 text-[10px] font-black transition hover:bg-[#EAF4EF] focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[#075C45]"
                >
                  {content}
                </Link>
              ) : (
                <span
                  aria-current={current ? "step" : undefined}
                  aria-disabled={locked ? "true" : undefined}
                  className="flex min-h-10 w-full items-center justify-center gap-2 px-3 text-[10px] font-bold"
                >
                  {content}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

export default GlobalWorkflowStepper;
