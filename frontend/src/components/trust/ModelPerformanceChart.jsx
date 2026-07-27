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

function ModelPerformanceChart({ data }) {
  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-5">
      <div>
        <h2 className="text-xl font-bold text-[#17211D]">
          모델별 성능 비교
        </h2>

        <p className="mt-2 text-sm leading-6 text-[#68736D]">
          정밀도, 재현율과 F1 점수를 같은 검증 데이터에서 비교합니다.
        </p>
      </div>

      <div className="mt-6 h-96 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{
              top: 10,
              right: 20,
              bottom: 30,
              left: 0,
            }}
          >
            <CartesianGrid
              stroke="#E6EBE7"
              strokeDasharray="4 4"
              vertical={false}
            />

            <XAxis
              dataKey="model"
              axisLine={false}
              tickLine={false}
              interval={0}
              tick={{
                fill: "#68736D",
                fontSize: 12,
              }}
            />

            <YAxis
              domain={[0, 1]}
              axisLine={false}
              tickLine={false}
              width={42}
              tickFormatter={(value) =>
                `${Math.round(value * 100)}%`
              }
              tick={{
                fill: "#68736D",
                fontSize: 12,
              }}
            />

            <Tooltip
              formatter={(value, name) => [
                `${(Number(value) * 100).toFixed(1)}%`,
                name,
              ]}
            />

            <Legend />

            <Bar
              dataKey="precision"
              name="정밀도"
              fill="#137A5A"
              radius={[4, 4, 0, 0]}
            />

            <Bar
              dataKey="recall"
              name="재현율"
              fill="#356A78"
              radius={[4, 4, 0, 0]}
            />

            <Bar
              dataKey="f1Score"
              name="F1 점수"
              fill="#A66A18"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <p className="mt-3 text-xs leading-5 text-[#68736D]">
        현재 비교값은 React 화면 구현을 위한 DEMO 값이며 실제
        모델 평가 결과로 교체해야 합니다.
      </p>
    </div>
  );
}

export default ModelPerformanceChart;