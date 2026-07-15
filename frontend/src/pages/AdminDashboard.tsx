import { useState, useEffect } from 'react';
import {
  Activity,
  AlertTriangle,
  RefreshCw,
  Play,
  AlignLeft,
} from 'lucide-react';
import { jobsApi } from '../services/api';
import Sidebar from '../components/Sidebar';
import { useSidebar } from '../contexts/SidebarContext';
import './AdminDashboard.css';
import './FooterCopyright.css';

export default function AdminDashboard() {
  const { toggleMobile, togglePinned } = useSidebar();
  const [data, setData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchData = async () => {
    setIsLoading(true);
    setError('');
    try {
      const flowData = await jobsApi.getNodeFlow();
      setData(flowData);
    } catch (err: any) {
      console.error('Failed to fetch:', err);
      setError(err.message || 'Gagal mengambil data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleTrigger = async () => {
    try {
      await jobsApi.trigger('LATEST_SYNC');
      alert('Job berhasil dibuat!');
      fetchData();
    } catch (err: any) {
      alert(err.message || 'Gagal');
    }
  };

  const handleHeaderToggle = () => {
    if (window.innerWidth < 1024) {
      toggleMobile();
    } else {
      togglePinned();
    }
  };

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
              <h1 className="header-title">Admin Panel</h1>
              <p className="header-subtitle">Monitoring Sistem Scraping</p>
            </div>
          </div>
          <div className="header-actions">
            <button className="btn btn-ghost" onClick={fetchData} disabled={isLoading}>
              <RefreshCw size={18} className={isLoading ? 'animate-spin' : ''} />
              <span>Refresh</span>
            </button>
            <button className="btn btn-gold" onClick={handleTrigger}>
              <Play size={18} />
              <span>Trigger Job</span>
            </button>
          </div>
        </header>

        <main className="dashboard-content">
          {error && (
            <div className="error-message">
              <p>Error: {error}</p>
              <button className="btn btn-ghost" onClick={fetchData}>Coba Lagi</button>
            </div>
          )}

          {isLoading ? (
            <div className="loading-state">
              <div className="loading-spinner" />
              <p>Memuat...</p>
            </div>
          ) : data ? (
            <>
              <div className="status-banner">
                <div className="status-icon">
                  {data.worker_status === 'alive' ? (
                    <Activity size={24} />
                  ) : (
                    <AlertTriangle size={24} />
                  )}
                </div>
                <div className="status-content">
                  <h3>Worker: {data.worker_status === 'alive' ? 'Online' : 'Offline'}</h3>
                  <p>{data.worker_last_heartbeat ? `Last heartbeat: ${new Date(data.worker_last_heartbeat).toLocaleString('id-ID')}` : 'No heartbeat'}</p>
                </div>
              </div>
              <div className="nodes-grid">
                {(data.nodes || []).map((node: any) => (
                  <div key={node.id} className="node-card">
                    <div className="node-name">{node.name}</div>
                    <div className={`node-status status-${node.status}`}>{node.status}</div>
                    <div className="node-desc">{node.description}</div>
                  </div>
                ))}
              </div>
              {data.current_job && (
                <div className="current-job">
                  <h3>Current Job</h3>
                  <pre>{JSON.stringify(data.current_job, null, 2)}</pre>
                </div>
              )}
            </>
          ) : (
            <div className="empty-state">
              <p>Tidak ada data</p>
            </div>
          )}
        </main>
        <footer className="page-footer">
          <p className="footer-copyright">
            © {new Date().getFullYear()} DJPb Mayz Monitoring System. Hak cipta dilindungi.
          </p>
        </footer>
      </div>
    </div>
  );
}
