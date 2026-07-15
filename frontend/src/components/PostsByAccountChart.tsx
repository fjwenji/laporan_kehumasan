import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import './ChartStyles.css';

interface Props {
  data: { username: string; nama_unit: string; count: number }[];
}

export default function PostsByAccountChart({ data }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="chart-empty">
        <p>Tidak ada data postingan</p>
      </div>
    );
  }

  const chartData = data.slice(0, 15).map((item) => ({
    name: item.username.length > 12 ? item.username.substring(0, 12) + '...' : item.username,
    fullName: item.nama_unit || item.username,
    count: item.count,
  }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={chartData}
        margin={{ top: 10, right: 10, left: 0, bottom: 20 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fill: '#64748B', fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: '#E2E8F0' }}
          angle={-45}
          textAnchor="end"
          height={60}
        />
        <YAxis
          tick={{ fill: '#64748B', fontSize: 11 }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          content={({ active, payload }) => {
            if (active && payload && payload.length) {
              const data = payload[0].payload;
              return (
                <div className="chart-tooltip">
                  <p className="tooltip-title">{data.fullName}</p>
                  <p className="tooltip-value">{data.count} postingan</p>
                </div>
              );
            }
            return null;
          }}
        />
        <Bar dataKey="count" fill="#F59E0B" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
