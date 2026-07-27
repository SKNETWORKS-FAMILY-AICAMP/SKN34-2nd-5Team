function getStatusStyle(status) {
  if (status === "완료") {
    return {
      dot: "bg-[#137A5A]",
      badge: "bg-[#E3F1EA] text-[#137A5A]",
    };
  }

  if (status === "진행 중") {
    return {
      dot: "bg-[#A66A18]",
      badge: "bg-[#FAEFD9] text-[#A66A18]",
    };
  }

  return {
    dot: "bg-[#B8C0BB]",
    badge: "bg-[#F1F4F1] text-[#68736D]",
  };
}

function RoadmapTimeline({ roadmap }) {
  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-6">
      <div className="space-y-0">
        {roadmap.map((item, index) => {
          const style = getStatusStyle(item.status);
          const isLast = index === roadmap.length - 1;

          return (
            <div
              key={item.stage}
              className="grid grid-cols-[40px_1fr] gap-4"
            >
              <div className="flex flex-col items-center">
                <span
                  className={[
                    "flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold text-white",
                    style.dot,
                  ].join(" ")}
                >
                  {item.stage}
                </span>

                {!isLast && (
                  <span className="min-h-20 w-px flex-1 bg-[#DDE4DF]" />
                )}
              </div>

              <div className={isLast ? "pb-0" : "pb-7"}>
                <div className="flex flex-col justify-between gap-2 sm:flex-row">
                  <h3 className="font-bold text-[#17211D]">
                    {item.title}
                  </h3>

                  <span
                    className={[
                      "w-fit rounded-full px-3 py-1 text-xs font-bold",
                      style.badge,
                    ].join(" ")}
                  >
                    {item.status}
                  </span>
                </div>

                <p className="mt-2 text-sm leading-6 text-[#68736D]">
                  {item.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default RoadmapTimeline;