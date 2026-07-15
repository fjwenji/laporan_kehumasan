import { useState, useEffect } from 'react';
import { RefreshCw, Download, Search, Filter, AlertCircle, FileText, ArrowLeft, AlignLeft } from 'lucide-react';
import { stagingApi } from '../services/api';
import Sidebar from '../components/Sidebar';
import { useSidebar } from '../contexts/SidebarContext';
import './StagingDataPage.css';

interface StagingJob {
  job_id: string;
  mode: string;
  file_path: string;
  file_size_bytes: number;
  file_size_mb: number;
  row_count: number;
  created_at: string;
  modified_at: string;
}

interface StagingRow {
  job_id: string;
  account_id: number | null;
  username: string;
  unit: string;
  zona_waktu: string;
  shortcode: string;
  post_url: string;
  posted_at: string | null;
  media_type: string;
  caption: string;
  like_count: number | null;
  comment_count: number | null;
  view_count: number | null;
  play_count: number | null;
  share_count: number | null;
  save_count: number | null;
  status_staging: string;
  catatan: string;
  scraped_at: string;
}

export default function StagingDataPage() {
  const { toggleMobile, togglePinned } = useSidebar();
  const [jobs, setJobs] = useState<StagingJob[]>([]);
  const [selectedJob, setSelectedJob] = useState<StagingJob | null>(null);
  const [rows, setRows] = useState<StagingRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingRows, setLoadingRows] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [limit] = useState(50);
  const [filterUsername, setFilterUsername] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterMediaType, setFilterMediaType] = useState('');

  const loadJobs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await stagingApi.listJobs();
      setJobs(data.jobs || []);
    } catch (err) {
      setError('Gagal memuat daftar staging job');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadRows = async (job: StagingJob, pageNum: number = 0) => {
    setLoadingRows(true);
    setError(null);
    try {
      const data = await stagingApi.getJobRows(
        job.job_id, job.mode, limit, pageNum * limit,
        filterUsername || undefined, filterStatus || undefined, filterMediaType || undefined
      );
      setRows(data.rows || []);
      setTotal(data.total || 0);
      setPage(pageNum);
    } catch (err) {
      setError('Gagal memuat data staging');
      console.error(err);
    } finally {
      setLoadingRows(false);
    }
  };

  useEffect(() => { loadJobs(); }, []);
  useEffect(() => { if (selectedJob) loadRows(selectedJob, 0); }, [filterUsername, filterStatus, filterMediaType]);

  const handleJobSelect = (job: StagingJob) => {
    setSelectedJob(job);
    setFilterUsername('');
    setFilterStatus('');
    setFilterMediaType('');
    setPage(0);
  };

  const handleDownload = async (job: StagingJob) => {
    try { await stagingApi.downloadJob(job.job_id, job.mode); }
    catch (err) { setError('Gagal mengunduh file'); console.error(err); }
  };

  const handleBack = () => {
    setSelectedJob(null);
    setRows([]);
    setTotal(0);
  };

  const handleHeaderToggle = () => {
    if (window.innerWidth < 1024) {
      toggleMobile();
    } else {
      togglePinned();
    }
  };

  const getStatusBadgeClass = (status: string) => {
    if (status === 'VALID') return 'badge-valid';
    if (status === 'INVALID') return 'badge-invalid';
    if (status === 'FAILED') return 'badge-failed';
    return 'badge-default';
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleString('id-ID', {
        day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
      });
    } catch { return dateStr; }
  };

  const formatNumber = (num: number | null) => num === null || num === undefined ? '-' : num.toLocaleString('id-ID');
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="app-shell">
      <Sidebar />

      <div className="app-main">
        <header className="main-header">
          <div className="header-left">
            <button className="header-icon-btn" onClick={handleHeaderToggle} aria-label="Toggle sidebar">
              <AlignLeft size={20} />
            </button>
            <div className="header-title-group">
              <h1 className="header-title">Data Persiapan</h1>
              <p className="header-subtitle">
                {selectedJob ? `Job: ${selectedJob.job_id}` : `${jobs.length} file ditemukan`}
              </p>
            </div>
          </div>
          <div className="header-actions">
            <button className="btn btn-ghost" onClick={selectedJob ? () => loadRows(selectedJob, page) : loadJobs} disabled={loading}>
              <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
              <span>Refresh</span>
            </button>
            {selectedJob && (
              <button className="btn btn-gold" onClick={() => handleDownload(selectedJob)}>
                <Download size={18} />
                <span>Download</span>
              </button>
            )}
          </div>
        </header>

        <main className="dashboard-content">
          {selectedJob && (
            <button className="back-btn-top" onClick={handleBack}>
              <ArrowLeft size={16} />
              Kembali ke daftar
            </button>
          )}

          {error && (
            <div className="error-banner">
              <AlertCircle size={16} />
              {error}
              <button onClick={() => setError(null)}>×</button>
            </div>
          )}

          {!selectedJob ? (
            <div className="jobs-list">
              {loading ? (
                <div className="loading-state"><RefreshCw size={32} className="spin" /><p>Memuat daftar staging...</p></div>
              ) : jobs.length === 0 ? (
                <div className="empty-state">
                  <FileText size={48} />
                  <h3>Tidak ada file staging</h3>
                  <p>File staging akan muncul setelah scraping selesai dijalankan.</p>
                </div>
              ) : (
                <div className="jobs-grid">
                  {jobs.map((job) => (
                    <div key={`${job.mode}-${job.job_id}`} className="job-card" onClick={() => handleJobSelect(job)}>
                      <div className="job-header">
                        <span className={`job-mode mode-${job.mode}`}>{job.mode.toUpperCase()}</span>
                        <span className="job-id">{job.job_id}</span>
                      </div>
                      <div className="job-stats">
                        <div className="stat"><span className="stat-value">{formatNumber(job.row_count)}</span><span className="stat-label">Rows</span></div>
                        <div className="stat"><span className="stat-value">{job.file_size_mb}</span><span className="stat-label">MB</span></div>
                      </div>
                      <div className="job-footer">
                        <span className="job-date">Dimodifikasi: {formatDate(job.modified_at)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="staging-detail">
              <div className="filters-bar">
                <div className="filter-group"><Search size={16} /><input type="text" placeholder="Filter username..." value={filterUsername} onChange={(e) => setFilterUsername(e.target.value)} /></div>
                <div className="filter-group">
                  <Filter size={16} />
                  <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
                    <option value="">Semua Status</option>
                    <option value="VALID">Valid</option>
                    <option value="INVALID">Invalid</option>
                    <option value="FAILED">Failed</option>
                  </select>
                </div>
                <div className="filter-group">
                  <Filter size={16} />
                  <select value={filterMediaType} onChange={(e) => setFilterMediaType(e.target.value)}>
                    <option value="">Semua Media</option>
                    <option value="IMAGE">Image</option>
                    <option value="CAROUSEL">Carousel</option>
                    <option value="REELS">Reels</option>
                    <option value="VIDEO">Video</option>
                    <option value="UNKNOWN">Unknown</option>
                  </select>
                </div>
                {(filterUsername || filterStatus || filterMediaType) && (
                  <button className="btn btn-ghost" onClick={() => { setFilterUsername(''); setFilterStatus(''); setFilterMediaType(''); }}>Clear</button>
                )}
              </div>

              {loadingRows ? (
                <div className="loading-state"><RefreshCw size={32} className="spin" /><p>Memuat data staging...</p></div>
              ) : rows.length === 0 ? (
                <div className="empty-state"><FileText size={48} /><h3>Tidak ada data</h3><p>Coba ubah filter atau pilih job lain.</p></div>
              ) : (
                <>
                  <div className="table-container">
                    <table className="staging-table">
                      <thead>
                        <tr><th>Username</th><th>Unit</th><th>Tanggal Posting</th><th>Media</th><th>Like</th><th>Comment</th><th>View</th><th>Status</th><th>Catatan</th></tr>
                      </thead>
                      <tbody>
                        {rows.map((row, idx) => (
                          <tr key={`${row.shortcode}-${idx}`}>
                            <td className="cell-username">@{row.username}</td>
                            <td className="cell-unit">{row.unit || '-'}</td>
                            <td className="cell-date">{formatDate(row.posted_at)}</td>
                            <td className="cell-media"><span className={`media-badge media-${(row.media_type || 'unknown').toLowerCase()}`}>{row.media_type || 'unknown'}</span></td>
                            <td className="cell-number">{formatNumber(row.like_count)}</td>
                            <td className="cell-number">{formatNumber(row.comment_count)}</td>
                            <td className="cell-number">{formatNumber(row.view_count)}</td>
                            <td className="cell-status"><span className={`status-badge ${getStatusBadgeClass(row.status_staging)}`}>{row.status_staging}</span></td>
                            <td className="cell-note" title={row.catatan}>{row.catatan ? row.catatan.substring(0, 50) + (row.catatan.length > 50 ? '...' : '') : '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="pagination">
                    <button className="btn btn-secondary" disabled={page === 0 || loadingRows} onClick={() => loadRows(selectedJob, page - 1)}>← Prev</button>
                    <span className="page-info">Halaman {page + 1} dari {totalPages || 1}</span>
                    <button className="btn btn-secondary" disabled={page >= totalPages - 1 || loadingRows} onClick={() => loadRows(selectedJob, page + 1)}>Next →</button>
                  </div>
                </>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
