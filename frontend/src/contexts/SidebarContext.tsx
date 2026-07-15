import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';

interface SidebarContextType {
  isMobileOpen: boolean;
  isPinnedOpen: boolean;
  toggleMobile: () => void;
  togglePinned: () => void;
  closeMobile: () => void;
}

const SidebarContext = createContext<SidebarContextType | null>(null);

export function SidebarProvider({ children }: { children: ReactNode }) {
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isPinnedOpen, setIsPinnedOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 1024;
      setIsMobile(mobile);
      if (mobile) {
        setIsPinnedOpen(false);
      }
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const toggleMobile = useCallback(() => {
    setIsMobileOpen(prev => !prev);
  }, []);

  const togglePinned = useCallback(() => {
    if (!isMobile) {
      setIsPinnedOpen(prev => !prev);
    }
  }, [isMobile]);

  const closeMobile = useCallback(() => {
    setIsMobileOpen(false);
  }, []);

  return (
    <SidebarContext.Provider value={{ isMobileOpen, isPinnedOpen, toggleMobile, togglePinned, closeMobile }}>
      {children}
    </SidebarContext.Provider>
  );
}

export function useSidebar() {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error('useSidebar must be used within SidebarProvider');
  }
  return context;
}
