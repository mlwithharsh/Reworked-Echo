import React from 'react'
import ReactDOM from 'react-dom/client'
import AboutPage from './pages/AboutPage'
import Navbar from './components/Navbar'
import Footer from './components/Footer'
import { Toaster } from 'react-hot-toast'
import { BrowserRouter as Router } from 'react-router-dom'
import './index.css'

const AboutApp = () => (
  <Router>
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 pt-20">
        <AboutPage />
      </main>
      <Footer />
      <Toaster position="bottom-right" />
    </div>
  </Router>
)

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AboutApp />
  </React.StrictMode>,
)
