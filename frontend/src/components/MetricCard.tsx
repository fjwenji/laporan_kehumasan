import React from 'react';
import './MetricCard.css';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'gold';
  isLoading?: boolean;
}

export default function MetricCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  variant = 'default',
  isLoading = false,
}: MetricCardProps) {
  if (isLoading) {
    return (
      <div className="metric-card metric-card-loading">
        <div className="metric-icon skeleton" />
        <div className="metric-content">
          <div className="metric-title skeleton-text" />
          <div className="metric-value skeleton-text" style={{ width: '60%' }} />
        </div>
      </div>
    );
  }

  return (
    <div className={`metric-card metric-card-${variant}`}>
      <div className="metric-icon">
        {icon || (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        )}
      </div>
      <div className="metric-content">
        <div className="metric-title">{title}</div>
        <div className="metric-value">
          {typeof value === 'number' ? value.toLocaleString('id-ID') : value}
        </div>
        {subtitle && <div className="metric-subtitle">{subtitle}</div>}
        {trend && (
          <div className={`metric-trend ${trend.isPositive ? 'positive' : 'negative'}`}>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className={trend.isPositive ? '' : 'rotate-180'}
            >
              <path d="M7 17l5-5 5 5M7 7l5 5 5-5" />
            </svg>
            <span>{Math.abs(trend.value)}%</span>
          </div>
        )}
      </div>
      <div className="metric-glow" />
    </div>
  );
}
