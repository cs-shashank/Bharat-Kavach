import React, { useState, useEffect } from 'react';
import Dashboard from './components/dashboard/Dashboard';
import CitizenApp from './components/dashboard/CitizenApp';

function App() {
  const [view, setView] = useState('officer');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const viewParam = params.get('view');
    if (viewParam === 'citizen') {
      setView('citizen');
    } else {
      setView('officer');
    }
  }, []);

  return (
    <div className="App selection:bg-accent-blue/30 selection:text-white flex justify-center items-center min-h-screen bg-slate-950">
      {view === 'citizen' ? <CitizenApp /> : <Dashboard />}
    </div>
  );
}

export default App;
