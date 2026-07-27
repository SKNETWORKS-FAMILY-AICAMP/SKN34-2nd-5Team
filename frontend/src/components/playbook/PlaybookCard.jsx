import { Link } from "react-router";

function getToneStyle(tone) {
  if (tone === "critical") {
    return {
      label: "bg-[#F7E8E5] text-[#E15D47]",
      border: "border-t-[#E15D47]",
    };
  }

  if (tone === "warning") {
    return {
      label: "bg-[#FAEFD9] text-[#A66A18]",
      border: "border-t-[#A66A18]",
    };
  }

  if (tone === "watch") {
    return {
      label: "bg-[#E6EFF1] text-[#356A78]",
      border: "border-t-[#356A78]",
    };
  }

  return {
    label: "bg-[#E3F1EA] text-[#137A5A]",
    border: "border-t-[#137A5A]",
  };
}

function PlaybookCard({ playbook, matchedReviewers }) {
  const toneStyle = getToneStyle(playbook.tone);

  return (
    <article
      className={[
        "rounded-xl border border-[#DDE4DF] border-t-4 bg-white p-6",
        toneStyle.border,
      ].join(" ")}
    >
      <div className="flex flex-col justify-between gap-4 sm:flex-row">
        <div>
          <span
            className={[
              "inline-flex rounded-full px-3 py-1 text-xs font-bold",
              toneStyle.label,
            ].join(" ")}
          >
            {playbook.category}
          </span>

          <h2 className="mt-4 text-2xl font-bold text-[#17211D]">
            {playbook.title}
          </h2>
        </div>

        <div className="sm:text-right">
          <p className="text-xs text-[#68736D]">
            현재 해당 대상
          </p>

          <p className="mt-1 text-2xl font-bold text-[#137A5A]">
            {matchedReviewers.length}명
          </p>
        </div>
      </div>

      <p className="mt-4 leading-7 text-[#68736D]">
        {playbook.summary}
      </p>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div>
          <h3 className="text-sm font-bold text-[#17211D]">
            주요 위험 신호
          </h3>

          <ul className="mt-3 space-y-2">
            {playbook.signals.map((signal) => (
              <li
                key={signal}
                className="flex gap-2 text-sm leading-6 text-[#68736D]"
              >
                <span className="font-bold text-[#137A5A]">
                  ·
                </span>
                <span>{signal}</span>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="text-sm font-bold text-[#17211D]">
            권장 실행안
          </h3>

          <p className="mt-3 rounded-lg bg-[#F1F4F1] px-4 py-3 text-sm font-semibold leading-6 text-[#17211D]">
            {playbook.primaryAction}
          </p>

          <ul className="mt-3 space-y-2">
            {playbook.secondaryActions.map((action) => (
              <li
                key={action}
                className="text-sm leading-6 text-[#68736D]"
              >
                · {action}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-6 border-t border-[#DDE4DF] pt-4">
        <p className="text-xs font-bold text-[#68736D]">
          활용 채널
        </p>

        <div className="mt-2 flex flex-wrap gap-2">
          {playbook.channels.map((channel) => (
            <span
              key={channel}
              className="rounded bg-[#F1F4F1] px-2 py-1 text-xs text-[#68736D]"
            >
              {channel}
            </span>
          ))}
        </div>
      </div>

      <div className="mt-6 border-t border-[#DDE4DF] pt-4">
        <p className="text-xs font-bold text-[#68736D]">
          해당 리뷰어
        </p>

        {matchedReviewers.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {matchedReviewers.slice(0, 4).map((reviewer) => (
              <Link
                key={reviewer.userId}
                to={`/reviewers/${reviewer.userId}`}
                className="rounded-lg border border-[#DDE4DF] px-3 py-2 text-xs font-semibold text-[#137A5A] transition hover:bg-[#E3F1EA]"
              >
                {reviewer.userId}
              </Link>
            ))}

            {matchedReviewers.length > 4 && (
              <span className="flex items-center px-2 text-xs text-[#68736D]">
                외 {matchedReviewers.length - 4}명
              </span>
            )}
          </div>
        ) : (
          <p className="mt-3 text-sm text-[#68736D]">
            현재 DEMO 데이터에서 해당하는 리뷰어가 없습니다.
          </p>
        )}
      </div>
    </article>
  );
}

export default PlaybookCard;