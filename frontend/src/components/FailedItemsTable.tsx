import { useState, useEffect } from 'react';
import { format } from 'date-fns';
import { jobsApi } from '../services/api';
import type { FailedItem } from '../types';
import './FailedItemsTable.css';

export default function FailedItemsTable() {
  const [items, setItems] = useState<FailedItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchFailedItems = async () => {
      setIsLoading(true);
      try {
        const data = await jobsApi.getFailed(undefined, 100);
        setItems((data as { items: FailedItem[] }).items);
      } catch (error) {
        console.error('Failed to fetch failed items:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchFailedItems();
  }, []);

  if (isLoading) {
    return (
      <div className="failed-loading">
        {[1, 2, 3].map((i) => (
          <div key={i} className="skeleton-row" />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="failed-empty">
        <p>Tidak ada item yang gagal</p>
      </div>
    );
  }

  return (
    <div className="failed-table-container">
      <table className="failed-table">
        <thead>
          <tr>
            <th>Job ID</th>
            <th>Username</th>
            <th>Post URL</th>
            <th>Error Type</th>
            <th>Reason</th>
            <th>Waktu</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td className="job-id-cell">
                <code>{item.job_id.substring(0, 16)}...</code>
              </td>
              <td>@{item.username || '-'}</td>
              <td className="url-cell">
                {item.post_url ? (
                  <a
                    href={item.post_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="external-link"
                  >
                    Link
                  </a>
                ) : (
                  '-'
                )}
              </td>
              <td>
                <span className={`error-type ${item.error_type?.toLowerCase() || 'unknown'}`}>
                  {item.error_type || 'Unknown'}
                </span>
              </td>
              <td className="reason-cell">{item.reason || '-'}</td>
              <td className="time-cell">
                {item.created_at
                  ? format(new Date(item.created_at), 'dd/MM HH:mm')
                  : '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
