import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  FileSpreadsheet,
  Settings,
  Monitor,
  Bell,
  LogOut,
  Users,
  Shield,
  AlignLeft,
  Instagram,
  Database,
} from 'lucide-react';
import { useAuth } from '../App';
import { useSidebar } from '../contexts/SidebarContext';
import { useState, useCallback } from 'react';
import './Sidebar.css';

export default function Sidebar() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const { isMobileOpen, isPinnedOpen, closeMobile, togglePinned } = useSidebar();
  const [isHovered, setIsHovered] = useState(false);

  const isAdmin = user?.role === 'admin';

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/export', label: 'Export Excel', icon: FileSpreadsheet },
    { path: '/staging', label: 'Data Persiapan', icon: Database },
    { path: '/accounts', label: 'Akun Instagram', icon: Instagram },
    ...(isAdmin ? [
      { path: '/admin', label: 'Admin Panel', icon: Settings },
      { path: '/jobs', label: 'Job Monitoring', icon: Monitor },
      { path: '/settings', label: 'Pengaturan', icon: Bell },
      { path: '/users', label: 'Kelola User', icon: Users },
    ] : []),
  ];

  const handleLogout = () => {
    logout();
    closeMobile();
  };

  const handleNavClick = useCallback(() => {
    closeMobile();
  }, [closeMobile]);

  const handleMouseEnter = () => {
    if (!isPinnedOpen) {
      setIsHovered(true);
    }
  };

  const handleMouseLeave = () => {
    if (!isPinnedOpen) {
      setIsHovered(false);
    }
  };

  const isExpanded = isPinnedOpen || isHovered;
  const sidebarClass = `sidebar${isExpanded ? ' expanded' : ''}${isMobileOpen ? ' mobile-open' : ''}`;

  return (
    <>
      {isMobileOpen && (
        <div className="sidebar-overlay" onClick={closeMobile} aria-hidden="true" />
      )}
      <aside className={sidebarClass} onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
        <div className="sidebar-header">
          <div className="sidebar-header-content">
            <img src="/assets/images/logo/djpb_logo.png" alt="DJPb" className="sidebar-logo-img" />
            <div className="sidebar-title-group">
              <span className="sidebar-title">Mayz</span>
              <span className="sidebar-subtitle">Monitoring DJPb</span>
            </div>
          </div>
          <button className="sidebar-toggle-btn" onClick={togglePinned} aria-label="Toggle sidebar">
            <AlignLeft size={20} />
          </button>
        </div>
        <nav className="sidebar-nav">
          <div className="nav-section">
            <span className="nav-section-title">Menu</span>
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`nav-link ${location.pathname === item.path ? 'active' : ''}`}
                onClick={handleNavClick}
                title={item.label}
              >
                <item.icon size={20} />
                <span className="nav-label">{item.label}</span>
              </Link>
            ))}
          </div>
        </nav>
        <div className="sidebar-footer">
          <div className="user-card">
            <div className="user-avatar">
              {user?.username?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="user-info">
              <span className="user-name">{user?.nama_lengkap || user?.username}</span>
              <span className="user-role">
                {isAdmin && <Shield size={10} />}
                {isAdmin ? 'Administrator' : 'User'}
              </span>
            </div>
          </div>
          <button className="logout-btn" onClick={handleLogout}>
            <LogOut size={16} />
            <span className="nav-label">Keluar</span>
          </button>
        </div>
      </aside>
    </>
  );
}
