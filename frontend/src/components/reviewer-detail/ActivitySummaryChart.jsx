import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function ActivitySummaryChart({ data }) {
  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-5">
      <div>
        <h3 className="text-lg font-bold text-[#17211D]">
          활동 변화 요약
        </h3>

        <p className="mt-2 text-sm text-[#68736D]">
          비교 연도와 선정·피처 마감 연도의 활동량을 비교합니다.
        </p>
      </div>

      <div className="mt-6 h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{
              top: 10,
              right: 20,
              bottom: 10,
              left: 0,
            }}
          >
            <CartesianGrid
              stroke="#E6EBE7"
              strokeDasharray="4 4"
              vertical={false}
            />

            <XAxis
              dataKey="label"
              axisLine={false}
              tickLine={false}
              tick={{
                fill: "#68736D",
                fontSize: 12,
              }}
            />

            <YAxis
              allowDecimals={false}
              axisLine={false}
              tickLine={false}
              width={40}
              tick={{
                fill: "#68736D",
                fontSize: 12,
              }}
            />

            <Tooltip />

            <Legend />

            <Bar
              dataKey="before"
              name="비교 연도"
              fill="#B8C0BB"
              radius={[5, 5, 0, 0]}
            />

            <Bar
              dataKey="after"
              name="선정·피처 마감 연도"
              fill="#137A5A"
              radius={[5, 5, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <p className="mt-3 text-xs leading-5 text-[#68736D]">
        선정·피처 마감 연도의 값이 비교 연도보다 낮을수록 활동이 줄어든
        것입니다.
      </p>
    </div>
  );
}

export default ActivitySummaryChart;
