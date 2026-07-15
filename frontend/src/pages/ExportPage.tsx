import { useState, useEffect } from 'react';
import {
  FileSpreadsheet,
  Download,
  Calendar,
  Users,
  CheckCircle,
  XCircle,
  Loader2,
  AlignLeft,
} from 'lucide-react';
import { dashboardApi, exportApi } from '../services/api';
import Sidebar from '../components/Sidebar';
import { useSidebar } from '../contexts/SidebarContext';
import './ExportPage.css';
import './FooterCopyright.css';

interface AccountOption {
  username: string;
  nama_unit: string;
}

export default function ExportPage() {
  const { toggleMobile, togglePinned } = useSidebar();
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exportSuccess, setExportSuccess] = useState(false);

  const [periodStart, setPeriodStart] = useState(() => {
    const date = new Date();
    date.setDate(date.getDate() - 7);
    return date.toISOString().split('T')[0];
  });
  const [periodEnd, setPeriodEnd] = useState(() => {
    return new Date().toISOString().split('T')[0];
  });
  const [selectedAccount, setSelectedAccount] = useState('');
  const [accounts, setAccounts] = useState<AccountOption[]>([]);
  const [loadingAccounts, setLoadingAccounts] = useState(true);

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    setLoadingAccounts(true);
    try {
      const data = await dashboardApi.getAccounts() as { accounts: AccountOption[] };
      setAccounts(data.accounts || []);
    } catch (error) {
      console.error('Failed to fetch accounts:', error);
    } finally {
      setLoadingAccounts(false);
    }
  };

  const handleHeaderToggle = () => {
    if (window.innerWidth < 1024) {
      toggleMobile();
    } else {
      togglePinned();
    }
  };

  const handleExport = async () => {
    setExporting(true);
    setError(null);
    setExportSuccess(false);

    try {
      await exportApi.downloadExcel(periodStart, periodEnd, selectedAccount || undefined);
      setExportSuccess(true);
      setTimeout(() => setExportSuccess(false), 5000);
    } catch (error: any) {
      setError(error.message || 'Gagal mengunduh file Excel');
    } finally {
      setExporting(false);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('id-ID', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
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
              <h1 className="header-title">Export Excel</h1>
              <p className="header-subtitle">Unduh laporan publikasi Instagram</p>
            </div>
          </div>
        </header>

        <main className="dashboard-content">
          <div className="export-container">
            <div className="export-info-card">
              <div className="info-icon">
                <FileSpreadsheet size={24} />
              </div>
              <div className="info-content">
                <h3>Unduh Laporan Excel</h3>
                <p>
                  Unduh laporan publikasi Instagram berdasarkan periode dan akun yang dipilih.
                  File Excel akan memuat data yang telah dikumpulkan dari akun Instagram Kanwil DJPb.
                </p>
              </div>
            </div>

            <div className="export-card">
              <h3 className="card-title">
                <Calendar size={18} />
                Filter Laporan
              </h3>

              <div className="filter-grid">
                <div className="filter-group">
                  <label>
                    <Calendar size={14} />
                    Tanggal Mulai
                  </label>
                  <input
                    type="date"
                    value={periodStart}
                    onChange={(e) => setPeriodStart(e.target.value)}
                    className="input"
                  />
                </div>

                <div className="filter-group">
                  <label>
                    <Calendar size={14} />
                    Tanggal Selesai
                  </label>
                  <input
                    type="date"
                    value={periodEnd}
                    onChange={(e) => setPeriodEnd(e.target.value)}
                    className="input"
                  />
                </div>

                <div className="filter-group full-width">
                  <label>
                    <Users size={14} />
                    Pilih Akun / Kanwil
                  </label>
                  <select
                    value={selectedAccount}
                    onChange={(e) => setSelectedAccount(e.target.value)}
                    className="input"
                    disabled={loadingAccounts}
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

              <div className="export-action">
                <button
                  className="btn btn-primary btn-export"
                  onClick={handleExport}
                  disabled={exporting}
                >
                  {exporting ? (
                    <>
                      <Loader2 size={20} className="animate-spin" />
                      Mengunduh...
                    </>
                  ) : (
                    <>
                      <Download size={20} />
                      Unduh Excel
                    </>
                  )}
                </button>
              </div>

              {exportSuccess && (
                <div className="alert alert-success">
                  <CheckCircle size={18} />
                  <span>File Excel berhasil di-download!</span>
                </div>
              )}

              {error && (
                <div className="alert alert-error">
                  <XCircle size={18} />
                  <span>{error}</span>
                </div>
              )}
            </div>

            <div className="export-card">
              <h3 className="card-title">
                <FileSpreadsheet size={18} />
                Isi Laporan
              </h3>

              <div className="preview-content">
                <p className="preview-label">File Excel akan memuat:</p>
                <ul className="preview-list">
                  <li>
                    <CheckCircle size={14} />
                    <span>Rekap performa publikasi</span>
                  </li>
                  <li>
                    <CheckCircle size={14} />
                    <span>Daftar postingan</span>
                  </li>
                  <li>
                    <CheckCircle size={14} />
                    <span>Jumlah like, komentar, dan views</span>
                  </li>
                  <li>
                    <CheckCircle size={14} />
                    <span>Engagement</span>
                  </li>
                  <li>
                    <CheckCircle size={14} />
                    <span>Tanggal laporan dibuat</span>
                  </li>
                </ul>

                <div className="preview-period">
                  <Calendar size={14} />
                  <span>
                    Periode: {formatDate(periodStart)} - {formatDate(periodEnd)}
                  </span>
                </div>
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
