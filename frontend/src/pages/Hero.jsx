import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Shield, Activity, AlertTriangle, Brain, ChevronRight, CheckCircle,
  Zap, Target, Eye, Lock, TrendingUp, Database, ArrowRight, Play, Sun, Moon,
  Menu, X, Landmark, ExternalLink, FileText, Radio, Banknote, ArrowUpRight
} from 'lucide-react';
import { getMetrics, getHealth } from '../api';

export default function Hero() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [systemStatus, setSystemStatus] = useState('connecting');
  const [darkMode, setDarkMode] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    Promise.all([getHealth(), getMetrics()])
      .then(([health, metrics]) => {
        setSystemStatus(health?.status === 'operational' ? 'operational' : 'connecting');
        setStats(metrics);
      })
      .catch(() => setSystemStatus('connecting'));
  }, []);

  return (
    <div className={`min-h-screen transition-colors duration-300 overflow-x-hidden ${
      darkMode 
        ? 'bg-gradient-to-br from-surface-900 via-[#0a0e17] to-surface-800 text-text-primary' 
        : 'bg-gradient-to-br from-slate-50 via-white to-slate-100 text-slate-900'
    }`}>
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className={`absolute top-20 left-10 w-72 h-72 rounded-full blur-3xl animate-pulse ${
          darkMode ? 'bg-accent/5' : 'bg-blue-200/30'
        }`}></div>
        <div className={`absolute bottom-20 right-10 w-96 h-96 rounded-full blur-3xl animate-pulse ${
          darkMode ? 'bg-severity-critical/5' : 'bg-purple-200/30'
        }`}></div>
        <div className={`absolute top-1/2 left-1/2 w-64 h-64 rounded-full blur-3xl animate-pulse ${
          darkMode ? 'bg-severity-medium/5' : 'bg-teal-200/30'
        }`}></div>
      </div>

      {/* Navigation - Modern Capsule Style */}
      <nav className="relative sticky top-0 z-50 py-4 sm:py-6 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between">
            {/* Logo */}
            <div className="flex items-center gap-2 sm:gap-3">
              <div className="relative">
                <img 
                  src="/Agentic_HoneyPot_Logo.png" 
                  alt="Agentic HoneyPot Logo" 
                  className="h-8 w-8 sm:h-10 sm:w-10 object-contain"
                />
              </div>
              <div>
                <div className={`text-base sm:text-lg md:text-xl font-bold tracking-tight ${darkMode ? 'text-text-primary' : 'text-slate-900'}`}>Agentic HoneyPot</div>
              </div>
            </div>

            {/* Capsule Navigation - Desktop */}
            <div className={`hidden md:flex items-center gap-1 px-2 py-2 rounded-full backdrop-blur-xl border ${
              darkMode 
                ? 'bg-surface-800/50 border-border/50' 
                : 'bg-white/80 border-slate-200 shadow-lg shadow-slate-200/50'
            }`}>
              <a href="#features" className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                darkMode
                  ? 'text-text-secondary hover:text-text-primary hover:bg-surface-700'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}>Features</a>
              <a href="#platform" className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                darkMode
                  ? 'text-text-secondary hover:text-text-primary hover:bg-surface-700'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}>Platform</a>
              <a href="#report" className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                darkMode
                  ? 'text-text-secondary hover:text-text-primary hover:bg-surface-700'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}>Report</a>
              <button
                onClick={() => navigate('/dashboard')}
                className={`ml-2 px-5 py-2 rounded-full text-sm font-semibold transition-all ${
                  darkMode
                    ? 'bg-accent text-surface-900 hover:bg-accent/90'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
              >
                Get Started
              </button>
            </div>

            {/* Mobile Menu & Dark Mode Toggle */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setDarkMode(!darkMode)}
                className={`p-2 sm:p-2.5 rounded-full backdrop-blur-xl border transition-all ${
                  darkMode
                    ? 'bg-surface-800/50 border-border/50 text-text-primary hover:bg-surface-700'
                    : 'bg-white/80 border-slate-200 text-slate-900 hover:bg-slate-100 shadow-lg shadow-slate-200/50'
                }`}
              >
                {darkMode ? <Sun size={20} /> : <Moon size={20} />}
              </button>
              
              {/* Mobile Menu Button */}
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className={`md:hidden p-2 sm:p-2.5 rounded-full backdrop-blur-xl border transition-all ${
                  darkMode
                    ? 'bg-surface-800/50 border-border/50 text-text-primary hover:bg-surface-700'
                    : 'bg-white/80 border-slate-200 text-slate-900 hover:bg-slate-100 shadow-lg shadow-slate-200/50'
                }`}
              >
                {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Menu Dropdown */}
        {mobileMenuOpen && (
          <div className={`md:hidden absolute top-full left-0 right-0 mt-2 mx-4 rounded-2xl backdrop-blur-xl border overflow-hidden shadow-xl animate-slide-up ${
            darkMode
              ? 'bg-surface-800/95 border-border/50'
              : 'bg-white/95 border-slate-200'
          }`}>
            <div className="p-4 space-y-2">
              <a
                href="#features"
                onClick={() => setMobileMenuOpen(false)}
                className={`block px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                  darkMode
                    ? 'text-text-secondary hover:text-text-primary hover:bg-surface-700'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                Features
              </a>
              <a
                href="#platform"
                onClick={() => setMobileMenuOpen(false)}
                className={`block px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                  darkMode
                    ? 'text-text-secondary hover:text-text-primary hover:bg-surface-700'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                Platform
              </a>
              <a
                href="#report"
                onClick={() => setMobileMenuOpen(false)}
                className={`block px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                  darkMode
                    ? 'text-text-secondary hover:text-text-primary hover:bg-surface-700'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                Report
              </a>
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  navigate('/dashboard');
                }}
                className={`w-full px-4 py-3 rounded-xl text-sm font-semibold transition-all ${
                  darkMode
                    ? 'bg-accent text-surface-900 hover:bg-accent/90'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
              >
                Get Started
              </button>
            </div>
          </div>
        )}
      </nav>

      {/* Hero Section - Modern Layout with Integrated Dashboard */}
      <section className="relative max-w-7xl mx-auto px-4 sm:px-6 pt-8 sm:pt-12 lg:pt-16 pb-0 overflow-visible">
        <div className="grid lg:grid-cols-2 gap-12 items-center mb-20">
          {/* Left Content */}
          <div className="animate-slide-up space-y-8">
            {/* Status Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full backdrop-blur-xl border ${
              darkMode
                ? 'bg-surface-800/50 border-accent/20'
                : 'bg-white/80 border-blue-200 shadow-lg shadow-blue-100/50'
            }">
              <div className="relative">
                <div className={`w-2 h-2 rounded-full ${systemStatus === 'operational' ? (darkMode ? 'bg-severity-low' : 'bg-green-500') : (darkMode ? 'bg-severity-medium' : 'bg-yellow-500')}`} />
                <div className={`absolute inset-0 w-2 h-2 rounded-full ${systemStatus === 'operational' ? (darkMode ? 'bg-severity-low' : 'bg-green-500') : (darkMode ? 'bg-severity-medium' : 'bg-yellow-500')} animate-ping`} />
              </div>
              <span className={`text-xs font-semibold uppercase tracking-wider ${
                darkMode ? 'text-text-primary' : 'text-slate-700'
              }`}>
                {systemStatus === 'operational' ? 'Live & Operational' : 'Initializing...'}
              </span>
            </div>

            {/* Main Heading */}
            <div className="space-y-4 sm:space-y-6">
              <h1 className={`text-3xl sm:text-5xl md:text-6xl lg:text-7xl font-bold leading-[1.1] tracking-tight ${
                darkMode ? 'text-text-primary' : 'text-slate-900'
              }`}>
                Autonomous AI{' '}
                <span className={darkMode ? 'text-accent' : 'text-blue-600'}>Defense</span>
                <br />
                Against Scam Operations
              </h1>

              <p className={`text-base sm:text-lg md:text-xl leading-relaxed max-w-xl ${
                darkMode ? 'text-text-secondary' : 'text-slate-600'
              }`}>
                Deploy intelligent honeypot agents powered by advanced LLMs to detect, 
                engage, and dismantle sophisticated financial fraud with real-time intelligence.
              </p>
            </div>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row items-start gap-4">
              <button
                onClick={() => navigate('/dashboard')}
                className={`group px-8 py-4 rounded-2xl font-semibold transition-all hover:scale-105 flex items-center gap-3 text-lg shadow-xl ${
                  darkMode
                    ? 'bg-accent text-surface-900 hover:shadow-accent/30'
                    : 'bg-blue-600 text-white hover:shadow-blue-500/30'
                }`}
              >
                Get Started Free
                <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
              </button>
              <button className={`px-8 py-4 rounded-2xl font-semibold transition-all backdrop-blur-xl border-2 ${
                darkMode
                  ? 'bg-surface-800/50 border-border hover:border-accent/50 text-text-primary hover:bg-surface-700/50'
                  : 'bg-white/80 border-slate-200 text-slate-900 hover:border-blue-300 hover:bg-white shadow-lg'
              }`}>
                Watch Demo
              </button>
            </div>
          </div>

          {/* Right - Dashboard Preview (Half Visible) */}
          <div className="relative lg:block hidden animate-fade-in-delay">
            <div className="absolute -right-32 top-0 w-[600px] h-[450px]">
              {/* Dashboard mockup with 3D tilt */}
              <div className="relative transform rotate-2 hover:rotate-0 transition-transform duration-500">
                <div className={`rounded-2xl border-2 overflow-hidden shadow-2xl ${
                  darkMode
                    ? 'bg-surface-800/90 border-accent/20 shadow-accent/10'
                    : 'bg-white border-slate-200 shadow-slate-300/50'
                }`} style={{ transform: 'perspective(1000px) rotateY(-5deg)' }}>
                  {/* Browser bar */}
                  <div className={`px-4 py-3 border-b flex items-center gap-2 ${
                    darkMode ? 'bg-surface-700 border-border' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <div className="flex gap-1.5">
                      <div className="w-3 h-3 rounded-full bg-red-500"></div>
                      <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                      <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    </div>
                    <div className={`ml-4 text-xs font-mono ${
                      darkMode ? 'text-text-muted' : 'text-slate-500'
                    }`}>Command Center — Live Session Analysis</div>
                  </div>

                  {/* Dashboard content */}
                  <div className={`p-6 space-y-4 ${
                    darkMode ? 'bg-gradient-to-br from-surface-900 to-surface-800' : 'bg-gradient-to-br from-slate-50 to-white'
                  }`}>
                    {/* Stats row */}
                    <div className="grid grid-cols-3 gap-3">
                      {[1, 2, 3].map(i => (
                        <div key={i} className={`p-4 rounded-xl border ${
                          darkMode ? 'bg-surface-700/50 border-border/50' : 'bg-white border-slate-200'
                        }`}>
                          <div className={`text-2xl font-bold font-mono mb-1 ${
                            darkMode ? 'text-accent' : 'text-blue-600'
                          }`}>{'847'}</div>
                          <div className={`text-xs ${
                            darkMode ? 'text-text-muted' : 'text-slate-500'
                          }`}>Sessions</div>
                        </div>
                      ))}
                    </div>

                    {/* Chart placeholder */}
                    <div className={`h-32 rounded-xl border flex items-end gap-2 p-4 ${
                      darkMode ? 'bg-surface-700/30 border-border/50' : 'bg-slate-50 border-slate-200'
                    }`}>
                      {[40, 70, 45, 85, 60, 90, 55].map((h, i) => (
                        <div key={i} className={`flex-1 rounded-t transition-all ${
                          darkMode ? 'bg-accent/70' : 'bg-blue-500'
                        }`} style={{ height: `${h}%` }}></div>
                      ))}
                    </div>

                    {/* Badge */}
                    <div className="flex items-center gap-2">
                      <Shield size={16} className={darkMode ? 'text-severity-critical' : 'text-red-500'} />
                      <span className={`text-xs font-semibold ${
                        darkMode ? 'text-severity-critical' : 'text-red-600'
                      }`}>24 Critical Threats Detected</span>
                    </div>
                  </div>

                  {/* Gradient overlay to fade right edge */}
                  <div className="absolute inset-y-0 right-0 w-32 bg-gradient-to-l from-surface-900/80 to-transparent pointer-events-none"></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Live Stats Grid */}

      </section>

      {/* Features Section */}
      <section id="features" className="relative max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-20 lg:py-24 border-t border-border/30">
        <div className="text-center mb-12 sm:mb-16">
          <div className={`inline-block px-3 sm:px-4 py-1 sm:py-1.5 rounded-full border text-[10px] sm:text-xs font-semibold uppercase tracking-wider mb-3 sm:mb-4 ${
            darkMode ? 'bg-accent/10 border-accent/20 text-accent' : 'bg-blue-50 border-blue-200 text-blue-700'
          }`}>
            Platform Capabilities
          </div>
          <h2 className={`text-3xl sm:text-4xl lg:text-5xl font-bold mb-3 sm:mb-4 px-4 ${
            darkMode ? 'text-text-primary' : 'text-slate-900'
          }`}>Enterprise-Grade Threat Intelligence</h2>
          <p className={`text-base sm:text-lg max-w-2xl mx-auto px-4 ${
            darkMode ? 'text-text-secondary' : 'text-slate-600'
          }`}>
            Military-grade detection system built for SOC analysts, security researchers, and financial institutions
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
          {[
            {
              icon: Shield,
              title: 'Autonomous Honeypot Agents',
              desc: 'Deploy AI agents that engage scammers naturally using adaptive dialogue strategies',
              color: 'accent'
            },
            {
              icon: Brain,
              title: 'LLM-Powered Classification',
              desc: 'Advanced intent detection and social engineering pattern recognition',
              color: 'severity-medium'
            },
            {
              icon: Target,
              title: 'Real-Time Risk Scoring',
              desc: 'Multi-dimensional weighted model with explainable decision trees',
              color: 'severity-critical'
            },
            {
              icon: Database,
              title: 'Intelligence Extraction',
              desc: 'Automated extraction of UPI IDs, phone numbers, and phishing infrastructure',
              color: 'severity-high'
            },
            {
              icon: Eye,
              title: 'SOC Analyst Console',
              desc: 'Professional investigation workbench with audit trails and case management',
              color: 'accent'
            },
            {
              icon: Lock,
              title: 'Cross-Session Correlation',
              desc: 'Link related threats across sessions for campaign tracking and attribution',
              color: 'severity-low'
            }
          ].map((feature, i) => (
            <div key={i} className="group relative">
              <div className={`absolute inset-0 rounded-xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity ${
                darkMode ? `bg-${feature.color}/5` : 'bg-blue-100/50'
              }`}></div>
              <div className={`relative backdrop-blur-sm border rounded-xl p-5 sm:p-7 transition-all ${
                darkMode ? 'bg-surface-800/40 border-border/50 hover:border-accent/40' : 'bg-white/80 border-slate-200 hover:border-blue-300 shadow-lg'
              }`}>
                <div className={`inline-flex p-2.5 sm:p-3 rounded-lg border mb-3 sm:mb-4 ${
                  darkMode ? `bg-${feature.color}/10 border-${feature.color}/20` : 'bg-blue-50 border-blue-200'
                }`}>
                  <feature.icon className={`text-${feature.color}`} size={24} />
                </div>
                <h3 className={`text-base sm:text-lg font-bold mb-1.5 sm:mb-2 ${
                  darkMode ? 'text-text-primary' : 'text-slate-900'
                }`}>{feature.title}</h3>
                <p className={`text-xs sm:text-sm leading-relaxed ${
                  darkMode ? 'text-text-secondary' : 'text-slate-600'
                }`}>{feature.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Platform Preview Section */}
      <section id="platform" className={`relative max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-20 lg:py-24 border-t ${
        darkMode ? 'border-border/30' : 'border-slate-200'
      }`}>
        <div className="text-center mb-8 sm:mb-12">
          <div className={`inline-block px-3 sm:px-4 py-1 sm:py-1.5 rounded-full border text-[10px] sm:text-xs font-semibold uppercase tracking-wider mb-3 sm:mb-4 ${
            darkMode ? 'bg-severity-critical/10 border-severity-critical/20 text-severity-critical' : 'bg-red-50 border-red-200 text-red-700'
          }`}>
            Live Platform
          </div>
          <h2 className={`text-3xl sm:text-4xl lg:text-5xl font-bold mb-3 sm:mb-4 px-4 ${
            darkMode ? 'text-text-primary' : 'text-slate-900'
          }`}>Built for Security Professionals</h2>
          <p className={`text-base sm:text-lg max-w-2xl mx-auto mb-8 sm:mb-12 px-4 ${
            darkMode ? 'text-text-secondary' : 'text-slate-600'
          }`}>
            Every feature designed with analysts in mind — from triage to investigation to intelligence export
          </p>
        </div>

        {/* Mock dashboard preview */}
        <div className={`relative rounded-xl sm:rounded-2xl border overflow-hidden shadow-2xl ${
          darkMode
            ? 'border-accent/20 shadow-accent/10'
            : 'border-slate-200 shadow-slate-300/50'
        }`}>
          <div className={`absolute inset-0 ${
            darkMode ? 'bg-gradient-to-br from-accent/5 to-severity-critical/5' : 'bg-gradient-to-br from-blue-50 to-purple-50'
          }`}></div>
          <div className={`relative backdrop-blur-xl p-4 sm:p-8 ${
            darkMode ? 'bg-surface-800/80' : 'bg-white/80'
          }`}>
            <div className="flex items-center gap-1.5 sm:gap-2 mb-4 sm:mb-6">
              <div className={`w-2 sm:w-3 h-2 sm:h-3 rounded-full ${
                darkMode ? 'bg-severity-critical' : 'bg-red-500'
              }`}></div>
              <div className={`w-2 sm:w-3 h-2 sm:h-3 rounded-full ${
                darkMode ? 'bg-severity-medium' : 'bg-yellow-500'
              }`}></div>
              <div className={`w-2 sm:w-3 h-2 sm:h-3 rounded-full ${
                darkMode ? 'bg-severity-low' : 'bg-green-500'
              }`}></div>
            </div>
            <div className={`aspect-video rounded-lg border flex items-center justify-center ${
              darkMode
                ? 'bg-gradient-to-br from-surface-900 via-surface-800 to-surface-900 border-border/30'
                : 'bg-gradient-to-br from-slate-50 via-white to-slate-50 border-slate-200'
            }`}>
              <div className="text-center px-4">
                <Shield size={48} className={`mx-auto mb-3 sm:mb-4 opacity-50 sm:w-16 sm:h-16 ${
                  darkMode ? 'text-accent' : 'text-blue-600'
                }`} />
                <p className={`text-xs sm:text-sm ${
                  darkMode ? 'text-text-muted' : 'text-slate-600'
                }`}>Command Center • Live Sessions • Investigation Workspace</p>
              </div>
            </div>
          </div>
        </div>

        <div className="text-center mt-8 sm:mt-12 px-4">
          <button
            onClick={() => navigate('/dashboard')}
            className={`w-full sm:w-auto inline-flex items-center justify-center gap-2 sm:gap-3 px-6 sm:px-8 py-3 sm:py-4 rounded-2xl font-semibold transition-all hover:scale-105 text-base shadow-xl ${
              darkMode
                ? 'bg-gradient-to-r from-severity-critical to-severity-high text-white hover:shadow-severity-critical/20'
                : 'bg-gradient-to-r from-red-600 to-orange-600 text-white hover:shadow-red-500/30'
            }`}
          >
            <Zap size={18} className="sm:w-5 sm:h-5" />
            Launch Full Console
            <ChevronRight size={18} className="sm:w-5 sm:h-5" />
          </button>
        </div>
      </section>

      {/* Report to Authorities */}
      <section className={`relative py-12 sm:py-16 lg:py-20 ${
        darkMode ? 'bg-gradient-to-b from-surface-900 via-surface-950 to-surface-900' : 'bg-gradient-to-b from-slate-50 via-white to-slate-50'
      }`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-center gap-3 mb-3 sm:mb-4">
            <Landmark className={`w-5 h-5 sm:w-6 sm:h-6 ${darkMode ? 'text-accent' : 'text-teal-600'}`} />
            <h2 className={`text-xl sm:text-2xl lg:text-3xl font-bold text-center ${
              darkMode ? 'text-text-primary' : 'text-slate-900'
            }`}>Report to Authorities</h2>
          </div>
          <p className={`text-center text-xs sm:text-sm max-w-2xl mx-auto mb-8 sm:mb-12 ${
            darkMode ? 'text-text-secondary' : 'text-slate-600'
          }`}>
            Escalate confirmed scams to Indian law enforcement, telecom regulators, and payment authorities with built-in portal links
          </p>

          {/* Regulatory Portal Cards */}
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            {[
              {
                icon: Shield,
                title: 'Cyber Crime Portal (NCRP)',
                badge: 'MHA / Law Enforcement',
                desc: 'File complaints for financial fraud, UPI scams, impersonation, phishing, and identity theft.',
                url: 'https://cybercrime.gov.in',
                color: 'severity-critical',
                useFor: ['Financial fraud', 'UPI scams', 'Phishing']
              },
              {
                icon: Banknote,
                title: 'NPCI / Bank Escalation',
                badge: 'Payments',
                desc: 'Escalate UPI ID misuse, payment redirection, and merchant impersonation to banks and NPCI.',
                url: 'https://www.npci.org.in',
                color: 'severity-high',
                useFor: ['UPI fraud', 'Payment redirect', 'Merchant scams']
              },
              {
                icon: Radio,
                title: 'Sanchaar Saathi (DoT)',
                badge: 'Telecom / DoT',
                desc: 'Report phone number misuse, SIM fraud, SMS scams, and spoofed caller IDs to telecom authority.',
                url: 'https://www.sancharsaathi.gov.in',
                color: 'accent',
                useFor: ['SIM fraud', 'SMS scams', 'Spoofed calls']
              }
            ].map((portal, i) => (
              <div key={i} className="group relative">
                <div className={`absolute inset-0 rounded-xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity ${
                  darkMode ? `bg-${portal.color}/5` : 'bg-blue-100/50'
                }`}></div>
                <div className={`relative backdrop-blur-sm border rounded-xl p-5 sm:p-7 transition-all h-full flex flex-col ${
                  darkMode ? 'bg-surface-800/40 border-border/50 hover:border-accent/40' : 'bg-white/80 border-slate-200 hover:border-teal-300 shadow-lg'
                }`}>
                  <div className="flex items-center gap-3 mb-3">
                    <div className={`inline-flex p-2.5 rounded-lg border ${
                      darkMode ? `bg-${portal.color}/10 border-${portal.color}/20` : 'bg-teal-50 border-teal-200'
                    }`}>
                      <portal.icon className={`text-${portal.color}`} size={22} />
                    </div>
                    <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full border ${
                      darkMode ? `bg-${portal.color}/10 border-${portal.color}/20 text-${portal.color}` : 'bg-teal-50 border-teal-200 text-teal-700'
                    }`}>{portal.badge}</span>
                  </div>
                  <h3 className={`text-base sm:text-lg font-bold mb-1.5 ${
                    darkMode ? 'text-text-primary' : 'text-slate-900'
                  }`}>{portal.title}</h3>
                  <p className={`text-xs sm:text-sm leading-relaxed mb-4 flex-1 ${
                    darkMode ? 'text-text-secondary' : 'text-slate-600'
                  }`}>{portal.desc}</p>

                  {/* Use-for tags */}
                  <div className="flex flex-wrap gap-1.5 mb-4">
                    {portal.useFor.map((tag, j) => (
                      <span key={j} className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium ${
                        darkMode ? 'bg-surface-600/60 text-text-muted' : 'bg-slate-100 text-slate-600'
                      }`}>{tag}</span>
                    ))}
                  </div>

                  <a
                    href={portal.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`inline-flex items-center gap-2 text-xs font-semibold transition-colors ${
                      darkMode ? 'text-accent hover:text-accent-glow' : 'text-teal-600 hover:text-teal-700'
                    }`}
                  >
                    <ExternalLink size={14} />
                    Open Portal
                    <ArrowUpRight size={12} />
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className={`relative border-t mt-16 sm:mt-20 lg:mt-24 backdrop-blur-sm ${
        darkMode ? 'border-border/30 bg-surface-800/20' : 'border-slate-200 bg-slate-50/50'
      }`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
          <div className="flex flex-col md:flex-row items-center justify-center gap-4 sm:gap-6">
            <div className="flex items-center gap-2 sm:gap-3">
              <img src="/Agentic_HoneyPot_Logo.png" alt="Agentic HoneyPot" className="w-8 h-8 sm:w-10 sm:h-10" />
              <div className="text-center md:text-left">
                <div className={`text-sm sm:text-base font-bold ${
                  darkMode ? 'text-text-primary' : 'text-slate-900'
                }`}>Agnetic HoneyPot</div>
                <div className={`text-[10px] sm:text-xs ${
                  darkMode ? 'text-text-muted' : 'text-slate-600'
                }`}>Enterprise Scam Detection & Intelligence Platform</div>
              </div>
            </div>
          </div>
          <div className={`mt-6 sm:mt-8 pt-6 sm:pt-8 border-t text-center text-xs sm:text-sm ${
            darkMode ? 'border-border/30 text-text-muted' : 'border-slate-200 text-slate-600'
          }`}>
            <p>© 2026 Agnetic HoneyPot Platform. SOC-Grade Defense Against Financial Fraud.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
