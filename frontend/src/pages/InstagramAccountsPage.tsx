import { useState, useEffect, useRef } from 'react';
import {
  Users,
  Plus,
  Search,
  Upload,
  Edit2,
  Trash2,
  ToggleLeft,
  ToggleRight,
  X,
  AlertCircle,
  CheckCircle,
  XCircle,
  Filter,
  RefreshCw,
  Lock,
  AlignLeft,
} from 'lucide-react';
import { instagramAccountsApi } from '../services/api';
import { useAuth } from '../App';
import Sidebar from '../components/Sidebar';
import { useSidebar } from '../contexts/SidebarContext';
import './InstagramAccountsPage.css';

interface Account {
  id: number;
  username: string;
  nama_unit: string;
  jenis_akun: string;
  status: string;
  notes?: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

interface PreviewRow {
  row_number: number;
  username: string;
  nama_unit: string;
  jenis_akun: string;
  status: string;
  is_valid: boolean;
  error_message?: string;
  is_duplicate: boolean;
  existing_id?: number;
}

export default function InstagramAccountsPage() {
  const { user } = useAuth();
  const { toggleMobile, togglePinned } = useSidebar();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [filterJenis, setFilterJenis] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [pagination, setPagination] = useState({ total: 0, active: 0, inactive: 0 });

  const isAdmin = user?.role === 'admin';

  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);

  const [formData, setFormData] = useState({
    username: '',
    nama_unit: '',
    jenis_akun: 'kanwil',
    status: 'aktif',
    notes: '',
  });
  const [formError, setFormError] = useState('');
  const [formSaving, setFormSaving] = useState(false);

  const [previewData, setPreviewData] = useState<{
    total_rows: number;
    valid_rows: number;
    duplicate_rows: number;
    invalid_rows: number;
    rows: PreviewRow[];
    can_proceed: boolean;
  } | null>(null);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<{
    success: boolean;
    imported: number;
    updated: number;
    skipped: number;
    failed: number;
  } | null>(null);
  const [skipDuplicates, setSkipDuplicates] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleHeaderToggle = () => {
    if (window.innerWidth < 1024) {
      toggleMobile();
    } else {
      togglePinned();
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, [search, filterJenis, filterStatus, isAdmin]);

  const fetchAccounts = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = isAdmin
        ? await instagramAccountsApi.list({
            search: search || undefined,
            jenis_akun: filterJenis || undefined,
            status: filterStatus || undefined,
          })
        : await instagramAccountsApi.listAll({
            search: search || undefined,
            jenis_akun: filterJenis || undefined,
            status: filterStatus || undefined,
          });
      setAccounts(data.accounts || []);
      setPagination({
        total: data.total || 0,
        active: data.active_count || 0,
        inactive: data.inactive_count || 0,
      });
    } catch (error: any) {
      console.error('Failed to fetch accounts:', error);
      setError(error.message || 'Gagal memuat data akun');
      setAccounts([]);
    } finally {
      setLoading(false);
    }
  };

  const handleAddAccount = async () => {
    setFormError('');
    if (!formData.username.trim() || !formData.nama_unit.trim()) {
      setFormError('Username dan Nama Unit harus diisi');
      return;
    }

    setFormSaving(true);
    try {
      await instagramAccountsApi.create(formData);
      setShowAddModal(false);
      resetForm();
      fetchAccounts();
    } catch (error: any) {
      setFormError(error.message || 'Gagal menambahkan akun');
    } finally {
      setFormSaving(false);
    }
  };

  const handleEditAccount = async () => {
    if (!editingAccount) return;
    setFormError('');

    if (!formData.username.trim() || !formData.nama_unit.trim()) {
      setFormError('Username dan Nama Unit harus diisi');
      return;
    }

    setFormSaving(true);
    try {
      await instagramAccountsApi.update(editingAccount.id, formData);
      setShowEditModal(false);
      setEditingAccount(null);
      resetForm();
      fetchAccounts();
    } catch (error: any) {
      setFormError(error.message || 'Gagal mengupdate akun');
    } finally {
      setFormSaving(false);
    }
  };

  const handleDeleteAccount = async (id: number) => {
    if (!confirm('Hapus akun ini? Data scraping yang sudah ada akan tetap disimpan.')) return;
    try {
      await instagramAccountsApi.delete(id);
      fetchAccounts();
    } catch (error) {
      console.error('Failed to delete:', error);
    }
  };

  const handleToggleStatus = async (id: number) => {
    try {
      await instagramAccountsApi.toggle(id);
      fetchAccounts();
    } catch (error) {
      console.error('Failed to toggle:', error);
    }
  };

  const openEditModal = (account: Account) => {
    setEditingAccount(account);
    setFormData({
      username: account.username,
      nama_unit: account.nama_unit,
      jenis_akun: account.jenis_akun,
      status: account.status,
      notes: account.notes || '',
    });
    setFormError('');
    setShowEditModal(true);
  };

  const resetForm = () => {
    setFormData({
      username: '',
      nama_unit: '',
      jenis_akun: 'kanwil',
      status: 'aktif',
      notes: '',
    });
    setFormError('');
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      alert('File harus format Excel (.xlsx atau .xls)');
      return;
    }

    setImportFile(file);
    setImportResult(null);

    try {
      const preview = await instagramAccountsApi.importPreview(file);
      setPreviewData(preview);
    } catch (error: any) {
      alert(error.message || 'Gagal preview file');
      setPreviewData(null);
    }
  };

  const handleImport = async () => {
    if (!importFile || !previewData?.can_proceed) return;

    setImporting(true);
    try {
      const result = await instagramAccountsApi.importConfirm(importFile, {
        skip_duplicates: skipDuplicates,
      });
      setImportResult(result);
      if (result.success) {
        setTimeout(() => {
          closeImportModal();
          fetchAccounts();
        }, 2000);
      }
    } catch (error: any) {
      alert(error.message || 'Gagal import');
    } finally {
      setImporting(false);
    }
  };

  const closeImportModal = () => {
    setShowImportModal(false);
    setImportFile(null);
    setPreviewData(null);
    setImportResult(null);
    setSkipDuplicates(true);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const getBadgeClass = (jenis: string) => {
    switch (jenis) {
      case 'kanwil': return 'badge-kanwil';
      case 'kppn': return 'badge-kppn';
      case 'pusat': return 'badge-pusat';
      case 'kanver_lainnya': return 'badge-other';
      default: return '';
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
              <h1 className="header-title">Akun Instagram</h1>
              <p className="header-subtitle">Manajemen Akun Monitoring</p>
            </div>
          </div>
          <div className="header-actions">
            <button className="btn btn-ghost" onClick={fetchAccounts} disabled={loading}>
              <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
            </button>
            {isAdmin && (
              <>
                <button className="btn btn-secondary" onClick={() => setShowImportModal(true)}>
                  <Upload size={18} />
                  Import Excel
                </button>
                <button className="btn btn-gold" onClick={() => { resetForm(); setShowAddModal(true); }}>
                  <Plus size={18} />
                  Tambah Akun
                </button>
              </>
            )}
            {!isAdmin && (
              <div className="readonly-notice">
                <Lock size={14} />
                <span>Mode Baca Saja</span>
              </div>
            )}
          </div>
        </header>

        <main className="dashboard-content">
          <div className="stats-row">
            <div className="stat-card">
              <span className="stat-value">{pagination.total}</span>
              <span className="stat-label">Total Akun</span>
            </div>
            <div className="stat-card active">
              <span className="stat-value">{pagination.active}</span>
              <span className="stat-label">Aktif</span>
            </div>
            <div className="stat-card inactive">
              <span className="stat-value">{pagination.inactive}</span>
              <span className="stat-label">Nonaktif</span>
            </div>
          </div>
          <div className="filters-bar">
            <div className="search-input">
              <Search size={18} />
              <input
                type="text"
                placeholder="Cari username atau nama unit..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="filter-group">
              <Filter size={18} />
              <select value={filterJenis} onChange={(e) => setFilterJenis(e.target.value)}>
                <option value="">Semua Jenis</option>
                <option value="kanwil">Kanwil</option>
                <option value="kppn">KPPN</option>
                <option value="pusat">Pusat</option>
                <option value="kanver_lainnya">Kanver Lainnya</option>
              </select>
            </div>
            <div className="filter-group">
              <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
                <option value="">Semua Status</option>
                <option value="aktif">Aktif</option>
                <option value="nonaktif">Nonaktif</option>
              </select>
            </div>
          </div>
          <div className="table-container">
            {loading ? (
              <div className="loading-state">
                <div className="loading-spinner" />
                <p>Memuat data akun...</p>
              </div>
            ) : error ? (
              <div className="error-state">
                <AlertCircle size={48} />
                <p>{error}</p>
                <button className="btn btn-secondary" onClick={fetchAccounts}>
                  <RefreshCw size={16} />
                  Coba Lagi
                </button>
              </div>
            ) : accounts.length === 0 ? (
              <div className="empty-state">
                <Users size={48} />
                <p>Belum ada akun Instagram.</p>
                {isAdmin && (
                  <button className="btn btn-gold" onClick={() => { resetForm(); setShowAddModal(true); }}>
                    <Plus size={18} />
                    Tambah Akun Pertama
                  </button>
                )}
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Nama Unit</th>
                    <th>Jenis</th>
                    <th>Status</th>
                    <th>Notes</th>
                    <th>Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  {accounts.map((account) => (
                    <tr key={account.id} className={!account.is_active ? 'inactive-row' : ''}>
                      <td>
                        <span className="username">@{account.username}</span>
                      </td>
                      <td>{account.nama_unit}</td>
                      <td>
                        <span className={`badge ${getBadgeClass(account.jenis_akun)}`}>
                          {account.jenis_akun.replace('_', ' ').toUpperCase()}
                        </span>
                      </td>
                      <td>
                        <span className={`status-badge ${account.is_active ? 'active' : 'inactive'}`}>
                          {(account.status || 'aktif').toUpperCase()}
                        </span>
                      </td>
                      <td className="notes-cell">{account.notes || '-'}</td>
                      <td>
                        {isAdmin ? (
                          <div className="action-buttons">
                            <button
                              className="btn-icon"
                              onClick={() => handleToggleStatus(account.id)}
                              title={account.is_active ? 'Nonaktifkan' : 'Aktifkan'}
                            >
                              {account.is_active ? (
                                <ToggleRight size={20} className="text-green-500" />
                              ) : (
                                <ToggleLeft size={20} className="text-gray-400" />
                              )}
                            </button>
                            <button
                              className="btn-icon"
                              onClick={() => openEditModal(account)}
                              title="Edit"
                            >
                              <Edit2 size={18} />
                            </button>
                            <button
                              className="btn-icon text-red-500"
                              onClick={() => handleDeleteAccount(account.id)}
                              title="Hapus"
                            >
                              <Trash2 size={18} />
                            </button>
                          </div>
                        ) : (
                          <span className="readonly-badge">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </main>
      </div>
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Tambah Akun</h3>
              <button className="btn btn-icon" onClick={() => setShowAddModal(false)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              {formError && (
                <div className="alert alert-error">
                  <AlertCircle size={18} />
                  {formError}
                </div>
              )}
              <div className="form-group">
                <label>Username Instagram</label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData(prev => ({ ...prev, username: e.target.value }))}
                  placeholder="@djpbkemenkeu"
                />
              </div>
              <div className="form-group">
                <label>Nama Unit</label>
                <input
                  type="text"
                  value={formData.nama_unit}
                  onChange={(e) => setFormData(prev => ({ ...prev, nama_unit: e.target.value }))}
                  placeholder="Kanwil DJPb Jakarta"
                />
              </div>
              <div className="form-group">
                <label>Jenis Akun</label>
                <select
                  value={formData.jenis_akun}
                  onChange={(e) => setFormData(prev => ({ ...prev, jenis_akun: e.target.value }))}
                >
                  <option value="kanwil">Kanwil</option>
                  <option value="kppn">KPPN</option>
                  <option value="pusat">Pusat</option>
                  <option value="kanver_lainnya">Kanver Lainnya</option>
                </select>
              </div>
              <div className="form-group">
                <label>Status</label>
                <select
                  value={formData.status}
                  onChange={(e) => setFormData(prev => ({ ...prev, status: e.target.value }))}
                >
                  <option value="aktif">Aktif</option>
                  <option value="nonaktif">Nonaktif</option>
                </select>
              </div>
              <div className="form-group">
                <label>Notes (opsional)</label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                  placeholder="Catatan tambahan..."
                  rows={2}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowAddModal(false)}>
                Batal
              </button>
              <button
                className="btn btn-primary"
                onClick={handleAddAccount}
                disabled={formSaving}
              >
                {formSaving ? 'Menyimpan...' : 'Tambah'}
              </button>
            </div>
          </div>
        </div>
      )}
      {showEditModal && editingAccount && (
        <div className="modal-overlay" onClick={() => setShowEditModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Edit Akun</h3>
              <button className="btn btn-icon" onClick={() => setShowEditModal(false)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              {formError && (
                <div className="alert alert-error">
                  <AlertCircle size={18} />
                  {formError}
                </div>
              )}
              <div className="form-group">
                <label>Username Instagram</label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData(prev => ({ ...prev, username: e.target.value }))}
                />
              </div>
              <div className="form-group">
                <label>Nama Unit</label>
                <input
                  type="text"
                  value={formData.nama_unit}
                  onChange={(e) => setFormData(prev => ({ ...prev, nama_unit: e.target.value }))}
                />
              </div>
              <div className="form-group">
                <label>Jenis Akun</label>
                <select
                  value={formData.jenis_akun}
                  onChange={(e) => setFormData(prev => ({ ...prev, jenis_akun: e.target.value }))}
                >
                  <option value="kanwil">Kanwil</option>
                  <option value="kppn">KPPN</option>
                  <option value="pusat">Pusat</option>
                  <option value="kanver_lainnya">Kanver Lainnya</option>
                </select>
              </div>
              <div className="form-group">
                <label>Status</label>
                <select
                  value={formData.status}
                  onChange={(e) => setFormData(prev => ({ ...prev, status: e.target.value }))}
                >
                  <option value="aktif">Aktif</option>
                  <option value="nonaktif">Nonaktif</option>
                </select>
              </div>
              <div className="form-group">
                <label>Notes (opsional)</label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                  rows={2}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowEditModal(false)}>
                Batal
              </button>
              <button
                className="btn btn-primary"
                onClick={handleEditAccount}
                disabled={formSaving}
              >
                {formSaving ? 'Menyimpan...' : 'Simpan'}
              </button>
            </div>
          </div>
        </div>
      )}
      {showImportModal && (
        <div className="modal-overlay" onClick={closeImportModal}>
          <div className="modal modal-lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Import Akun dari Excel</h3>
              <button className="btn btn-icon" onClick={closeImportModal}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <div className="file-upload-area">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleFileChange}
                  style={{ display: 'none' }}
                />
                <Upload size={32} className="text-gray-400" />
                <p>Klik untuk pilih file Excel</p>
                <button
                  className="btn btn-secondary"
                  onClick={() => fileInputRef.current?.click()}
                >
                  Pilih File
                </button>
                {importFile && (
                  <span className="file-name">
                    <CheckCircle size={16} className="text-green-500" />
                    {importFile.name}
                  </span>
                )}
              </div>
              {previewData && (
                <>
                  <div className="preview-stats">
                    <div className="preview-stat">
                      <span className="stat-value">{previewData.total_rows}</span>
                      <span className="stat-label">Total Rows</span>
                    </div>
                    <div className="preview-stat success">
                      <span className="stat-value">{previewData.valid_rows}</span>
                      <span className="stat-label">Valid</span>
                    </div>
                    <div className="preview-stat warning">
                      <span className="stat-value">{previewData.duplicate_rows}</span>
                      <span className="stat-label">Duplicate</span>
                    </div>
                    <div className="preview-stat error">
                      <span className="stat-value">{previewData.invalid_rows}</span>
                      <span className="stat-label">Invalid</span>
                    </div>
                  </div>
                  <div className="preview-table-container">
                    <table className="preview-table">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th>Username</th>
                          <th>Nama Unit</th>
                          <th>Jenis</th>
                          <th>Status</th>
                          <th>Info</th>
                        </tr>
                      </thead>
                      <tbody>
                        {previewData.rows.slice(0, 20).map((row) => (
                          <tr
                            key={row.row_number}
                            className={
                              !row.is_valid
                                ? 'invalid-row'
                                : row.is_duplicate
                                ? 'duplicate-row'
                                : ''
                            }
                          >
                            <td>{row.row_number}</td>
                            <td>@{row.username}</td>
                            <td>{row.nama_unit}</td>
                            <td>{row.jenis_akun}</td>
                            <td>{row.status}</td>
                            <td>
                              {row.is_duplicate ? (
                                <span className="badge badge-warning">Duplicate</span>
                              ) : !row.is_valid ? (
                                <span className="badge badge-error" title={row.error_message}>
                                  Invalid
                                </span>
                              ) : (
                                <CheckCircle size={16} className="text-green-500" />
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {previewData.rows.length > 20 && (
                      <p className="preview-note">
                        Menampilkan 20 dari {previewData.rows.length} rows
                      </p>
                    )}
                  </div>
                  {previewData.duplicate_rows > 0 && (
                    <div className="duplicate-options">
                      <label className="radio-label">
                        <input
                          type="radio"
                          checked={skipDuplicates}
                          onChange={() => setSkipDuplicates(true)}
                        />
                        <span>Skip duplicate (abaikan yang sudah ada)</span>
                      </label>
                      <label className="radio-label">
                        <input
                          type="radio"
                          checked={!skipDuplicates}
                          onChange={() => setSkipDuplicates(false)}
                        />
                        <span>Update existing (perbarui yang sudah ada)</span>
                      </label>
                    </div>
                  )}
                </>
              )}
              {importResult && (
                <div className={`import-result ${importResult.success ? 'success' : 'error'}`}>
                  {importResult.success ? (
                    <CheckCircle size={24} />
                  ) : (
                    <XCircle size={24} />
                  )}
                  <div>
                    <p className="result-title">
                      {importResult.success ? 'Import Berhasil!' : 'Import Gagal'}
                    </p>
                    <p className="result-stats">
                      {importResult.imported > 0 && `Diimport: ${importResult.imported}`}
                      {importResult.updated > 0 && `, Diupdate: ${importResult.updated}`}
                      {importResult.skipped > 0 && `, Dilewati: ${importResult.skipped}`}
                      {importResult.failed > 0 && `, Gagal: ${importResult.failed}`}
                    </p>
                  </div>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={closeImportModal}>
                {importResult?.success ? 'Tutup' : 'Batal'}
              </button>
              {previewData && !importResult && (
                <button
                  className="btn btn-primary"
                  onClick={handleImport}
                  disabled={importing || !previewData.can_proceed}
                >
                  {importing ? 'Mengimport...' : 'Import Sekarang'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
      <footer className="page-footer">
        <p className="footer-copyright">
          © {new Date().getFullYear()} DJPb Mayz Monitoring System. Hak cipta dilindungi.
        </p>
      </footer>
    </div>
  );
}
