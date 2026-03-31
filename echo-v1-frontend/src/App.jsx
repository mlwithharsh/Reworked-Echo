import React from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AnimatePresence } from 'framer-motion';

// Components
import Navbar from './components/Navbar';
import Footer from './components/Footer';

// Pages
import LandingPage from './pages/LandingPage';
import ChatPage from './pages/ChatPage';
import AboutPage from './pages/AboutPage';

// Context
import { AIProvider } from './context/AIContext';

const AppContent = () => {
  const location = useLocation();
  const isChatPage = location.pathname === '/chat';

  return (
    <div className="min-h-screen flex flex-col">
      {!isChatPage && <Navbar />}
      
      <main className="flex-1">
        <AnimatePresence mode="wait">
          <Routes location={location} key={location.pathname}>
            <Route path="/" element={<LandingPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/about" element={<AboutPage />} />
          </Routes>
        </AnimatePresence>
      </main>

      {!isChatPage && <Footer />}
      
      <Toaster 
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#12121a',
            color: '#f8fafc',
            border: '1px solid rgba(255, 255, 255, 0.05)',
            borderRadius: '1rem',
            fontSize: '12px',
            fontWeight: '600',
            textTransform: 'uppercase',
            letterSpacing: '0.1em'
          },
        }}
      />
    </div>
  );
};

const App = () => {
  return (
    <AIProvider>
      <Router>
        <AppContent />
      </Router>
    </AIProvider>
  );
};

export default App;
