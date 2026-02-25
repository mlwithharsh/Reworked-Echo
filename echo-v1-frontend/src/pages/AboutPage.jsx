import React from 'react';
import { motion } from 'framer-motion';
import { Shield, Heart, Eye, Globe, AlertTriangle, CheckCircle2 } from 'lucide-react';

const AboutPage = () => {
  return (
    <div className="pt-32 pb-24 px-6 max-w-5xl mx-auto space-y-24">
      {/* About Section */}
      <section className="space-y-8 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          <h1 className="text-4xl md:text-5xl font-bold">About ECHO</h1>
          <p className="text-solace-purple-glow font-bold uppercase tracking-[0.3em] text-sm">Our Mission</p>
        </motion.div>
        
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-lg text-text-secondary leading-relaxed max-w-3xl mx-auto"
        >
          ECHO was created with a single purpose: to ensure that no one has to face their emotional struggles alone. We combine cutting-edge emotionally intelligent AI with a deeply human-centric design to provide a safe, non-judgmental space for expression.
        </motion.p>
      </section>

      {/* Core Values */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <ValueCard 
          icon={Shield} 
          title="Emotional Safety" 
          desc="Your vulnerability is respected. We provide a space where you can be your true self without fear." 
        />
        <ValueCard 
          icon={Heart} 
          title="Empathetic Intelligence" 
          desc="Our AI doesn't just process text; it strives to understand the emotional weight behind your words." 
        />
        <ValueCard 
          icon={Eye} 
          title="Total Confidentiality" 
          desc="Your data is encrypted and your conversations are private. We prioritize your trust above all else." 
        />
      </section>

      {/* Important Notice */}
      <section className="glass-card p-8 md:p-12 border-solace-blue/20 bg-solace-blue/5">
        <div className="flex flex-col md:flex-row items-start space-y-6 md:space-y-0 md:space-x-8">
          <div className="w-16 h-16 rounded-2xl bg-solace-blue/10 flex items-center justify-center shrink-0">
            <AlertTriangle className="w-8 h-8 text-solace-blue" />
          </div>
          <div className="space-y-4">
            <h2 className="text-2xl font-bold text-white">Important Notice</h2>
            <div className="space-y-4 text-text-secondary leading-relaxed">
              <p>
                While ECHO is designed to provide emotional support and guidance, it is **not a replacement for professional therapy, counseling, or medical intervention.**
              </p>
              <p>
                If you are experiencing a crisis, thoughts of self-harm, or severe psychological distress, please reach out to professional emergency services or a licensed mental health practitioner immediately.
              </p>
            </div>
            <div className="flex flex-wrap gap-4 pt-4">
              <a href="https://www.befrienders.org/" target="_blank" rel="noopener noreferrer" className="text-xs font-bold text-solace-blue-glow hover:underline uppercase tracking-widest">Global Helplines</a>
              <a href="https://www.who.int/news-room/fact-sheets/detail/mental-health-strengthening-our-response" target="_blank" rel="noopener noreferrer" className="text-xs font-bold text-solace-blue-glow hover:underline uppercase tracking-widest">WHO Resources</a>
            </div>
          </div>
        </div>
      </section>

      {/* Privacy & Safety */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
        <div className="space-y-6">
          <h2 className="text-3xl font-bold">Privacy & Safety</h2>
          <p className="text-text-secondary leading-relaxed">
            We believe that privacy is a fundamental human right, especially when it comes to emotional wellness. 
          </p>
          <ul className="space-y-4">
            <SafetyItem text="End-to-end encryption for all messages." />
            <SafetyItem text="No personal data sold to third parties." />
            <SafetyItem text="Anonymous interactions by default." />
            <SafetyItem text="Secure, isolated neural processing." />
          </ul>
        </div>
        <div className="relative">
          <div className="absolute inset-0 bg-solace-blue/20 blur-[100px] rounded-full" />
          <div className="glass-card p-8 relative z-10 border-white/10">
            <Globe className="w-12 h-12 text-solace-blue mb-6" />
            <h3 className="text-xl font-bold mb-4">Global Vision</h3>
            <p className="text-sm text-text-secondary leading-relaxed">
              Our vision is to create a world where emotionally intelligent support is accessible to everyone, everywhere, at any time. We are building the future of compassionate technology.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
};

const ValueCard = ({ icon: Icon, title, desc }) => (
  <div className="space-y-4 p-6 rounded-3xl hover:bg-white/5 transition-colors duration-300">
    <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center">
      <Icon className="w-6 h-6 text-solace-purple" />
    </div>
    <h3 className="text-xl font-bold text-white">{title}</h3>
    <p className="text-sm text-text-secondary leading-relaxed">{desc}</p>
  </div>
);

const SafetyItem = ({ text }) => (
  <li className="flex items-center space-x-3">
    <CheckCircle2 className="w-5 h-5 text-solace-cyan shrink-0" />
    <span className="text-sm text-text-secondary font-medium">{text}</span>
  </li>
);

export default AboutPage;
