import { formatDistanceToNow } from 'date-fns';
import { Bell, AlertTriangle, AlertCircle, Info } from 'lucide-react';
import type { AlertItem } from '../types';
import './AlertPanel.css';

interface Props {
  alerts: AlertItem[];
}

const ALERT_ICONS = {
  info: Info,
  warning: AlertTriangle,
  danger: AlertCircle,
};

const ALERT_COLORS = {
  info: { bg: '#EFF6FF', border: '#3B82F6', color: '#3B82F6' },
  warning: { bg: '#FFFBEB', border: '#F59E0B', color: '#F59E0B' },
  danger: { bg: '#FEF2F2', border: '#DC2626', color: '#DC2626' },
};

export default function AlertPanel({ alerts }: Props) {
  if (!alerts || alerts.length === 0) {
    return null;
  }

  return (
    <div className="alert-panel">
      <div className="alert-panel-header">
        <Bell size={18} />
        <h3>Notifikasi & Alert</h3>
        <span className="alert-count">{alerts.length}</span>
      </div>
      <div className="alert-list">
        {alerts.slice(0, 5).map((alert) => {
          const Icon = ALERT_ICONS[alert.severity as keyof typeof ALERT_ICONS] || Info;
          const colors = ALERT_COLORS[alert.severity as keyof typeof ALERT_COLORS] || ALERT_COLORS.info;

          return (
            <div
              key={alert.id}
              className="alert-item"
              style={{
                backgroundColor: colors.bg,
                borderColor: colors.border,
              }}
            >
              <div className="alert-icon" style={{ color: colors.color }}>
                <Icon size={16} />
              </div>
              <div className="alert-content">
                <div className="alert-title">{alert.title}</div>
                <div className="alert-message">{alert.message}</div>
                <div className="alert-time">
                  {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
