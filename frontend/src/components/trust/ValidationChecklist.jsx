function getStatusStyle(status) {
  if (status === "완료") {
    return {
      icon: "✓",
      badge: "bg-[#E3F1EA] text-[#137A5A]",
      iconBox: "bg-[#137A5A] text-white",
    };
  }

  return {
    icon: "!",
    badge: "bg-[#FAEFD9] text-[#A66A18]",
    iconBox: "bg-[#A66A18] text-white",
  };
}

function ValidationChecklist({ checks }) {
  return (
    <div className="overflow-hidden rounded-xl border border-[#DDE4DF] bg-white">
      {checks.map((check) => {
        const style = getStatusStyle(check.status);

        return (
          <div
            key={check.id}
            className="flex gap-4 border-b border-[#DDE4DF] px-5 py-4 last:border-b-0"
          >
            <span
              className={[
                "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold",
                style.iconBox,
              ].join(" ")}
            >
              {style.icon}
            </span>

            <div className="flex-1">
              <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-start">
                <strong className="text-sm text-[#17211D]">
                  {check.title}
                </strong>

                <span
                  className={[
                    "w-fit rounded-full px-3 py-1 text-xs font-bold",
                    style.badge,
                  ].join(" ")}
                >
                  {check.status}
                </span>
              </div>

              <p className="mt-2 text-sm leading-6 text-[#68736D]">
                {check.description}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default ValidationChecklist;