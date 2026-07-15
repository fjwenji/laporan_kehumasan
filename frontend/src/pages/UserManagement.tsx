import { useState, useEffect } from 'react';
import {
  UserPlus,
  Shield,
  Key,
  Trash2,
  Edit3,
  X,
  Search,
  AlertCircle,
  RefreshCw,
  ToggleLeft,
  ToggleRight,
  AlignLeft,
  Check,
} from 'lucide-react';
import { authApi } from '../services/api';
import { useAuth } from '../App';
import Sidebar from '../components/Sidebar';
import { useSidebar } from '../contexts/SidebarContext';
import type { User } from '../types';
import './UserManagement.css';

interface UserListItem extends User {
  created_at?: string;
}

export default function UserManagement() {
  const { user: currentUser } = useAuth();
  const { toggleMobile, togglePinned } = useSidebar();
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<UserListItem | null>(null);

  const [searchTerm, setSearchTerm] = useState('');
  const [notification, setNotification] = useState<{type: 'success' | 'error', message: string} | null>(null);

  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newNamaLengkap, setNewNamaLengkap] = useState('');
  const [newRole, setNewRole] = useState<'admin' | 'user'>('user');
  const [editNamaLengkap, setEditNamaLengkap] = useState('');
  const [editRole, setEditRole] = useState<'admin' | 'user'>('user');
  const [editPassword, setEditPassword] = useState('');

  const fetchUsers = async () => {
    setIsLoading(true);
    try {
      const response = await authApi.getUsers();
      setUsers((response as { users: UserListItem[] }).users || []);
    } catch (err: any) {
      console.error('Failed to fetch users:', err);
      showNotification('error', 'Gagal mengambil daftar user');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const showNotification = (type: 'success' | 'error', message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 4000);
  };

  const filteredUsers = users.filter(
    (user) =>
      user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (user.nama_lengkap && user.nama_lengkap.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await authApi.register({
        username: newUsername,
        password: newPassword,
        role: newRole,
        nama_lengkap: newNamaLengkap || undefined,
      });
      showNotification('success', 'User berhasil ditambahkan');
      setShowAddModal(false);
      resetForm();
      fetchUsers();
    } catch (err: any) {
      showNotification('error', err.message || 'Gagal menambahkan user');
    }
  };

  const handleToggleActive = async (user: UserListItem) => {
    try {
      await authApi.updateUser(user.id, { is_active: !user.is_active });
      showNotification('success', `User ${!user.is_active ? 'diaktifkan' : 'dinonaktifkan'}`);
      fetchUsers();
    } catch (err: any) {
      showNotification('error', err.message || 'Gagal mengubah status user');
    }
  };

  const handleEditUser = (user: UserListItem) => {
    setSelectedUser(user);
    setEditNamaLengkap(user.nama_lengkap || '');
    setEditRole(user.role as 'admin' | 'user');
    setEditPassword('');
    setShowEditModal(true);
  };

  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;
    try {
      await authApi.updateUser(selectedUser.id, {
        nama_lengkap: editNamaLengkap || undefined,
        role: editRole,
        password: editPassword || undefined,
      });
      showNotification('success', 'User berhasil diupdate');
      setShowEditModal(false);
      fetchUsers();
    } catch (err: any) {
      showNotification('error', err.message || 'Gagal mengupdate user');
    }
  };

  const handleResetPassword = async (userId: number) => {
    if (!confirm('Reset password user ini?')) return;
    try {
      const response = await authApi.resetPassword(userId) as { new_password: string };
      showNotification('success', `Password direset: ${response.new_password}`);
    } catch (err: any) {
      showNotification('error', err.message || 'Gagal reset password');
    }
  };

  const handleDeleteUser = async (user: UserListItem) => {
    if (!confirm(`Hapus user "${user.username}"?`)) return;
    try {
      await authApi.deleteUser(user.id);
      showNotification('success', 'User berhasil dihapus');
      fetchUsers();
    } catch (err: any) {
      showNotification('error', err.message || 'Gagal menghapus user');
    }
  };

  const resetForm = () => {
    setNewUsername('');
    setNewPassword('');
    setNewNamaLengkap('');
    setNewRole('user');
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
              <h1 className="header-title">Kelola User</h1>
              <p className="header-subtitle">Tambah, edit, dan kelola user sistem</p>
            </div>
          </div>
          <div className="header-actions">
            <button className="btn btn-ghost" onClick={fetchUsers} disabled={isLoading}>
              <RefreshCw size={18} className={isLoading ? 'animate-spin' : ''} />
              <span>Refresh</span>
            </button>
            <button className="btn btn-gold" onClick={() => setShowAddModal(true)}>
              <UserPlus size={18} />
              <span>Tambah User</span>
            </button>
          </div>
        </header>

        <main className="dashboard-content">
          {notification && (
            <div className={`notification notification-${notification.type}`}>
              {notification.type === 'success' ? <Check size={18} /> : <AlertCircle size={18} />}
              <span>{notification.message}</span>
              <button onClick={() => setNotification(null)}><X size={16} /></button>
            </div>
          )}
          <div className="search-bar">
            <Search size={18} />
            <input
              type="text"
              placeholder="Cari username atau nama..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input"
            />
          </div>
          <div className="users-table-container">
            <table className="users-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Aksi</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((user) => (
                  <tr key={user.id}>
                    <td>
                      <div className="user-cell">
                        <div className="user-avatar">{user.username.charAt(0).toUpperCase()}</div>
                        <div>
                          <div className="user-name">{user.nama_lengkap || user.username}</div>
                          <div className="user-username">@{user.username}</div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className={`role-badge ${user.role}`}>
                        {user.role === 'admin' && <Shield size={12} />}
                        {user.role}
                      </span>
                    </td>
                    <td>
                      <button
                        className={`toggle-btn ${user.is_active ? 'active' : 'inactive'}`}
                        onClick={() => handleToggleActive(user)}
                        disabled={user.id === currentUser?.id}
                      >
                        {user.is_active ? <ToggleRight size={20} /> : <ToggleLeft size={20} />}
                        <span>{user.is_active ? 'Aktif' : 'Nonaktif'}</span>
                      </button>
                    </td>
                    <td>
                      <div className="action-buttons">
                        <button className="action-btn edit" onClick={() => handleEditUser(user)} title="Edit">
                          <Edit3 size={16} />
                        </button>
                        <button className="action-btn reset" onClick={() => handleResetPassword(user.id)} title="Reset Password">
                          <Key size={16} />
                        </button>
                        <button
                          className="action-btn delete"
                          onClick={() => handleDeleteUser(user)}
                          disabled={user.id === currentUser?.id}
                          title={user.id === currentUser?.id ? 'Tidak dapat menghapus diri sendiri' : 'Hapus'}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </main>
      </div>
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Tambah User Baru</h3>
              <button className="close-btn" onClick={() => setShowAddModal(false)}><X size={20} /></button>
            </div>
            <form onSubmit={handleAddUser}>
              <div className="form-group">
                <label>Username</label>
                <input type="text" className="input" value={newUsername} onChange={(e) => setNewUsername(e.target.value)} placeholder="username" required minLength={3} maxLength={30} pattern="^[a-zA-Z0-9_]+$" />
              </div>
              <div className="form-group">
                <label>Password</label>
                <input type="password" className="input" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="Minimal 8 karakter" required minLength={8} />
              </div>
              <div className="form-group">
                <label>Nama Lengkap</label>
                <input type="text" className="input" value={newNamaLengkap} onChange={(e) => setNewNamaLengkap(e.target.value)} placeholder="Nama lengkap (opsional)" />
              </div>
              <div className="form-group">
                <label>Role</label>
                <select className="input" value={newRole} onChange={(e) => setNewRole(e.target.value as 'admin' | 'user')}>
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-ghost" onClick={() => setShowAddModal(false)}>Batal</button>
                <button type="submit" className="btn btn-gold"><UserPlus size={16} /> Tambah</button>
              </div>
            </form>
          </div>
        </div>
      )}
      {showEditModal && selectedUser && (
        <div className="modal-overlay" onClick={() => setShowEditModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Edit User: {selectedUser.username}</h3>
              <button className="close-btn" onClick={() => setShowEditModal(false)}><X size={20} /></button>
            </div>
            <form onSubmit={handleUpdateUser}>
              <div className="form-group">
                <label>Username</label>
                <input type="text" className="input" value={selectedUser.username} disabled />
              </div>
              <div className="form-group">
                <label>Nama Lengkap</label>
                <input type="text" className="input" value={editNamaLengkap} onChange={(e) => setEditNamaLengkap(e.target.value)} />
              </div>
              <div className="form-group">
                <label>Role</label>
                <select className="input" value={editRole} onChange={(e) => setEditRole(e.target.value as 'admin' | 'user')}>
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="form-group">
                <label>Password Baru</label>
                <input type="password" className="input" value={editPassword} onChange={(e) => setEditPassword(e.target.value)} placeholder="Kosongkan jika tidak diubah" minLength={8} />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-ghost" onClick={() => setShowEditModal(false)}>Batal</button>
                <button type="submit" className="btn btn-gold"><Check size={16} /> Simpan</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
