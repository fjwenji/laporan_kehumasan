import { useState, useEffect } from 'react';
import { format } from 'date-fns';
import { jobsApi } from '../services/api';
import type { JobItem } from '../types';
import './JobStatusTable.css';

interface Props {
  limit?: number;
}

const STATUS_BADGE: Record<string, { variant: string; label: string }> = {
  QUEUED: { variant: 'info', label: 'Queued' },
  RUNNING: { variant: 'running', label: 'Running' },
  SUCCESS: { variant: 'success', label: 'Success' },
  PARTIAL_SUCCESS: { variant: 'warning', label: 'Partial' },
  FAILED: { variant: 'danger', label: 'Failed' },
  RATE_LIMITED: { variant: 'danger', label: 'Rate Limited' },
  SKIPPED: { variant: 'info', label: 'Skipped' },
};

export default function JobStatusTable({ limit = 20 }: Props) {
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchJobs = async () => {
      setIsLoading(true);
      try {
        const data = await jobsApi.list(limit);
        setJobs((data as { jobs: JobItem[] }).jobs);
      } catch (error) {
        console.error('Failed to fetch jobs:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchJobs();
  }, [limit]);

  if (isLoading) {
    return (
      <div className="jobs-loading">
        <div className="skeleton-row" />
        <div className="skeleton-row" />
        <div className="skeleton-row" />
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="jobs-empty">
        <p>Tidak ada job scraping</p>
      </div>
    );
  }

  return (
    <div className="jobs-table-container">
      <table className="jobs-table">
        <thead>
          <tr>
            <th>Job ID</th>
            <th>Type</th>
            <th>Status</th>
            <th>Dibuat</th>
            <th>Akun</th>
            <th>Ditemukan</th>
            <th>Disimpan</th>
            <th>Gagal</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => {
            const status = STATUS_BADGE[job.status] || { variant: 'info', label: job.status };
            return (
              <tr key={job.id} className={job.status === 'RUNNING' ? 'row-running' : ''}>
                <td className="job-id">
                  <code>{job.job_id.substring(0, 16)}...</code>
                </td>
                <td>{job.job_type}</td>
                <td>
                  <span className={`badge badge-${status.variant}`}>{status.label}</span>
                </td>
                <td className="job-time">
                  {job.created_at ? format(new Date(job.created_at), 'dd/MM HH:mm') : '-'}
                </td>
                <td>{job.total_accounts}</td>
                <td>{job.total_posts_found}</td>
                <td>{job.total_posts_inserted}</td>
                <td className={job.total_failed > 0 ? 'text-danger' : ''}>
                  {job.total_failed}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
