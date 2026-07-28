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

function RegionalRiskChart({ regions }) {
  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-5">
      <div>
        <h2 className="text-xl font-bold text-[#17211D]">
          권역별 활동 위험 리뷰어
        </h2>

        <p className="mt-2 text-sm leading-6 text-[#68736D]">
          약화 우세와 중단 우세 리뷰어 수를 권역별로 비교합니다.
        </p>
      </div>

      <div className="mt-6 h-96 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={regions}
            margin={{ top: 10, right: 20, bottom: 10, left: 0 }}
          >
            <CartesianGrid
              stroke="#E6EBE7"
              strokeDasharray="4 4"
              vertical={false}
            />

            <XAxis
              dataKey="region"
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#68736D", fontSize: 12 }}
            />

            <YAxis
              allowDecimals={false}
              axisLine={false}
              tickLine={false}
              width={45}
              tick={{ fill: "#68736D", fontSize: 12 }}
            />

            <Tooltip
              formatter={(value, name) => [
                `${Number(value).toLocaleString()}명`,
                name,
              ]}
              labelFormatter={(label) => {
                const match = regions.find((item) => item.region === label);
                return match ? `${label} · ${match.topCity} 중심` : label;
              }}
            />

            <Legend />

            <Bar
              dataKey="retained"
              name="유지 우세"
              stackId="state"
              fill="#B8C0BB"
            />

            <Bar
              dataKey="weakened"
              name="약화 우세"
              stackId="state"
              fill="#D9A441"
            />

            <Bar
              dataKey="stopped"
              name="중단 우세"
              stackId="state"
              fill="#E15D47"
              radius={[5, 5, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <p className="mt-3 text-xs leading-5 text-[#68736D]">
        권역은 리뷰어가 관찰 구간에 가장 많이 리뷰한 지역이며, 거주지가
        아닙니다.
      </p>
    </div>
  );
}

export default RegionalRiskChart;
