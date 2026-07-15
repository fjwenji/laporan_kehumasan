import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import type { EngagementData } from '../types';
import './ChartStyles.css';

interface Props {
  data: EngagementData[];
}

const COLORS = ['#2563EB', '#16A34A', '#F59E0B', '#7C3AED', '#0891B2', '#EC4899', '#14B8A6', '#F97316', '#8B5CF6', '#06B6D4'];

export default function EngagementBarChart({ data }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="chart-empty">
        <p>Tidak ada data engagement</p>
      </div>
    );
  }

  const chartData = data.slice(0, 10).map((item) => ({
    name: item.username.length > 15 ? item.username.substring(0, 15) + '...' : item.username,
    fullName: item.nama_unit || item.username,
    engagement: item.total_engagement,
    likes: item.like_count,
    comments: item.comment_count,
  }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={chartData}
        margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
        layout="vertical"
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" horizontal={false}/>
        <XAxis
          type="number"
          tick={{ fill: '#64748B', fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: '#E2E8F0' }}
        />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fill: '#64748B', fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          width={80}
        />
        <Tooltip
          content={({ active, payload }) => {
            if (active && payload && payload.length) {
              const data = payload[0].payload;
              return (
                <div className="chart-tooltip">
                  <p className="tooltip-title">{data.fullName}</p>
                  <p className="tooltip-value">Total: {data.engagement.toLocaleString('id-ID')}</p>
                  <p className="tooltip-detail">Like: {data.likes.toLocaleString('id-ID')}</p>
                  <p className="tooltip-detail">Komentar: {data.comments.toLocaleString('id-ID')}</p>
                </div>
              );
            }
            return null;
          }}
        />
        <Bar dataKey="engagement" radius={[0, 4, 4, 0]}>
          {chartData.map((_, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
