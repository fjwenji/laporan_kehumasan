const API_BASE = '/api';

interface ApiOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
  headers?: Record<string, string>;
}

class ApiError extends Error {
  status: number;
  data?: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

function errorText(data: unknown, fallback = 'Request failed'): string {
  if (!data) return fallback;
  if (typeof data === 'string') return data;
  if (typeof data === 'object') {
    const record = data as Record<string, unknown>;
    const value = record.detail ?? record.message ?? record.error;
    if (typeof value === 'string') return value;
    if (Array.isArray(value)) {
      const result = value.map(item => errorText(item, '')).filter(Boolean).join(', ');
      return result || fallback;
    }
    if (value && typeof value === 'object') return JSON.stringify(value);
  }
  return fallback;
}

async function api<T>(endpoint: string, options: ApiOptions = {}): Promise<T> {
  const token = localStorage.getItem('token');

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: options.method || 'GET',
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    let errorDetail = 'Request failed';
    let errorData: unknown = null;
    try {
      errorData = await response.json();
      errorDetail = errorText(errorData, errorDetail);
    } catch {
      errorDetail = response.statusText || errorDetail;
    }
    throw new ApiError(errorDetail, response.status, errorData);
  }

  if (response.headers.get('content-type')?.includes('spreadsheet') || response.headers.get('content-type')?.includes('excel')) {
    return response.blob() as unknown as T;
  }

  return response.json();
}

export const authApi = {
  login: (username: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    return fetch('/api/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData.toString(),
    }).then(response => {
      if (!response.ok) {
        return response.json().then(err => Promise.reject(new Error(err.detail || 'Login failed')));
      }
      return response.json();
    }) as Promise<{ access_token: string; token_type: string }>;
  },

  getMe: () => api<{
    id: number;
    username: string;
    role: string;
    is_active: boolean;
    nama_lengkap?: string;
  }>('/auth/me'),

  changePassword: (oldPassword: string, newPassword: string) =>
    api<{ success: boolean; message: string }>('/auth/change-password', {
      method: 'POST',
      body: { old_password: oldPassword, new_password: newPassword },
    }),

  forgotPassword: (username: string) =>
    api<{ success: boolean; message: string }>('/auth/forgot-password', {
      method: 'POST',
      body: { username },
    }),

  getUsers: () => api<{ users: unknown[]; total: number }>('/auth/users'),

  register: (data: { username: string; password: string; role: string; nama_lengkap?: string }) =>
    api('/auth/register', {
      method: 'POST',
      body: data,
    }),

  updateUser: (userId: number, data: { nama_lengkap?: string; role?: string; is_active?: boolean; password?: string }) =>
    api(`/auth/users/${userId}`, {
      method: 'PUT',
      body: data,
    }),

  deleteUser: (userId: number) =>
    api(`/auth/users/${userId}`, { method: 'DELETE' }),

  resetPassword: (userId: number) =>
    api<{ success: boolean; new_password: string }>(`/auth/users/${userId}/reset-password`, {
      method: 'POST',
    }),
};

export const dashboardApi = {
  getSummary: (start: string, end: string, username?: string) => {
    let url = `/dashboard/summary?start=${start}&end=${end}`;
    if (username) url += `&username=${username}`;
    return api<{
      total_accounts: number;
      active_accounts: number;
      total_posts: number;
      new_posts: number;
      failed_posts: number;
      partial_posts: number;
      total_likes: number;
      total_comments: number;
      total_engagement: number;
      total_views: number;
      media_image: number;
      media_carousel: number;
      media_reels: number;
      media_video: number;
      media_unclassified: number;
    }>(url);
  },

  getPosts: (start: string, end: string, username?: string, limit = 100, offset = 0) => {
    let url = `/dashboard/posts?start=${start}&end=${end}&limit=${limit}&offset=${offset}`;
    if (username) url += `&username=${username}`;
    return api<{
      posts: unknown[];
      total: number;
      period_start: string;
      period_end: string;
    }>(url);
  },

  getCharts: (start: string, end: string) =>
    api<{
      engagement_by_account: unknown[];
      posts_by_account: unknown[];
      media_type_breakdown: unknown[];
      interaction_tiers: { high: number; medium: number; low: number };
    }>(`/dashboard/charts?start=${start}&end=${end}`),

  getAccounts: (kategori?: string) => {
    let url = '/dashboard/accounts';
    if (kategori) url += `?kategori=${kategori}`;
    return api<{
      accounts: unknown[];
      total: number;
    }>(url);
  },
};

export const jobsApi = {
  list: (limit = 20, status?: string) => {
    let url = `/jobs/?limit=${limit}`;
    if (status) url += `&status=${status}`;
    return api<{
      jobs: unknown[];
      total: number;
      running_count: number;
      queued_count: number;
    }>(url);
  },

  getCurrent: () =>
    api<{ running: boolean; job?: unknown }>('/jobs/current'),

  getNodeFlow: () =>
    api<{
      nodes: unknown[];
      current_job?: unknown;
      worker_status: string;
      worker_last_heartbeat?: string;
    }>('/jobs/node-flow'),

  getFailed: (jobId?: string, limit = 50) => {
    let url = `/jobs/failed?limit=${limit}`;
    if (jobId) url += `&job_id=${jobId}`;
    return api<{
      items: unknown[];
      total: number;
    }>(url);
  },

  getWorkerStatus: () =>
    api<{
      is_alive: boolean;
      last_heartbeat?: string;
      current_job_id?: string;
      current_job_status?: string;
      pid?: number;
    }>('/jobs/worker-status'),

  getAlerts: (limit = 20) =>
    api<{
      alerts: unknown[];
      total: number;
      unread_count: number;
    }>(`/jobs/alerts?limit=${limit}`),

  trigger: (jobType: string, periodStart?: string, periodEnd?: string) =>
    api<{ success: boolean; job_id?: string; message: string }>('/jobs/trigger', {
      method: 'POST',
      body: {
        job_type: jobType,
        period_start: periodStart,
        period_end: periodEnd,
      },
    }),
};

export const exportApi = {
  downloadExcel: async (start: string, end: string, username?: string) => {
    const token = localStorage.getItem('token');
    let url = `/export/excel?start=${start}&end=${end}`;
    if (username) url += `&username=${username}`;

    const response = await fetch(`${API_BASE}${url}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error('Export failed');
    }

    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = `mayz_export_${start}_${end}.xlsx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(downloadUrl);
  },
};

export const settingsApi = {
  getTelegramSettings: () =>
    api<{
      enabled: boolean;
      bot_token_masked: string;
      notify_new_post: boolean;
      recipient_count: number;
      recipients: Array<{
        id: number;
        name: string;
        chat_id: string;
        is_active: boolean;
        created_at?: string;
        updated_at?: string;
      }>;
    }>('/admin/settings/telegram'),

  updateTelegramSettings: (data: { enabled?: boolean; notify_new_post?: boolean }) =>
    api<{ success: boolean; message: string }>('/admin/settings/telegram', {
      method: 'PUT',
      body: data,
    }),

  updateTelegramToken: (token: string) =>
    api<{ success: boolean; message: string }>('/admin/settings/telegram/token', {
      method: 'POST',
      body: { bot_token: token },
    }),

  getTelegramRecipients: () =>
    api<{
      recipients: Array<{
        id: number;
        name: string;
        chat_id: string;
        is_active: boolean;
      }>;
      total: number;
    }>('/admin/settings/telegram/recipients'),

  createTelegramRecipient: (data: { name: string; chat_id: string }) =>
    api<{
      id: number;
      name: string;
      chat_id: string;
      is_active: boolean;
    }>('/admin/settings/telegram/recipients', {
      method: 'POST',
      body: data,
    }),

  updateTelegramRecipient: (id: number, data: { name?: string; chat_id?: string; is_active?: boolean }) =>
    api<{ id: number; name: string; chat_id: string; is_active: boolean }>(
      `/admin/settings/telegram/recipients/${id}`,
      { method: 'PUT', body: data }
    ),

  deleteTelegramRecipient: (id: number) =>
    api<{ success: boolean; message: string }>(`/admin/settings/telegram/recipients/${id}`, {
      method: 'DELETE',
    }),

  toggleTelegramRecipient: (id: number) =>
    api<{ id: number; name: string; chat_id: string; is_active: boolean }>(
      `/admin/settings/telegram/recipients/${id}/toggle`,
      { method: 'POST' }
    ),

  testTelegram: (message?: string) =>
    api<{ success: boolean; message: string; details?: string }>('/admin/settings/telegram/test', {
      method: 'POST',
      body: { message },
    }),

  getSchedulerSettings: () =>
    api<{
      is_enabled: boolean;
      schedule_mode: string;
      interval_minutes: number;
      daily_times: string[];
      account_scope: string;
      account_limit: number;
      cooldown_seconds: number;
      updated_at?: string;
    }>('/admin/settings/scheduler'),

  updateSchedulerSettings: (data: {
    is_enabled?: boolean;
    schedule_mode?: string;
    interval_minutes?: number;
    daily_times?: string;
    account_scope?: string;
    account_limit?: number;
    cooldown_seconds?: number;
  }) =>
    api<{ success: boolean; message: string }>('/admin/settings/scheduler', {
      method: 'PUT',
      body: data,
    }),

  getSchedulerStatus: () =>
    api<{
      status: string;
      message: string;
      is_enabled: boolean;
      is_synced: boolean;
      schedule_mode: string;
      interval_minutes: number;
      daily_times: string[];
      next_run?: string;
      last_run?: string;
      last_run_status?: string;
      worker_status: string;
      worker_last_heartbeat?: string;
      current_job_id?: string;
    }>('/admin/settings/scheduler/status'),

  syncScheduler: () =>
    api<{
      success: boolean;
      message: string;
      tasks_synced: number;
      errors: string[];
    }>('/admin/settings/scheduler/sync', { method: 'POST' }),
};

export const instagramAccountsApi = {
  listAll: (params?: {
    search?: string;
    jenis_akun?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.append('search', params.search);
    if (params?.jenis_akun) searchParams.append('jenis_akun', params.jenis_akun);
    if (params?.status) searchParams.append('status', params.status);
    if (params?.limit) searchParams.append('limit', String(params.limit));
    if (params?.offset) searchParams.append('offset', String(params.offset));

    const query = searchParams.toString();
    return api<{
      accounts: Array<{
        id: number;
        username: string;
        nama_unit: string;
        jenis_akun: string;
        status: string;
        notes?: string;
        is_active: boolean;
        created_at?: string;
        updated_at?: string;
      }>;
      total: number;
      active_count: number;
      inactive_count: number;
    }>(`/dashboard/instagram-accounts${query ? `?${query}` : ''}`);
  },

  list: (params?: {
    search?: string;
    jenis_akun?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.append('search', params.search);
    if (params?.jenis_akun) searchParams.append('jenis_akun', params.jenis_akun);
    if (params?.status) searchParams.append('status', params.status);
    if (params?.limit) searchParams.append('limit', String(params.limit));
    if (params?.offset) searchParams.append('offset', String(params.offset));

    const query = searchParams.toString();
    return api<{
      accounts: Array<{
        id: number;
        username: string;
        nama_unit: string;
        jenis_akun: string;
        status: string;
        notes?: string;
        is_active: boolean;
        created_at?: string;
        updated_at?: string;
      }>;
      total: number;
      active_count: number;
      inactive_count: number;
    }>(`/admin/instagram-accounts${query ? `?${query}` : ''}`);
  },

  get: (id: number) =>
    api<{
      id: number;
      username: string;
      nama_unit: string;
      jenis_akun: string;
      status: string;
      notes?: string;
      is_active: boolean;
    }>(`/admin/instagram-accounts/${id}`),

  create: (data: {
    username: string;
    nama_unit: string;
    jenis_akun: string;
    status: string;
    notes?: string;
  }) =>
    api<{
      id: number;
      username: string;
      nama_unit: string;
      jenis_akun: string;
      status: string;
      is_active: boolean;
    }>('/admin/instagram-accounts', {
      method: 'POST',
      body: data,
    }),

  update: (id: number, data: {
    username?: string;
    nama_unit?: string;
    jenis_akun?: string;
    status?: string;
    notes?: string;
  }) =>
    api<{
      id: number;
      username: string;
      nama_unit: string;
      jenis_akun: string;
      status: string;
      is_active: boolean;
    }>(`/admin/instagram-accounts/${id}`, {
      method: 'PUT',
      body: data,
    }),

  delete: (id: number) =>
    api<{ success: boolean; message: string }>(`/admin/instagram-accounts/${id}`, {
      method: 'DELETE',
    }),

  toggle: (id: number) =>
    api<{ success: boolean; message: string }>(`/admin/instagram-accounts/${id}/toggle`, {
      method: 'POST',
    }),

  validateUsername: (username: string) =>
    api<{
      valid: boolean;
      normalized_username: string;
      message: string;
      is_duplicate: boolean;
      existing_account?: {
        id: number;
        nama_unit: string;
        kategori_unit: string;
      };
    }>('/admin/instagram-accounts/validate-username', {
      method: 'POST',
      body: { username },
    }),

  importPreview: async (file: File) => {
    const token = localStorage.getItem('token');
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/admin/instagram-accounts/import-preview`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || 'Preview failed');
    }

    return response.json() as Promise<{
      total_rows: number;
      valid_rows: number;
      duplicate_rows: number;
      invalid_rows: number;
      rows: Array<{
        row_number: number;
        username: string;
        nama_unit: string;
        jenis_akun: string;
        status: string;
        notes?: string;
        is_valid: boolean;
        error_message?: string;
        is_duplicate: boolean;
        existing_id?: number;
      }>;
      can_proceed: boolean;
    }>;
  },

  importConfirm: async (file: File, options: { skip_duplicates: boolean }) => {
    const token = localStorage.getItem('token');
    const formData = new FormData();
    formData.append('file', file);
    formData.append('skip_duplicates', String(options.skip_duplicates));

    const response = await fetch(`${API_BASE}/admin/instagram-accounts/import-confirm`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || 'Import failed');
    }

    return response.json() as Promise<{
      success: boolean;
      imported: number;
      updated: number;
      skipped: number;
      failed: number;
      errors: string[];
    }>;
  },
};

export const stagingApi = {
  listJobs: () =>
    api<{
      jobs: Array<{
        job_id: string;
        mode: string;
        file_path: string;
        file_size_bytes: number;
        file_size_mb: number;
        row_count: number;
        created_at: string;
        modified_at: string;
      }>;
      total: number;
      staging_root: string;
    }>('/staging/jobs'),

  getJobRows: (
    jobId: string,
    mode: string,
    limit: number = 100,
    offset: number = 0,
    username?: string,
    status?: string,
    mediaType?: string
  ) => {
    const params = new URLSearchParams();
    params.append('limit', String(limit));
    params.append('offset', String(offset));
    if (mode && mode !== 'hot') params.append('mode', mode);
    if (username) params.append('username', username);
    if (status) params.append('status', status);
    if (mediaType) params.append('media_type', mediaType);

    return api<{
      job_id: string;
      mode: string;
      rows: Array<{
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
      }>;
      total: number;
      total_raw: number;
      limit: number;
      offset: number;
      filters: {
        username: string | null;
        status: string | null;
        media_type: string | null;
      };
    }>(`/staging/jobs/${jobId}?${params.toString()}`);
  },

  getJobSummary: (jobId: string, mode: string = 'hot') =>
    api<{
      job_id: string;
      mode: string;
      summary: {
        total_rows: number;
        valid_count: number;
        invalid_count: number;
        failed_count: number;
        by_username: Record<string, number>;
        by_media_type: Record<string, number>;
        by_status: Record<string, number>;
      };
    }>(`/staging/jobs/${jobId}/summary?mode=${mode}`),

  downloadJob: async (jobId: string, mode: string = 'hot') => {
    const token = localStorage.getItem('token');
    const response = await fetch(`${API_BASE}/staging/jobs/${jobId}/download?mode=${mode}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error('Download failed');
    }

    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = `staging_${mode}_${jobId}.jsonl`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(downloadUrl);
  },
};

export { ApiError };
