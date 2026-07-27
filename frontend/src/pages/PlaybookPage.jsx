import { useMemo, useState } from "react";
import { Link } from "react-router";

import PlaybookCard from "../components/playbook/PlaybookCard";
import PlaybookFilters from "../components/playbook/PlaybookFilters";
import { playbookData } from "../mocks/playbookData";
import { reviewerData } from "../mocks/reviewerData";

function PlaybookPage() {
  const [judgmentFilter, setJudgmentFilter] =
    useState("전체");

  const [riskTypeFilter, setRiskTypeFilter] =
    useState("전체");

  const riskTypes = useMemo(
    () => [
      ...new Set(
        playbookData.flatMap(
          (playbook) => playbook.riskTypes,
        ),
      ),
    ],
    [],
  );

  const visiblePlaybooks = useMemo(() => {
    return playbookData.filter((playbook) => {
      const matchesJudgment =
        judgmentFilter === "전체" ||
        playbook.judgments.includes(judgmentFilter);

      const matchesRiskType =
        riskTypeFilter === "전체" ||
        playbook.riskTypes.includes(riskTypeFilter);

      return matchesJudgment && matchesRiskType;
    });
  }, [judgmentFilter, riskTypeFilter]);

  function getMatchedReviewers(playbook) {
    return reviewerData.filter((reviewer) => {
      const matchesJudgment =
        playbook.judgments.includes(
          reviewer.modelJudgment,
        );

      const matchesRiskType =
        playbook.riskTypes.includes(reviewer.riskType);

      return matchesJudgment && matchesRiskType;
    });
  }

  const interventionTargetCount = reviewerData.filter(
    (reviewer) =>
      reviewer.modelJudgment === "약화 우세" ||
      reviewer.modelJudgment === "중단 우세",
  ).length;

  return (
    <section>
      <div className="flex flex-col justify-between gap-5 border-b border-[#DDE4DF] pb-7 lg:flex-row">
        <div>
          <p className="text-xs font-bold tracking-[0.15em] text-[#4C987C]">
            RETENTION PLAYBOOK · REACT
          </p>

          <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] text-[#17211D] md:text-5xl">
            리텐션 플레이북
          </h1>

          <p className="mt-4 max-w-3xl leading-7 text-[#68736D]">
            리뷰 활동 변화와 위험 유형에 따라 운영자가 검토할
            대응 전략을 정리합니다.
          </p>
        </div>

        <div className="lg:text-right">
          <span className="inline-flex rounded-full bg-[#17211D] px-3 py-1 text-xs font-bold text-white">
            DEMO 전략
          </span>

          <p className="mt-3 text-sm text-[#68736D]">
            현재 개입 검토 대상
          </p>

          <p className="mt-1 text-2xl font-bold text-[#137A5A]">
            {interventionTargetCount}명
          </p>
        </div>
      </div>

      <div className="mt-7 grid gap-4 md:grid-cols-3">
        <SummaryCard
          label="전체 전략"
          value={`${playbookData.length}개`}
        />

        <SummaryCard
          label="현재 표시"
          value={`${visiblePlaybooks.length}개`}
        />

        <SummaryCard
          label="개입 검토 리뷰어"
          value={`${interventionTargetCount}명`}
          good
        />
      </div>

      <div className="mt-6">
        <PlaybookFilters
          judgmentFilter={judgmentFilter}
          onJudgmentChange={setJudgmentFilter}
          riskTypeFilter={riskTypeFilter}
          onRiskTypeChange={setRiskTypeFilter}
          riskTypes={riskTypes}
        />
      </div>

      <div className="mt-7 space-y-6">
        {visiblePlaybooks.length > 0 ? (
          visiblePlaybooks.map((playbook) => (
            <PlaybookCard
              key={playbook.id}
              playbook={playbook}
              matchedReviewers={getMatchedReviewers(
                playbook,
              )}
            />
          ))
        ) : (
          <div className="rounded-xl bg-[#F1F4F1] px-6 py-12 text-center">
            <h2 className="font-bold text-[#17211D]">
              해당 조건의 플레이북이 없습니다
            </h2>

            <p className="mt-2 text-sm text-[#68736D]">
              모델 판단 또는 위험 유형 필터를 변경해 주세요.
            </p>
          </div>
        )}
      </div>

      <div className="mt-8 rounded-xl border border-[#DDE4DF] bg-white p-6">
        <h2 className="text-lg font-bold text-[#17211D]">
          운영 시 주의사항
        </h2>

        <p className="mt-3 text-sm leading-7 text-[#68736D]">
          현재 플레이북은 모델이 자동으로 실행하는 마케팅
          정책이 아닙니다. 운영자가 활동 변화 근거를 확인하고
          개입 필요성을 판단하기 위한 전략 후보입니다.
        </p>

        <Link
          to="/reviewers"
          className="mt-5 inline-flex min-h-11 items-center justify-center rounded-lg bg-[#137A5A] px-5 font-bold text-white transition hover:bg-[#185C46]"
        >
          리뷰어 워크리스트 확인
        </Link>
      </div>

      <footer className="mt-12 border-t border-[#DDE4DF] pt-5 text-xs text-[#68736D]">
        Reviewer Retention · DEMO playbook · 실제 실행 정책은
        담당자 검토와 효과 검증 이후 확정합니다.
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
          good
            ? "text-[#137A5A]"
            : "text-[#17211D]",
        ].join(" ")}
      >
        {value}
      </p>
    </div>
  );
}

export default PlaybookPage;