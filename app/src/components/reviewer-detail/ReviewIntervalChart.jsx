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

function ReviewIntervalChart({ data }) {
  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-5">
      <div>
        <h3 className="text-lg font-bold text-[#17211D]">
          리뷰 작성 간격 비교
        </h3>

        <p className="mt-2 text-sm text-[#68736D]">
          이전 기간과 최근 기간의 작성 간격 및 리뷰 공백을
          비교합니다.
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

            <Tooltip
              formatter={(value, name) => [
                `${Math.round(value).toLocaleString()}일`,
                name,
              ]}
            />

            <Legend />

            <Bar
              dataKey="before"
              name="이전 기간"
              fill="#B8C0BB"
              radius={[5, 5, 0, 0]}
            />

            <Bar
              dataKey="after"
              name="최근 기간"
              fill="#137A5A"
              radius={[5, 5, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <p className="mt-3 text-xs leading-5 text-[#68736D]">
        값이 커질수록 리뷰 작성 주기가 길어졌거나 마지막 리뷰
        이후 공백이 증가했다는 의미입니다.
      </p>
    </div>
  );
}

export default ReviewIntervalChart;