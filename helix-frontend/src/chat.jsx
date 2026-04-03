import React from 'react'
import ReactDOM from 'react-dom/client'
import ChatPage from './pages/ChatPage'
import { AIProvider } from './context/AIContext'
import Navbar from './components/Navbar'
import Footer from './components/Footer'
import { Toaster } from 'react-hot-toast'
import { BrowserRouter as Router } from 'react-router-dom'
import './index.css'

// We use a simplified wrapper since we are in a Multi-Page setup now
const ChatApp = () => (
  <Router>
    <AIProvider>
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1">
          <ChatPage />
        </main>
        <Toaster position="bottom-right" />
      </div>
    </AIProvider>
  </Router>
)

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ChatApp />
  </React.StrictMode>,
)
