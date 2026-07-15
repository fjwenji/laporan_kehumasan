import { useState, useEffect } from 'react';
import { format } from 'date-fns';
import { AlignLeft } from 'lucide-react';
import { jobsApi } from '../services/api';
import Sidebar from '../components/Sidebar';
import { useSidebar } from '../contexts/SidebarContext';
import JobStatusTable from '../components/JobStatusTable';
import FailedItemsTable from '../components/FailedItemsTable';
import './JobMonitoringPage.css';

export default function JobMonitoringPage() {
  const { toggleMobile, togglePinned } = useSidebar();
  const [workerStatus, setWorkerStatus] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'jobs' | 'failed'>('jobs');

  const fetchWorkerStatus = async () => {
    try {
      const status = await jobsApi.getWorkerStatus();
      setWorkerStatus(status);
    } catch (error) {
      console.error('Failed to fetch worker status:', error);
    }
  };

  useEffect(() => {
    fetchWorkerStatus();
    const interval = setInterval(fetchWorkerStatus, 10000);
    return () => clearInterval(interval);
  }, []);

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
              <h1 className="header-title">Job Monitoring</h1>
              <p className="header-subtitle">Monitoring scraping jobs dan failed items</p>
            </div>
          </div>
        </header>

        <main className="dashboard-content">
          <div className="worker-status-card">
            <div className={`worker-status-indicator ${workerStatus?.is_alive ? 'alive' : 'dead'}`} />
            <div className="worker-status-content">
              <h3>Worker {workerStatus?.is_alive ? 'Online' : 'Offline'}</h3>
              <p>
                {workerStatus?.is_alive
                  ? workerStatus?.status === 'idle'
                    ? 'Worker idle / siap menerima job'
                    : `Job ${workerStatus?.current_job_id?.substring(0, 20)}... (${workerStatus?.current_job_status})`
                  : 'Tidak ada worker aktif'}
              </p>
              {workerStatus?.last_heartbeat && (
                <p className="worker-heartbeat">
                  Last heartbeat: {format(new Date(workerStatus.last_heartbeat), 'dd/MM/yyyy HH:mm:ss')}
                </p>
              )}
            </div>
          </div>
          <div className="tabs">
            <button
              className={`tab ${activeTab === 'jobs' ? 'active' : ''}`}
              onClick={() => setActiveTab('jobs')}
            >
              Jobs
            </button>
            <button
              className={`tab ${activeTab === 'failed' ? 'active' : ''}`}
              onClick={() => setActiveTab('failed')}
            >
              Failed Items
            </button>
          </div>
          <div className="tab-content">
            {activeTab === 'jobs' ? (
              <JobStatusTable limit={50} />
            ) : (
              <FailedItemsTable />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
