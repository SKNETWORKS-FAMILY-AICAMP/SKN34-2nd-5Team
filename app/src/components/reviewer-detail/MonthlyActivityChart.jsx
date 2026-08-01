import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// Builds a continuous month axis so gaps (months with zero reviews) show up
// as dips instead of being skipped — `data` only carries months that had
// activity, exported sparsely to keep reviewer-details.json smaller.
function buildSeries(data, comparisonYear, selectionYear) {
  const bySampleMonth = new Map(data.map((item) => [item.month, item]));
  const months = [];

  for (let year = comparisonYear; year <= selectionYear; year += 1) {
    for (let month = 1; month <= 12; month += 1) {
      const key = `${year}-${String(month).padStart(2, "0")}`;
      const found = bySampleMonth.get(key);

      months.push({
        month: key,
        reviewCount: found?.reviewCount ?? 0,
        uniqueBusinessCount: found?.uniqueBusinessCount ?? 0,
      });
    }
  }

  return months;
}

// Restricted to comparison_year..selection_year (never the target/validation
// year) so this always-visible tab can't leak the post-hoc outcome that the
// "검증 정답 표시" toggle is meant to gate.
function MonthlyActivityChart({ data, comparisonYear, selectionYear }) {
  const series = buildSeries(data, comparisonYear, selectionYear);

  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-5">
      <div>
        <h3 className="text-lg font-bold text-[#17211D]">
          월별 리뷰 활동 추이
        </h3>

        <p className="mt-2 text-sm text-[#626D67]">
          {comparisonYear}년 ~ {selectionYear}년(비교~선정·피처 마감 구간)
          동안 월별 리뷰 수와 방문 음식점 수의 변화를 표시합니다.
        </p>
      </div>

      <div className="mt-6 h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={series} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
            <CartesianGrid stroke="#E6EBE7" strokeDasharray="4 4" vertical={false} />

            <XAxis
              dataKey="month"
              axisLine={false}
              tickLine={false}
              interval={1}
              tick={{ fill: "#626D67", fontSize: 11 }}
            />

            <YAxis
              allowDecimals={false}
              axisLine={false}
              tickLine={false}
              width={35}
              tick={{ fill: "#626D67", fontSize: 12 }}
            />

            <Tooltip
              formatter={(value, name) => [`${value}건`, name]}
              labelFormatter={(label) => `${label} 활동`}
            />

            <Line
              type="monotone"
              dataKey="reviewCount"
              name="리뷰 수"
              stroke="#137A5A"
              strokeWidth={3}
              dot={{ fill: "#137A5A", strokeWidth: 0, r: 3 }}
            />

            <Line
              type="monotone"
              dataKey="uniqueBusinessCount"
              name="고유 음식점 수"
              stroke="#A66A18"
              strokeWidth={2}
              dot={{ fill: "#A66A18", strokeWidth: 0, r: 3 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <p className="mt-3 text-xs leading-5 text-[#626D67]">
        파이프라인이 생성한 reviewer_monthly_activity_v04.parquet을 사용하며,
        타깃·검증 연도는 제외하고 비교 연도부터 선정 연도까지만 표시합니다.
      </p>
    </div>
  );
}

export default MonthlyActivityChart;
