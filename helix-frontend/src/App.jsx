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
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import AgentPage from './pages/AgentPage';
import SmartParksWorkspace from './pages/SmartParksWorkspace';

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
            <Route path="/agent" element={<AgentPage />} />
            <Route path="/smart-parks" element={<SmartParksWorkspace />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
          </Routes>
        </AnimatePresence>
      </main>

      {!isChatPage && <Footer />}
      
      <Toaster 
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#fffcf7',
            color: '#2d3a2f',
            border: '1px solid rgba(45, 58, 47, 0.08)',
            borderRadius: '1rem',
            fontSize: '13px',
            fontWeight: '500',
            fontFamily: '"Inter", sans-serif',
            boxShadow: '0 12px 40px rgba(52, 62, 53, 0.12)',
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
