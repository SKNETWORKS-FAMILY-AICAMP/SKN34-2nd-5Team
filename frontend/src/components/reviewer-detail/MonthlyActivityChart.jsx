import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function MonthlyActivityChart({ data }) {
  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-5">
      <div>
        <h3 className="text-lg font-bold text-[#17211D]">
          월별 리뷰 활동 추이
        </h3>

        <p className="mt-2 text-sm text-[#68736D]">
          관찰 기간 동안 월별로 작성한 리뷰 수의 변화를 표시합니다.
        </p>
      </div>

      <div className="mt-6 h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
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
              dataKey="month"
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
              width={35}
              tick={{
                fill: "#68736D",
                fontSize: 12,
              }}
            />

            <Tooltip
              formatter={(value) => [
                `${value}건`,
                "리뷰 수",
              ]}
              labelFormatter={(label) => `${label} 활동`}
            />

            <Line
              type="monotone"
              dataKey="reviewCount"
              name="리뷰 수"
              stroke="#137A5A"
              strokeWidth={3}
              dot={{
                fill: "#137A5A",
                strokeWidth: 0,
                r: 4,
              }}
              activeDot={{
                r: 6,
              }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <p className="mt-3 text-xs leading-5 text-[#68736D]">
        현재 차트는 React 화면 검증을 위한 DEMO 데이터입니다.
      </p>
    </div>
  );
}

export default MonthlyActivityChart;