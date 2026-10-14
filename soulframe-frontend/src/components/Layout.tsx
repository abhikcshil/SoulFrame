import { ReactNode } from 'react';
import { BottomNav } from './BottomNav';

interface LayoutProps {
  children: ReactNode;
  showNav?: boolean;
}

export function Layout({ children, showNav = true }: LayoutProps) {
  return (
    <div className={showNav ? 'app-shell' : 'app-shell app-shell-minimal'}>
      {showNav && (
        <aside className="desktop-sidebar">
          <div className="brand-lockup" aria-label="SoulFrame">
            <span className="brand-mark" aria-hidden="true">S</span>
            <span><strong>SoulFrame</strong><small>Digital art, alive</small></span>
          </div>
          <BottomNav variant="sidebar" />
        </aside>
      )}
      <main className="app-main"><div className="page-transition">{children}</div></main>
      {showNav && <BottomNav />}
    </div>
  );
}
