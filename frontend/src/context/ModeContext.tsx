import React, { createContext, useContext, useState, useEffect } from 'react';

export type UIMode = 'simple' | 'dev';

interface ModeContextType {
  mode: UIMode;
  setMode: (mode: UIMode) => void;
  toggleMode: () => void;
  isDev: boolean;
}

const ModeContext = createContext<ModeContextType | undefined>(undefined);

export const ModeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mode, setModeState] = useState<UIMode>(() => {
    const saved = localStorage.getItem('phoenix_ui_mode');
    return (saved === 'dev' || saved === 'simple') ? saved : 'simple';
  });

  const setMode = (newMode: UIMode) => {
    setModeState(newMode);
    localStorage.setItem('phoenix_ui_mode', newMode);
  };

  const toggleMode = () => {
    setMode(mode === 'simple' ? 'dev' : 'simple');
  };

  // Keyboard shortcut: Cmd+D / Ctrl+D / Shift+D
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'd') {
        e.preventDefault();
        toggleMode();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [mode]);

  return (
    <ModeContext.Provider value={{ mode, setMode, toggleMode, isDev: mode === 'dev' }}>
      {children}
    </ModeContext.Provider>
  );
};

export const useMode = (): ModeContextType => {
  const context = useContext(ModeContext);
  if (!context) {
    throw new Error('useMode must be used within a ModeProvider');
  }
  return context;
};
