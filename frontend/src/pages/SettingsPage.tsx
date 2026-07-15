import { useState, useEffect } from 'react';
import {
  Send,
  Plus,
  Trash2,
  Edit2,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Play,
  Clock,
  Activity,
  X,
  Eye,
  EyeOff,
  Calendar,
  Check,
  Loader2,
  AlignLeft,
} from 'lucide-react';
import { settingsApi } from '../services/api';
import Sidebar from '../components/Sidebar';
import { useSidebar } from '../contexts/SidebarContext';
import './SettingsPage.css';
import './FooterCopyright.css';

type TabType = 'telegram' | 'scheduler';

interface Recipient {
  id: number;
  name: string;
  chat_id: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

interface TelegramSettings {
  enabled: boolean;
  bot_token_masked: string;
  notify_new_post: boolean;
  recipient_count: number;
  recipients: Recipient[];
}

interface ScheduleWindow {
  id: string;
  start_time: string;
  end_time: string;
}

interface SchedulerStatus {
  status: string;
  message: string;
  is_enabled: boolean;
  schedule_mode: string;
  interval_minutes: number;
  daily_times: string[];
  next_run?: string;
  last_run?: string;
  last_run_status?: string;
  worker_status: string;
  worker_last_heartbeat?: string;
  current_job_id?: string;
  is_synced?: boolean;
}

interface SchedulerSettings {
  is_enabled: boolean;
  schedule_mode: string;
  interval_minutes: number;
  daily_times: string[];
  schedule_windows: ScheduleWindow[];
  account_limit: number;
  cooldown_seconds: number;
}

export default function SettingsPage() {
  const { toggleMobile, togglePinned } = useSidebar();
  const [activeTab, setActiveTab] = useState<TabType>('telegram');

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const [telegramSettings, setTelegramSettings] = useState<TelegramSettings | null>(null);
  const [showTokenInput, setShowTokenInput] = useState(false);
  const [newToken, setNewToken] = useState('');
  const [showToken, setShowToken] = useState(false);
  const [showAddRecipient, setShowAddRecipient] = useState(false);
  const [editingRecipient, setEditingRecipient] = useState<Recipient | null>(null);
  const [newRecipient, setNewRecipient] = useState({ name: '', chat_id: '' });
  const [testMessage, setTestMessage] = useState('');
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [testing, setTesting] = useState(false);

  const [tokenMessage, setTokenMessage] = useState<{ success: boolean; text: string } | null>(null);
  const [recipientMessage, setRecipientMessage] = useState<{ success: boolean; text: string } | null>(null);
  const [schedulerMessage, setSchedulerMessage] = useState<{ success: boolean; text: string } | null>(null);

  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null);
  const [schedulerSettings, setSchedulerSettings] = useState<SchedulerSettings>({
    is_enabled: true,
    schedule_mode: 'daily',
    interval_minutes: 60,
    daily_times: ['22:00'],
    schedule_windows: [
      { id: '1', start_time: '08:00', end_time: '11:00' },
      { id: '2', start_time: '20:00', end_time: '23:59' },
    ],
    account_limit: 15,
    cooldown_seconds: 5,
  });
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<{ success: boolean; message: string } | null>(null);

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'telegram') {
        const data = await settingsApi.getTelegramSettings();
        setTelegramSettings(data);
      } else {
        const [status, settings] = await Promise.all([
          settingsApi.getSchedulerStatus(),
          settingsApi.getSchedulerSettings(),
        ]);
        setSchedulerStatus(status);

        let windows: ScheduleWindow[] = [];
        if (settings.daily_times && settings.daily_times.length > 0) {
          // Parse format "HH:mm-HH:mm" pairs (e.g., "11:00-12:00, 20:00-23:00")
          windows = settings.daily_times.map((timePair, index) => {
            const parts = timePair.split('-');
            const start_time = parts[0] || '';
            const end_time = parts[1] || '';
            return {
              id: String(index + 1),
              start_time,
              end_time,
            };
          });
        }

        if (windows.length === 0) {
          windows = [
            { id: '1', start_time: '08:00', end_time: '11:00' },
            { id: '2', start_time: '20:00', end_time: '23:59' },
          ];
        }

        setSchedulerSettings({
          is_enabled: settings.is_enabled,
          schedule_mode: settings.schedule_mode,
          interval_minutes: settings.interval_minutes,
          daily_times: settings.daily_times,
          schedule_windows: windows,
          account_limit: settings.account_limit,
          cooldown_seconds: settings.cooldown_seconds,
        });
      }
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleHeaderToggle = () => {
    if (window.innerWidth < 1024) {
      toggleMobile();
    } else {
      togglePinned();
    }
  };

  const handleUpdateTelegramEnabled = async (enabled: boolean) => {
    // Guard: pastikan state ada
    if (!telegramSettings) {
      return;
    }

    // Validasi sebelum mengaktifkan
    if (enabled) {
      if (!telegramSettings.bot_token_masked || telegramSettings.bot_token_masked === 'Belum diset') {
        setTokenMessage({ success: false, text: 'Bot token belum dikonfigurasi.' });
        return;
      }
      const activeRecipients = telegramSettings.recipients?.filter((r: Recipient) => r.is_active) || [];
      if (activeRecipients.length === 0) {
        setTokenMessage({ success: false, text: 'Tambahkan minimal satu Chat ID aktif terlebih dahulu.' });
        return;
      }
    }

    setSaving(true);
    setTokenMessage(null);

    try {
      await settingsApi.updateTelegramSettings({ enabled });
      // Ambil ulang data dari server
      await fetchData();
      setTokenMessage({ success: true, text: enabled ? 'Notifikasi Telegram diaktifkan.' : 'Notifikasi Telegram dinonaktifkan.' });
    } catch (error: any) {
      const errorMessage = error?.message || error?.detail || 'Gagal menyimpan pengaturan Telegram.';
      setTokenMessage({ success: false, text: String(errorMessage) });
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateNotifyNewPost = async (notify: boolean) => {
    // Guard: pastikan state ada
    if (!telegramSettings) {
      return;
    }

    // Validasi: harus aktifkan Notifikasi Telegram dulu
    if (notify && !telegramSettings.enabled) {
      setTokenMessage({ success: false, text: 'Aktifkan "Notifikasi Telegram" terlebih dahulu.' });
      return;
    }

    setSaving(true);
    setTokenMessage(null);

    try {
      await settingsApi.updateTelegramSettings({ notify_new_post: notify });
      // Ambil ulang data dari server
      await fetchData();
      setTokenMessage({ success: true, text: notify ? 'Notifikasi postingan baru diaktifkan.' : 'Notifikasi postingan baru dinonaktifkan.' });
    } catch (error: any) {
      const errorMessage = error?.message || error?.detail || 'Gagal menyimpan pengaturan.';
      setTokenMessage({ success: false, text: String(errorMessage) });
    } finally {
      setSaving(false);
    }
  };

  const handleSaveToken = async () => {
    if (!newToken.trim()) return;
    setSaving(true);
    setTokenMessage(null);
    try {
      await settingsApi.updateTelegramToken(newToken);
      setNewToken('');
      setShowTokenInput(false);
      setTokenMessage({ success: true, text: 'Bot token berhasil disimpan!' });
      await fetchData();
    } catch (error: any) {
      const errorMessage = error?.message || error?.detail || 'Gagal menyimpan bot token. Periksa format token atau koneksi backend.';
      setTokenMessage({ success: false, text: String(errorMessage) });
    } finally {
      setSaving(false);
    }
  };

  const handleAddRecipient = async () => {
    if (!newRecipient.name.trim() || !newRecipient.chat_id.trim()) return;
    setSaving(true);
    setRecipientMessage(null);
    try {
      await settingsApi.createTelegramRecipient(newRecipient);
      setNewRecipient({ name: '', chat_id: '' });
      setShowAddRecipient(false);
      setRecipientMessage({ success: true, text: 'Chat ID berhasil ditambahkan.' });
      await fetchData();
    } catch (error: any) {
      setRecipientMessage({ success: false, text: error.message || 'Gagal menambahkan Chat ID' });
    } finally {
      setSaving(false);
    }
  };

  const handleEditRecipient = async () => {
    if (!editingRecipient || !newRecipient.name.trim() || !newRecipient.chat_id.trim()) return;
    setSaving(true);
    setRecipientMessage(null);
    try {
      await settingsApi.updateTelegramRecipient(editingRecipient.id, {
        name: newRecipient.name,
        chat_id: newRecipient.chat_id,
      });
      setNewRecipient({ name: '', chat_id: '' });
      setEditingRecipient(null);
      setRecipientMessage({ success: true, text: 'Chat ID berhasil diperbarui.' });
      await fetchData();
    } catch (error: any) {
      setRecipientMessage({ success: false, text: error.message || 'Gagal memperbarui Chat ID' });
    } finally {
      setSaving(false);
    }
  };

  const openEditRecipient = (recipient: Recipient) => {
    setEditingRecipient(recipient);
    setNewRecipient({ name: recipient.name, chat_id: recipient.chat_id });
    setShowAddRecipient(true);
  };

  const closeRecipientModal = () => {
    setShowAddRecipient(false);
    setEditingRecipient(null);
    setNewRecipient({ name: '', chat_id: '' });
  };

  const handleToggleRecipient = async (id: number) => {
    setSaving(true);
    try {
      await settingsApi.toggleTelegramRecipient(id);
      await fetchData();
    } catch (error) {
      console.error('Failed to toggle:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteRecipient = async (id: number) => {
    if (!confirm('Hapus penerima notifikasi ini?')) return;
    setSaving(true);
    setRecipientMessage(null);
    try {
      await settingsApi.deleteTelegramRecipient(id);
      setRecipientMessage({ success: true, text: 'Penerima notifikasi berhasil dihapus.' });
      await fetchData();
    } catch (error: any) {
      setRecipientMessage({ success: false, text: error.message || 'Gagal menghapus penerima notifikasi' });
    } finally {
      setSaving(false);
    }
  };

  const handleTestTelegram = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await settingsApi.testTelegram(testMessage || undefined);
      setTestResult({ success: result.success, message: result.message });
    } catch (error: any) {
      const errorMessage = error?.message || error?.detail || 'Gagal mengirim pesan test.';
      setTestResult({ success: false, message: String(errorMessage) });
    } finally {
      setTesting(false);
    }
  };

  const handleToggleSchedulerEnabled = async (enabled: boolean) => {
    setSaving(true);
    setSchedulerMessage(null);
    try {
      // Format: "HH:mm-HH:mm" pairs (e.g., "11:00-12:00, 20:00-23:00")
      // Normalize any dots to colons before saving
      const normalizeTime = (t: string) => t.replace(/\./g, ':');

      const dailyTimesStr = schedulerSettings.schedule_windows
        .filter(w => w.start_time && w.end_time)
        .map(w => `${normalizeTime(w.start_time)}-${normalizeTime(w.end_time)}`)
        .join(', ');

      await settingsApi.updateSchedulerSettings({
        is_enabled: enabled,
        schedule_mode: schedulerSettings.schedule_mode,
        interval_minutes: schedulerSettings.interval_minutes,
        daily_times: dailyTimesStr,
        account_limit: schedulerSettings.account_limit,
        cooldown_seconds: schedulerSettings.cooldown_seconds,
      });
      setSchedulerSettings(prev => ({ ...prev, is_enabled: enabled }));
    } catch (error: any) {
      setSchedulerMessage({ success: false, text: error.message || 'Gagal update scheduler' });
    } finally {
      setSaving(false);
    }
  };

  const addScheduleWindow = () => {
    const newId = String(Date.now());
    setSchedulerSettings(prev => ({
      ...prev,
      schedule_windows: [
        ...prev.schedule_windows,
        { id: newId, start_time: '', end_time: '' },
      ],
    }));
  };

  const removeScheduleWindow = (id: string) => {
    setSchedulerSettings(prev => ({
      ...prev,
      schedule_windows: prev.schedule_windows.filter(w => w.id !== id),
    }));
  };

  const updateScheduleWindow = (id: string, field: 'start_time' | 'end_time', value: string) => {
    setSchedulerSettings(prev => ({
      ...prev,
      schedule_windows: prev.schedule_windows.map(w =>
        w.id === id ? { ...w, [field]: value } : w
      ),
    }));
  };

  const validateScheduleWindows = (): { valid: boolean; message: string } => {
    const windows = schedulerSettings.schedule_windows;

    for (const window of windows) {
      if (!window.start_time || !window.end_time) {
        return { valid: false, message: 'Jam mulai dan jam selesai wajib diisi' };
      }
      if (window.start_time >= window.end_time) {
        return { valid: false, message: 'Jam mulai harus lebih kecil dari jam selesai' };
      }
    }

    for (let i = 0; i < windows.length; i++) {
      for (let j = i + 1; j < windows.length; j++) {
        const a = windows[i];
        const b = windows[j];
        if (
          (a.start_time < b.end_time && a.end_time > b.start_time)
        ) {
          return { valid: false, message: 'Jadwal tidak boleh overlap' };
        }
      }
    }

    return { valid: true, message: '' };
  };

  const handleSaveSchedulerSettings = async () => {
    setSchedulerMessage(null);

    const validation = validateScheduleWindows();
    if (!validation.valid) {
      setSchedulerMessage({ success: false, text: validation.message });
      return;
    }

    setSaving(true);
    try {
      // Format: "HH:mm-HH:mm" pairs (e.g., "11:00-12:00, 20:00-23:00")
      // Normalize any dots to colons before saving
      const normalizeTime = (t: string) => t.replace(/\./g, ':');

      const dailyTimesStr = schedulerSettings.schedule_windows
        .filter(w => w.start_time && w.end_time)
        .map(w => `${normalizeTime(w.start_time)}-${normalizeTime(w.end_time)}`)
        .join(', ');

      await settingsApi.updateSchedulerSettings({
        is_enabled: schedulerSettings.is_enabled,
        schedule_mode: schedulerSettings.schedule_mode,
        interval_minutes: schedulerSettings.interval_minutes,
        daily_times: dailyTimesStr,
        account_limit: schedulerSettings.account_limit,
        cooldown_seconds: schedulerSettings.cooldown_seconds,
      });

      setSchedulerMessage({ success: true, text: 'Pengaturan scheduler berhasil disimpan.' });
      await fetchData();
    } catch (error: any) {
      setSchedulerMessage({ success: false, text: error.message || 'Gagal menyimpan pengaturan scheduler.' });
    } finally {
      setSaving(false);
    }
  };

  const handleSyncScheduler = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const result = await settingsApi.syncScheduler();
      setSyncResult({ success: result.success, message: result.message });
      await fetchData();
    } catch (error: any) {
      setSyncResult({ success: false, message: error.message || 'Sync gagal' });
    } finally {
      setSyncing(false);
    }
  };

  const formatDateTime = (dateStr?: string) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('id-ID', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const isWorkerOnline = (status?: string) => {
    if (!status) return false;
    return ['alive', 'running', 'idle'].includes(status.toLowerCase());
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
              <h1 className="header-title">Pengaturan</h1>
              <p className="header-subtitle">Kelola konfigurasi sistem dan preferensi aplikasi.</p>
            </div>
          </div>
          <div className="header-actions">
            <button className="btn btn-ghost" onClick={fetchData} disabled={loading}>
              <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>
        </header>

        <main className="dashboard-content">
          <div className="settings-tabs">
            <button
              className={`tab-btn ${activeTab === 'telegram' ? 'active' : ''}`}
              onClick={() => setActiveTab('telegram')}
            >
              Telegram
            </button>
            <button
              className={`tab-btn ${activeTab === 'scheduler' ? 'active' : ''}`}
              onClick={() => setActiveTab('scheduler')}
            >
              Scheduler / Cron
            </button>
          </div>

          {loading ? (
            <div className="loading-state">
              <div className="loading-spinner" />
              <p>Memuat...</p>
            </div>
          ) : (
            <>
              {activeTab === 'telegram' && telegramSettings && (
                <div className="settings-section">
                  <div className="settings-card">
                    <h3 className="card-title">Pengaturan Telegram</h3>

                    {/* Toggle: Notifikasi Telegram */}
                    <div className="setting-row">
                      <div className="setting-info">
                        <span className="setting-label">Notifikasi Telegram</span>
                        <span className={`setting-status ${telegramSettings.enabled ? 'status-on' : 'status-off'}`}>
                          {telegramSettings.enabled ? '● Aktif' : '○ Nonaktif'}
                        </span>
                        <p className="setting-desc">Kirim notifikasi ke Telegram saat ada postingan baru</p>
                      </div>
                      <div className="setting-actions">
                        <button
                          type="button"
                          className={`btn-toggle ${telegramSettings.enabled ? 'btn-toggle-on' : ''}`}
                          onClick={() => handleUpdateTelegramEnabled(!telegramSettings.enabled)}
                          disabled={saving}
                        >
                          {saving ? '...' : telegramSettings.enabled ? 'MATIKAN' : 'AKTIFKAN'}
                        </button>
                      </div>
                    </div>

                    {/* Toggle: Notifikasi Postingan Baru */}
                    <div className="setting-row">
                      <div className="setting-info">
                        <span className="setting-label">Notifikasi Postingan Baru</span>
                        <span className={`setting-status ${telegramSettings.notify_new_post ? 'status-on' : 'status-off'}`}>
                          {telegramSettings.notify_new_post ? '● Aktif' : '○ Nonaktif'}
                        </span>
                        <p className="setting-desc">Kirim notifikasi saat menemukan postingan baru</p>
                      </div>
                      <div className="setting-actions">
                        <button
                          type="button"
                          className={`btn-toggle ${telegramSettings.notify_new_post ? 'btn-toggle-on' : ''}`}
                          onClick={() => handleUpdateNotifyNewPost(!telegramSettings.notify_new_post)}
                          disabled={saving}
                        >
                          {saving ? '...' : telegramSettings.notify_new_post ? 'MATIKAN' : 'AKTIFKAN'}
                        </button>
                      </div>
                    </div>

                    {/* Error/Success Messages */}
                    {tokenMessage && (
                      <div className={`message-box ${tokenMessage.success ? 'message-success' : 'message-error'}`}>
                        {tokenMessage.success ? '✓ ' : '✗ '}{tokenMessage.text}
                      </div>
                    )}
                  </div>

                  <div className="settings-card">
                    <h3 className="card-title">Bot Token</h3>
                    <div className="token-display">
                      <span className="token-label">Token:</span>
                      <code className="token-value">
                        {telegramSettings.bot_token_masked || 'Belum diset'}
                      </code>
                      <button
                        className="btn btn-sm btn-secondary"
                        onClick={() => setShowTokenInput(!showTokenInput)}
                      >
                        <Edit2 size={14} />
                        {showTokenInput ? 'Batal' : 'Update'}
                      </button>
                    </div>
                    {showTokenInput && (
                      <div className="token-input-section">
                        <div className="token-input-row">
                          <div className="input-group">
                            <input
                              type={showToken ? 'text' : 'password'}
                              value={newToken}
                              onChange={(e) => setNewToken(e.target.value)}
                              placeholder="123456:ABCDEFxxxxx"
                              className="input"
                            />
                            <button
                              className="btn btn-icon"
                              onClick={() => setShowToken(!showToken)}
                              type="button"
                            >
                              {showToken ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                          </div>
                          <button
                            className="btn btn-primary"
                            onClick={handleSaveToken}
                            disabled={saving || !newToken.trim()}
                          >
                            {saving ? 'Menyimpan...' : 'Simpan'}
                          </button>
                        </div>
                        {tokenMessage && (
                          <div className={`inline-message ${tokenMessage.success ? 'success' : 'error'}`}>
                            {tokenMessage.success ? <CheckCircle size={16} /> : <XCircle size={16} />}
                            <span>{tokenMessage.text}</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="settings-card">
                    <div className="card-header-row">
                      <div>
                        <h3 className="card-title">Penerima Notifikasi</h3>
                        <p className="card-help">Chat ID adalah ID akun atau grup Telegram yang akan menerima notifikasi dari bot.</p>
                      </div>
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={() => setShowAddRecipient(true)}
                      >
                        <Plus size={16} />
                        Tambah Chat ID
                      </button>
                    </div>

                    {recipientMessage && (
                      <div className={`inline-message ${recipientMessage.success ? 'success' : 'error'}`}>
                        {recipientMessage.success ? <CheckCircle size={16} /> : <XCircle size={16} />}
                        <span>{recipientMessage.text}</span>
                      </div>
                    )}

                    {telegramSettings.recipients.length === 0 ? (
                      <div className="empty-state">
                        <p className="empty-text">
                          Belum ada Chat ID. Tambahkan Chat ID agar bot tahu tujuan pengiriman notifikasi.
                        </p>
                      </div>
                    ) : (
                      <div className="recipient-list">
                        {telegramSettings.recipients.map((recipient) => (
                          <div key={recipient.id} className="recipient-item">
                            <div className="recipient-info">
                              <span className="recipient-name">{recipient.name}</span>
                              <code className="recipient-chat">{recipient.chat_id}</code>
                              <span className={`recipient-status ${recipient.is_active ? 'active' : 'inactive'}`}>
                                {recipient.is_active ? 'Aktif' : 'Nonaktif'}
                              </span>
                            </div>
                            <div className="recipient-actions">
                              <button
                                className={`btn btn-icon ${recipient.is_active ? 'text-green-500' : 'text-gray-400'}`}
                                onClick={() => handleToggleRecipient(recipient.id)}
                                title={recipient.is_active ? 'Nonaktifkan' : 'Aktifkan'}
                              >
                                {recipient.is_active ? <CheckCircle size={18} /> : <XCircle size={18} />}
                              </button>
                              <button
                                className="btn btn-icon text-blue-500"
                                onClick={() => openEditRecipient(recipient)}
                                title="Edit"
                              >
                                <Edit2 size={18} />
                              </button>
                              <button
                                className="btn btn-icon text-red-500"
                                onClick={() => handleDeleteRecipient(recipient.id)}
                                title="Hapus"
                              >
                                <Trash2 size={18} />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="settings-card">
                    <h3 className="card-title">Test Kirim Pesan</h3>
                    <div className="test-row">
                      <input
                        type="text"
                        value={testMessage}
                        onChange={(e) => setTestMessage(e.target.value)}
                        placeholder="Pesan test (opsional)"
                        className="input"
                      />
                      <button
                        className="btn btn-primary"
                        onClick={handleTestTelegram}
                        disabled={testing}
                      >
                        <Send size={16} />
                        {testing ? 'Mengirim...' : 'Test Kirim Pesan'}
                      </button>
                    </div>
                    {testResult && (
                      <div className={`test-result ${testResult.success ? 'success' : 'error'}`}>
                        {testResult.success ? <CheckCircle size={18} /> : <XCircle size={18} />}
                        <span>{testResult.message}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {activeTab === 'scheduler' && (
                <div className="settings-section">
                  <div className="settings-card scheduler-status-card">
                    <h3 className="card-title">
                      <Activity size={18} />
                      Status Scheduler
                    </h3>

                    <div className="scheduler-status-grid">
                      <div className="status-badge-container">
                        <div className={`status-badge ${schedulerSettings.is_enabled ? 'active' : 'inactive'}`}>
                          {schedulerSettings.is_enabled ? (
                            <>
                              <CheckCircle size={16} />
                              <span>Scheduler Aktif</span>
                            </>
                          ) : (
                            <>
                              <XCircle size={16} />
                              <span>Scheduler Nonaktif</span>
                            </>
                          )}
                        </div>
                      </div>
                      <div className="status-row">
                        <div className="status-indicator">
                          <span className={`indicator-dot ${isWorkerOnline(schedulerStatus?.worker_status) ? 'online' : 'offline'}`} />
                          <span className="indicator-label">
                            {isWorkerOnline(schedulerStatus?.worker_status) ? 'Worker Online' : 'Worker Offline'}
                          </span>
                        </div>
                      </div>
                      <div className="status-row">
                        <div className="status-info">
                          <Clock size={16} className="status-icon" />
                          <div className="status-details">
                            <span className="status-label">Terakhir Berjalan</span>
                            <span className="status-value">
                              {schedulerStatus?.last_run
                                ? formatDateTime(schedulerStatus.last_run)
                                : 'Belum pernah berjalan'}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="status-row">
                        <div className="status-info">
                          <Calendar size={16} className="status-icon" />
                          <div className="status-details">
                            <span className="status-label">Jadwal Berikutnya</span>
                            <span className="status-value">
                              {schedulerStatus?.next_run
                                ? formatDateTime(schedulerStatus.next_run)
                                : 'Belum tersedia'}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="status-row">
                        <div className="status-info">
                          <RefreshCw size={16} className="status-icon" />
                          <div className="status-details">
                            <span className="status-label">Status Sinkronisasi</span>
                            <span className="status-value sync-status">
                              {schedulerStatus?.is_synced ? (
                                <span className="sync-badge synced">
                                  <CheckCircle size={14} />
                                  Tersinkronisasi
                                </span>
                              ) : (
                                <span className="sync-badge not-synced">
                                  <AlertTriangle size={14} />
                                  Belum tersinkronisasi
                                </span>
                              )}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="settings-card">
                    <h3 className="card-title">
                      <Play size={18} />
                      Aktifkan Scheduler
                    </h3>

                    <div className="scheduler-toggle-container">
                      <label className="scheduler-toggle">
                        <input
                          type="checkbox"
                          checked={schedulerSettings.is_enabled}
                          onChange={(e) => handleToggleSchedulerEnabled(e.target.checked)}
                          disabled={saving}
                        />
                        <span className="scheduler-toggle-slider" />
                      </label>
                      <div className="scheduler-toggle-info">
                        <span className={`scheduler-toggle-label ${schedulerSettings.is_enabled ? 'enabled' : 'disabled'}`}>
                          {schedulerSettings.is_enabled ? 'Scheduler Aktif' : 'Scheduler Nonaktif'}
                        </span>
                        <p className="scheduler-toggle-helper">
                          {schedulerSettings.is_enabled
                            ? 'Scraping otomatis akan berjalan sesuai jadwal yang ditentukan.'
                            : 'Scraping otomatis sedang dimatikan.'}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="settings-card">
                    <div className="card-header-row">
                      <h3 className="card-title">
                        <Calendar size={18} />
                        Jadwal Aktif Scraping
                      </h3>
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={addScheduleWindow}
                      >
                        <Plus size={16} />
                        Tambah Jadwal
                      </button>
                    </div>

                    {schedulerSettings.schedule_windows.length === 0 ? (
                      <div className="empty-state">
                        <p className="empty-text">
                          Belum ada jadwal aktif. Tambahkan jadwal agar scheduler dapat berjalan otomatis.
                        </p>
                      </div>
                    ) : (
                      <div className="schedule-windows-list">
                        {schedulerSettings.schedule_windows.map((window, index) => (
                          <div key={window.id} className="schedule-window-row">
                            <span className="schedule-window-number">{index + 1}</span>
                            <div className="schedule-window-inputs">
                              <div className="schedule-time-group">
                                <label>Jam Mulai</label>
                                <input
                                  type="time"
                                  value={window.start_time}
                                  onChange={(e) => updateScheduleWindow(window.id, 'start_time', e.target.value)}
                                  className="input schedule-input"
                                />
                              </div>
                              <span className="schedule-time-separator">-</span>
                              <div className="schedule-time-group">
                                <label>Jam Selesai</label>
                                <input
                                  type="time"
                                  value={window.end_time}
                                  onChange={(e) => updateScheduleWindow(window.id, 'end_time', e.target.value)}
                                  className="input schedule-input"
                                />
                              </div>
                            </div>
                            <button
                              className="btn btn-icon text-red-500"
                              onClick={() => removeScheduleWindow(window.id)}
                              title="Hapus jadwal"
                              disabled={schedulerSettings.schedule_windows.length <= 1}
                            >
                              <Trash2 size={18} />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="schedule-note">
                      <AlertTriangle size={14} />
                      <span>
                        Scheduler akan berjalan dalam rentang waktu yang ditentukan.
                        Worker perlu mendukung pembacaan jadwal ini agar benar-benar membatasi jam scraping.
                      </span>
                    </div>
                  </div>

                  <div className="settings-card">
                    <h3 className="card-title">Pengaturan Tambahan</h3>

                    <div className="form-grid">
                      <div className="form-group">
                        <label className="form-label">Limit Akun per Job</label>
                        <input
                          type="number"
                          value={schedulerSettings.account_limit}
                          onChange={(e) => setSchedulerSettings(prev => ({
                            ...prev,
                            account_limit: parseInt(e.target.value) || 15
                          }))}
                          min="1"
                          max="100"
                          className="input"
                        />
                      </div>

                      <div className="form-group">
                        <label className="form-label">Cooldown (detik)</label>
                        <input
                          type="number"
                          value={schedulerSettings.cooldown_seconds}
                          onChange={(e) => setSchedulerSettings(prev => ({
                            ...prev,
                            cooldown_seconds: parseInt(e.target.value) || 5
                          }))}
                          min="0"
                          max="60"
                          className="input"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="settings-card">
                    <div className="scheduler-actions">
                      <button
                        className="btn btn-primary btn-save"
                        onClick={handleSaveSchedulerSettings}
                        disabled={saving}
                      >
                        {saving ? (
                          <>
                            <Loader2 size={18} className="animate-spin" />
                            Menyimpan...
                          </>
                        ) : (
                          <>
                            <Check size={18} />
                            Simpan Pengaturan Scheduler
                          </>
                        )}
                      </button>

                      <button
                        className="btn btn-secondary"
                        onClick={handleSyncScheduler}
                        disabled={syncing}
                      >
                        <RefreshCw size={16} className={syncing ? 'animate-spin' : ''} />
                        {syncing ? 'Syncing...' : 'Sync ke Windows Task Scheduler'}
                      </button>
                    </div>

                    {schedulerMessage && (
                      <div className={`inline-message ${schedulerMessage.success ? 'success' : 'error'}`}>
                        {schedulerMessage.success ? <CheckCircle size={16} /> : <XCircle size={16} />}
                        <span>{schedulerMessage.text}</span>
                      </div>
                    )}

                    {syncResult && (
                      <div className={`sync-result ${syncResult.success ? 'success' : 'error'}`}>
                        {syncResult.success ? <CheckCircle size={18} /> : <XCircle size={18} />}
                        <span>{syncResult.message}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>

      {showAddRecipient && (
        <div className="modal-overlay" onClick={closeRecipientModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingRecipient ? 'Edit Penerima Notifikasi' : 'Tambah Chat ID'}</h3>
              <button className="btn btn-icon" onClick={closeRecipientModal}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label className="form-label">Nama Penerima</label>
                <input
                  type="text"
                  value={newRecipient.name}
                  onChange={(e) => setNewRecipient(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="Contoh: Admin DJPb"
                  className="input"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Chat ID Telegram</label>
                <input
                  type="text"
                  value={newRecipient.chat_id}
                  onChange={(e) => setNewRecipient(prev => ({ ...prev, chat_id: e.target.value }))}
                  placeholder="123456789 atau -100123456789"
                  className="input"
                />
                <p className="form-help">Contoh personal: 123456789. Contoh grup: -100123456789.</p>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={closeRecipientModal}>
                Batal
              </button>
              <button
                className="btn btn-primary"
                onClick={editingRecipient ? handleEditRecipient : handleAddRecipient}
                disabled={saving || !newRecipient.name.trim() || !newRecipient.chat_id.trim()}
              >
                {saving ? 'Menyimpan...' : 'Simpan Chat ID'}
              </button>
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
