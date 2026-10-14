import { NavLink } from 'react-router-dom';

interface BottomNavProps {
  variant?: 'mobile' | 'sidebar';
}

export function BottomNav({ variant = 'mobile' }: BottomNavProps) {
  return (
    <nav className={`bottom-nav ${variant === 'sidebar' ? 'sidebar-nav' : ''}`} aria-label="Primary navigation">
      <NavLink to="/devices" className={({ isActive }) => `bottom-nav-item ${isActive ? 'active' : ''}`}>
        <span className="bottom-nav-icon">📱</span>
        <span>Devices</span>
      </NavLink>
      <NavLink to="/media" className={({ isActive }) => `bottom-nav-item ${isActive ? 'active' : ''}`}>
        <span className="bottom-nav-icon">🖼️</span>
        <span>Media</span>
      </NavLink>
      <NavLink to="/playlists" className={({ isActive }) => `bottom-nav-item ${isActive ? 'active' : ''}`}>
        <span className="bottom-nav-icon">📋</span>
        <span>Playlists</span>
      </NavLink>
      <NavLink to="/account" className={({ isActive }) => `bottom-nav-item ${isActive ? 'active' : ''}`}>
        <span className="bottom-nav-icon">👤</span>
        <span>Account</span>
      </NavLink>
    </nav>
  );
}
