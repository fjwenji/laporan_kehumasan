import React from 'react';
import { Clock, CheckCircle, AlertTriangle, XCircle, Loader, Activity } from 'lucide-react';
import type { NodeFlowItem } from '../types';
import './ScrapingNodeFlow.css';

interface Props {
  nodes: NodeFlowItem[];
}

const STATUS_CONFIG = {
  idle: { icon: Clock, color: '#94A3B8', label: 'Idle', bgColor: '#F1F5F9' },
  running: { icon: Loader, color: '#3B82F6', label: 'Running', bgColor: '#EFF6FF' },
  success: { icon: CheckCircle, color: '#16A34A', label: 'Success', bgColor: '#F0FDF4' },
  warning: { icon: AlertTriangle, color: '#F59E0B', label: 'Warning', bgColor: '#FFFBEB' },
  failed: { icon: XCircle, color: '#DC2626', label: 'Failed', bgColor: '#FEF2F2' },
  stuck: { icon: Activity, color: '#7C3AED', label: 'Stuck', bgColor: '#F5F3FF' },
};

export default function ScrapingNodeFlow({ nodes }: Props) {
  if (!nodes || nodes.length === 0) {
    return (
      <div className="node-flow-empty">
        <p>Tidak ada data workflow</p>
      </div>
    );
  }

  return (
    <div className="node-flow">
      <div className="node-flow-track">
        {nodes.map((node, index) => {
          const config = STATUS_CONFIG[node.status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.idle;
          const Icon = config.icon;
          const isLast = index === nodes.length - 1;

          return (
            <React.Fragment key={node.id}>
              <div className="node-item">
                <div
                  className={`node-circle ${node.status}`}
                  style={{ backgroundColor: config.bgColor, borderColor: config.color }}
                >
                  <Icon
                    size={24}
                    style={{ color: config.color }}
                    className={node.status === 'running' ? 'animate-spin' : ''}
                  />
                </div>
                <div className="node-info">
                  <div className="node-name" style={{ color: config.color }}>
                    {node.name}
                  </div>
                  <div className="node-desc">{node.description || config.label}</div>
                  {node.last_updated && (
                    <div className="node-time">
                      {new Date(node.last_updated).toLocaleString('id-ID', {
                        day: '2-digit',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </div>
                  )}
                </div>
                {node.details && (
                  <div className="node-details">
                    {Object.entries(node.details).map(([key, value]) => (
                      <span key={key} className="detail-badge">
                        {key}: {String(value)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              {!isLast && (
                <div className={`node-connector ${node.status}`} />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
