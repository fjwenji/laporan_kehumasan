import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { MediaTypeData } from '../types';
import './ChartStyles.css';

interface Props {
  data: MediaTypeData[];
}

const COLORS: Record<string, string> = {
  'IMAGE': '#2563EB',
  'CAROUSEL': '#F59E0B',
  'REELS': '#16A34A',
  'VIDEO': '#7C3AED',
  'UNCLASSIFIED_REVIEW': '#94A3B8',
};

const LABELS: Record<string, string> = {
  'IMAGE': 'Gambar',
  'CAROUSEL': 'Carousel',
  'REELS': 'Reels',
  'VIDEO': 'Video',
  'UNCLASSIFIED_REVIEW': 'Perlu Review',
};

export default function MediaTypeChart({ data }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="chart-empty">
        <p>Tidak ada data media type</p>
      </div>
    );
  }

  const chartData = data
    .filter((d) => d.count > 0)
    .map((d) => ({
      ...d,
      label: LABELS[d.media_type] || d.media_type,
      color: COLORS[d.media_type] || '#94A3B8',
    }));

  if (chartData.length === 0) {
    return (
      <div className="chart-empty">
        <p>Tidak ada data</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={90}
          paddingAngle={3}
          dataKey="count"
          nameKey="label"
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} stroke="white" strokeWidth={2} />
          ))}
        </Pie>
        <Tooltip
          content={({ active, payload }) => {
            if (active && payload && payload.length) {
              const data = payload[0].payload;
              return (
                <div className="chart-tooltip">
                  <p className="tooltip-title">{data.label}</p>
                  <p className="tooltip-value">{data.count.toLocaleString('id-ID')} ({data.percentage}%)</p>
                </div>
              );
            }
            return null;
          }}
        />
        <Legend
          verticalAlign="bottom"
          height={36}
          formatter={(value) => <span style={{ color: '#64748B', fontSize: '12px' }}>{value}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
