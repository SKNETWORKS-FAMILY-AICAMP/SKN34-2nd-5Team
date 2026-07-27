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

function RegionalRiskChart({ data }) {
  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-5">
      <div>
        <h2 className="text-xl font-bold text-[#17211D]">
          지역별 활동 위험 리뷰어
        </h2>

        <p className="mt-2 text-sm leading-6 text-[#68736D]">
          약화 우세와 중단 우세 리뷰어를 지역별로 비교합니다.
        </p>
      </div>

      <div className="mt-6 h-96 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{
              top: 10,
              right: 20,
              bottom: 35,
              left: 0,
            }}
          >
            <CartesianGrid
              stroke="#E6EBE7"
              strokeDasharray="4 4"
              vertical={false}
            />

            <XAxis
              dataKey="city"
              axisLine={false}
              tickLine={false}
              angle={-20}
              textAnchor="end"
              height={70}
              tick={{
                fill: "#68736D",
                fontSize: 12,
              }}
            />

            <YAxis
              allowDecimals={false}
              axisLine={false}
              tickLine={false}
              width={45}
              tick={{
                fill: "#68736D",
                fontSize: 12,
              }}
            />

            <Tooltip
              formatter={(value, name) => [
                `${Number(value).toLocaleString()}명`,
                name,
              ]}
            />

            <Legend />

            <Bar
              dataKey="weakened"
              name="약화 우세"
              stackId="risk"
              fill="#D48A43"
            />

            <Bar
              dataKey="stopped"
              name="중단 우세"
              stackId="risk"
              fill="#E15D47"
              radius={[5, 5, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <p className="mt-3 text-xs leading-5 text-[#68736D]">
        막대의 전체 높이는 해당 지역에서 우선 검토가 필요한
        리뷰어 수를 의미합니다.
      </p>
    </div>
  );
}

export default RegionalRiskChart;