import { useState, useEffect } from 'react';
import { format, subDays } from 'date-fns';
import {
  Users,
  Image,
  LayoutGrid,
  Play,
  Eye,
  ThumbsUp,
  MessageCircle,
  TrendingUp,
  RefreshCw,
  Filter,
  AlignLeft,
  UserCheck,
  UserPlus,
} from 'lucide-react';
import { dashboardApi } from '../services/api';
import Sidebar from '../components/Sidebar';
import MetricCard from '../components/MetricCard';
import EngagementBarChart from '../components/EngagementBarChart';
import MediaTypeChart from '../components/MediaTypeChart';
import PostsByAccountChart from '../components/PostsByAccountChart';
import { useSidebar } from '../contexts/SidebarContext';
import type { DashboardSummary, ChartData, AccountOption } from '../types';
import './Dashboard.css';
import './FooterCopyright.css';

export default function UserDashboard() {
  const { toggleMobile, togglePinned } = useSidebar();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [chartData, setChartData] = useState<ChartData | null>(null);
  const [accounts, setAccounts] = useState<AccountOption[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const [periodStart, setPeriodStart] = useState(format(subDays(new Date(), 7), 'yyyy-MM-dd'));
  const [periodEnd, setPeriodEnd] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [selectedAccount, setSelectedAccount] = useState('');

  const fetchData = async () => {
    setIsLoading(true);
    setError('');
    try {
      const [summaryData, chartsData, accountsData] = await Promise.all([
        dashboardApi.getSummary(periodStart, periodEnd, selectedAccount || undefined),
        dashboardApi.getCharts(periodStart, periodEnd),
        dashboardApi.getAccounts(),
      ]);
      setSummary(summaryData as DashboardSummary);
      setChartData(chartsData as ChartData);
      setAccounts((accountsData as { accounts: AccountOption[] }).accounts || []);
    } catch (err: any) {
      console.error('Failed to fetch data:', err);
      setError(err.message || 'Gagal mengambil data dari server');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [periodStart, periodEnd, selectedAccount]);

  const handleRefresh = () => {
    fetchData();
  };

  const handleHeaderToggle = () => {
    if (window.innerWidth < 1024) {
      toggleMobile();
    } else {
      togglePinned();
    }
  };

  const formatNumber = (num: number | undefined | null, showZeroAsDash = false): string => {
    if (num === undefined || num === null) return '-';
    if (showZeroAsDash && num === 0) return '-';
    return num.toLocaleString('id-ID');
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
              <h1 className="header-title">Mayz Monitoring</h1>
              <p className="header-subtitle">Monitoring Instagram DJPb</p>
            </div>
          </div>
          <div className="header-actions">
            <button className="btn btn-ghost" onClick={handleRefresh} disabled={isLoading}>
              <RefreshCw size={18} className={isLoading ? 'animate-spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>
        </header>

        <main className="dashboard-content">
          {error && (
            <div className="dashboard-error">
              <p>{error}</p>
              <button className="btn btn-ghost" onClick={handleRefresh}>
                <RefreshCw size={16} />
                <span>Coba Lagi</span>
              </button>
            </div>
          )}
          <div className="filter-section">
            <div className="filter-card">
              <div className="filter-group">
                <label>Periode</label>
                <div className="date-inputs">
                  <input
                    type="date"
                    value={periodStart}
                    onChange={(e) => setPeriodStart(e.target.value)}
                    className="input"
                  />
                  <span>s/d</span>
                  <input
                    type="date"
                    value={periodEnd}
                    onChange={(e) => setPeriodEnd(e.target.value)}
                    className="input"
                  />
                </div>
              </div>
              <div className="filter-group">
                <label>
                  <Filter size={14} />
                  Akun
                </label>
                <select
                  value={selectedAccount}
                  onChange={(e) => setSelectedAccount(e.target.value)}
                  className="input"
                >
                  <option value="">Semua Akun</option>
                  {accounts.map((acc) => (
                    <option key={acc.username} value={acc.username}>
                      {acc.nama_unit || acc.username}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
          <div className="metrics-grid">
            <MetricCard
              title="Akun Aktif"
              value={summary?.active_accounts || 0}
              subtitle={`dari ${summary?.total_accounts || 0} total`}
              icon={<Users size={24} />}
              isLoading={isLoading}
            />
            <MetricCard
              title="Total Followers"
              value={summary?.total_followers || 0}
              subtitle={`avg ${formatNumber(summary?.avg_followers)}/akun`}
              icon={<UserCheck size={24} />}
              isLoading={isLoading}
            />
            <MetricCard
              title="Total Following"
              value={summary?.total_following || 0}
              subtitle={`${summary?.accounts_with_followers || 0} akun terukur`}
              icon={<UserPlus size={24} />}
              isLoading={isLoading}
            />
          </div>
          <div className="metrics-grid">
            <MetricCard
              title="Total Postingan"
              value={summary?.total_posts || 0}
              subtitle={`${summary?.new_posts || 0} postingan baru`}
              icon={<LayoutGrid size={24} />}
              isLoading={isLoading}
            />
            <MetricCard
              title="Total Like"
              value={summary?.total_likes || 0}
              icon={<ThumbsUp size={24} />}
              isLoading={isLoading}
            />
            <MetricCard
              title="Total Komentar"
              value={summary?.total_comments || 0}
              icon={<MessageCircle size={24} />}
              isLoading={isLoading}
            />
            <MetricCard
              title="Total Engagement"
              value={summary?.total_engagement || 0}
              icon={<TrendingUp size={24} />}
              variant="gold"
              isLoading={isLoading}
            />
            <MetricCard
              title="Total Views"
              value={summary?.total_views || 0}
              subtitle="Hanya Reels/Video"
              icon={<Eye size={24} />}
              isLoading={isLoading}
            />
          </div>
          <div className="media-summary">
            <div className="media-item">
              <Image size={20} />
              <span className="media-count">{summary?.media_image || 0}</span>
              <span className="media-label">Gambar</span>
            </div>
            <div className="media-item">
              <LayoutGrid size={20} />
              <span className="media-count">{summary?.media_carousel || 0}</span>
              <span className="media-label">Carousel</span>
            </div>
            <div className="media-item">
              <Play size={20} />
              <span className="media-count">{summary?.media_reels || 0}</span>
              <span className="media-label">Reels</span>
            </div>
            {summary?.media_unclassified && summary.media_unclassified > 0 ? (
              <div className="media-item media-warning">
                <Eye size={20} />
                <span className="media-count">{summary.media_unclassified}</span>
                <span className="media-label">Perlu Review</span>
              </div>
            ) : null}
          </div>
          <div className="charts-grid">
            <div className="chart-card">
              <div className="chart-header">
                <h3>Engagement per Akun</h3>
              </div>
              <div className="chart-body">
                {isLoading ? (
                  <div className="chart-loading">
                    <div className="loading-spinner" />
                  </div>
                ) : (
                  <EngagementBarChart data={chartData?.engagement_by_account || []} />
                )}
              </div>
            </div>

            <div className="chart-card">
              <div className="chart-header">
                <h3>Komposisi Media</h3>
              </div>
              <div className="chart-body">
                {isLoading ? (
                  <div className="chart-loading">
                    <div className="loading-spinner" />
                  </div>
                ) : (
                  <MediaTypeChart data={chartData?.media_type_breakdown || []} />
                )}
              </div>
            </div>

            <div className="chart-card chart-wide">
              <div className="chart-header">
                <h3>Jumlah Postingan per Akun</h3>
              </div>
              <div className="chart-body">
                {isLoading ? (
                  <div className="chart-loading">
                    <div className="loading-spinner" />
                  </div>
                ) : (
                  <PostsByAccountChart data={chartData?.posts_by_account || []} />
                )}
              </div>
            </div>
          </div>
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
