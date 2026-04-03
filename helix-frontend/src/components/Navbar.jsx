import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Heart, MessageSquare, Info, Menu, X } from 'lucide-react';

const Navbar = () => {
  const [isOpen, setIsOpen] = React.useState(false);
  const location = useLocation();

  const navItems = [
    { name: 'Home', path: '/', icon: Heart },
    { name: 'Chat', path: '/chat', icon: MessageSquare },
    { name: 'About', path: '/about', icon: Info },
  ];

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-[rgba(244,239,230,0.82)] backdrop-blur-lg border-b border-black/5">
      <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
        <a href="/" className="flex items-center space-x-3 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-solace-purple to-solace-blue flex items-center justify-center shadow-glow-purple group-hover:scale-110 transition-transform duration-500">
            <Heart className="w-5 h-5 text-white fill-white/20" />
          </div>
          <span className="text-xl font-bold tracking-tight text-text-primary uppercase tracking-[0.1em]">
            H<span className="text-solace-purple">ELIX</span>
          </span>
        </a>

        {/* Desktop Nav */}
        <div className="hidden md:flex items-center space-x-8">
          {navItems.map((item) => (
            <a
              key={item.path}
              href={item.path === '/' ? '/' : `${item.path}.html`}
              className={`nav-link flex items-center space-x-2 ${location.pathname === (item.path === '/' ? '/' : `${item.path}.html`) ? 'text-text-primary' : ''
                }`}
            >
              <item.icon className="w-4 h-4" />
              <span>{item.name}</span>
            </a>
          ))}
          <a href="/chat.html" className="btn-solace-primary !py-2 !px-6 text-sm">
            Get Support
          </a>
        </div>

        {/* Mobile Menu Toggle */}
        <button className="md:hidden text-text-primary" onClick={() => setIsOpen(!isOpen)}>
          {isOpen ? <X /> : <Menu />}
        </button>
      </div>

      {/* Mobile Nav */}
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="md:hidden bg-background-soft border-b border-black/5 px-6 py-8 space-y-6"
        >
          {navItems.map((item) => (
            <a
              key={item.path}
              href={item.path === '/' ? '/' : `${item.path}.html`}
              onClick={() => setIsOpen(false)}
              className="flex items-center space-x-4 text-text-secondary"
            >
              <item.icon className="w-5 h-5" />
              <span className="text-lg font-medium">{item.name}</span>
            </a>
          ))}
          <a
            href="/chat.html"
            onClick={() => setIsOpen(false)}
            className="block btn-solace-primary text-center"
          >
            Get Support
          </a>
        </motion.div>
      )}
    </nav>
  );
};

export default Navbar;
