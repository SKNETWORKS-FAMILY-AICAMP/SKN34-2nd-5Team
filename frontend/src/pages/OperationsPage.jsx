import { Link } from "react-router";

import PolicyPanel from "../components/operations/PolicyPanel";
import PriorityQueue from "../components/operations/PriorityQueue";
import {
  operationsSummary,
  priorityReviewers,
} from "../mocks/operationsData";

function OperationsPage() {
  return (
    <section>
      <div className="flex flex-col justify-between gap-5 border-b border-[#DDE4DF] pb-7 lg:flex-row lg:items-start">
        <div>
          <p className="text-xs font-bold tracking-[0.15em] text-[#4C987C]">
            OPERATIONS · {operationsSummary.modelVersion}
          </p>

          <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] text-[#17211D] md:text-5xl">
            우선 대응 대상 리뷰어
          </h1>

          <p className="mt-4 text-[#68736D]">
            통합 우선순위 상위 20% ·{" "}
            {operationsSummary.targetUsers.toLocaleString()}명
          </p>
        </div>

        <div className="text-left lg:text-right">
          <span className="inline-flex rounded-full bg-[#17211D] px-3 py-1 text-xs font-bold text-white">
            {operationsSummary.dataMode}
          </span>

          <p className="mt-2 text-xs text-[#68736D]">
            {operationsSummary.snapshot} 스냅샷 기준
          </p>
        </div>
      </div>

      <div className="mt-8 grid gap-5 sm:grid-cols-3">
        <SummaryCard
          label="전체 리뷰어"
          value={`${operationsSummary.totalReviewers.toLocaleString()}명`}
        />

        <SummaryCard
          label="우선 검토 대상"
          value={`${operationsSummary.targetUsers.toLocaleString()}명`}
        />

        <SummaryCard
          label="판단 완료"
          value={`${operationsSummary.completedUsers.toLocaleString()}명`}
          good
        />
      </div>

      <div className="mt-10 grid gap-8 xl:grid-cols-[1.7fr_1fr]">
        <div>
          <div className="mb-4 flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
            <div>
              <h2 className="text-xl font-bold text-[#17211D]">
                이번 세션 우선 검토
              </h2>

              <p className="mt-1 text-sm text-[#68736D]">
                {priorityReviewers.length}명 표시 · 통합 검토 대상{" "}
                {operationsSummary.targetUsers.toLocaleString()}명 중
              </p>
            </div>

            <span className="text-sm text-[#68736D]">
              {operationsSummary.completedUsers.toLocaleString()}명 판단 완료
            </span>
          </div>

          <PriorityQueue reviewers={priorityReviewers} />

          <Link
            to="/reviewers"
            className="mt-5 flex min-h-11 items-center justify-center rounded-lg bg-[#137A5A] px-5 font-bold text-white transition hover:bg-[#185C46]"
          >
            리뷰어 관리에서 전체 대상 보기
          </Link>
        </div>

        <PolicyPanel summary={operationsSummary} />
      </div>

      <footer className="mt-12 border-t border-[#DDE4DF] pt-5 text-xs text-[#68736D]">
        Reviewer Retention · DEMO data · 클래스 점수는 보정 확률이
        아니며 통합 점수는 운영 우선순위에 사용합니다.
      </footer>
    </section>
  );
}

function SummaryCard({ label, value, good = false }) {
  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white px-5 py-4">
      <p className="text-sm text-[#68736D]">
        {label}
      </p>

      <p
        className={[
          "mt-2 text-2xl font-bold",
          good ? "text-[#137A5A]" : "text-[#17211D]",
        ].join(" ")}
      >
        {value}
      </p>
    </div>
  );
}

export default OperationsPage;