import { Outlet } from 'react-router-dom';
import { useState } from 'react';
import Sidebar from './Sidebar';
import Topbar from './Topbar';

export default function Layout() {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-surface-900">
      <Sidebar 
        mobileOpen={mobileSidebarOpen} 
        onMobileClose={() => setMobileSidebarOpen(false)} 
      />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Topbar onMobileMenuToggle={() => setMobileSidebarOpen(!mobileSidebarOpen)} />
        <main className="flex-1 overflow-y-auto p-3 sm:p-4 lg:p-5">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
