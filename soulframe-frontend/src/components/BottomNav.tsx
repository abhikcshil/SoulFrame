import { NavLink } from 'react-router-dom';
import { Images, ListVideo, Monitor, UserRound } from 'lucide-react';

interface BottomNavProps {
  variant?: 'mobile' | 'sidebar';
}

export function BottomNav({ variant = 'mobile' }: BottomNavProps) {
  return (
    <nav className={`bottom-nav ${variant === 'sidebar' ? 'sidebar-nav' : ''}`} aria-label="Primary navigation">
      <NavLink to="/devices" className={({ isActive }) => `bottom-nav-item ${isActive ? 'active' : ''}`}>
        <Monitor className="bottom-nav-icon" aria-hidden="true" />
        <span>Devices</span>
      </NavLink>
      <NavLink to="/media" className={({ isActive }) => `bottom-nav-item ${isActive ? 'active' : ''}`}>
        <Images className="bottom-nav-icon" aria-hidden="true" />
        <span>Media</span>
      </NavLink>
      <NavLink to="/playlists" className={({ isActive }) => `bottom-nav-item ${isActive ? 'active' : ''}`}>
        <ListVideo className="bottom-nav-icon" aria-hidden="true" />
        <span>Playlists</span>
      </NavLink>
      <NavLink to="/account" className={({ isActive }) => `bottom-nav-item ${isActive ? 'active' : ''}`}>
        <UserRound className="bottom-nav-icon" aria-hidden="true" />
        <span>Account</span>
      </NavLink>
    </nav>
  );
}
