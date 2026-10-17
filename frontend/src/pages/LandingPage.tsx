import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  Plane,
  Cpu,
  Sliders,
  Package,
  ShieldCheck,
  TrendingUp,
  ArrowRight,
  Sparkles,
  Layers,
  Search,
  ChevronDown,
  Lock,
  GitBranch,
  Shield,
  ChevronRight,
  Server,
  CheckCircle2,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import type { UserRole } from '../types/api';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { switchDemoRole } = useAuth();

  // Interactive state
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [heroFleetSize, setHeroFleetSize] = useState('24 Airframes (Tactical)');
  const [heroRole, setHeroRole] = useState<UserRole>('commander');
  const [heroEmail, setHeroEmail] = useState('commander@aeropulse.defense.local');
  const [activeTab, setActiveTab] = useState<'entity' | 'trajectory' | 'spares' | 'simulation'>('entity');
  const [formSubmitting, setFormSubmitting] = useState(false);

  const handleHeroSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormSubmitting(true);
    try {
      await switchDemoRole(heroRole);
      navigate('/dashboard');
    } catch {
      navigate('/login');
    } finally {
      setFormSubmitting(false);
    }
  };

  const navMenuItems = [
    {
      id: 'platform',
      label: 'Platform',
      items: [
        {
          title: 'Fleet Intelligence Cockpit',
          desc: 'Real-time Ao readiness metrics and cross-airframe health index matrix.',
          icon: <Activity className="w-4 h-4 text-[#0D6553]" />,
          path: '/dashboard',
        },
        {
          title: 'Airframe Digital Twin',
          desc: 'High-fidelity topological schematics with degradation curves.',
          icon: <Plane className="w-4 h-4 text-[#0D6553]" />,
          path: '/aircraft',
        },
        {
          title: 'ML Diagnostics & SHAP',
          desc: 'Multivariate sensor anomaly attribution and quantile RUL regression.',
          icon: <Cpu className="w-4 h-4 text-[#0D6553]" />,
          path: '/components',
        },
      ],
    },
    {
      id: 'solutions',
      label: 'Solutions',
      items: [
        {
          title: 'Predictive Queue & Advisories',
          desc: 'Priority human-in-the-loop work order creation and justification audit.',
          icon: <ShieldCheck className="w-4 h-4 text-[#0D6553]" />,
          path: '/advisories',
        },
        {
          title: 'Maintenance Depot Planning',
          desc: 'Depot bay capacity load balancing with proactive inspection bundling.',
          icon: <Layers className="w-4 h-4 text-[#0D6553]" />,
          path: '/planning',
        },
        {
          title: 'Spares Supply Chain Risk',
          desc: 'Automated shortfall alerts when lead time exceeds component RUL.',
          icon: <Package className="w-4 h-4 text-[#0D6553]" />,
          path: '/spares',
        },
      ],
    },
    {
      id: 'simulation',
      label: 'Simulation Engine',
      items: [
        {
          title: 'Monte Carlo What-If Engine',
          desc: 'Stochastic dual-leg policy evaluation under stress conditions.',
          icon: <Sliders className="w-4 h-4 text-[#0D6553]" />,
          path: '/scenarios',
        },
      ],
    },
  ];

  const coreModules = [
    {
      icon: <Activity className="w-5 h-5 text-[#0D6553]" />,
      tag: 'OPERATIONS',
      title: 'Contextual Fleet Cockpit',
      desc: 'Connect airframe sensor streams, maintenance logs, and operational tempo into an integrated single pane of glass.',
      metric: '94.2% Availability Target',
      path: '/dashboard',
    },
    {
      icon: <Plane className="w-5 h-5 text-[#0D6553]" />,
      tag: 'DIGITAL TWIN',
      title: 'Topological Airframe Twins',
      desc: 'Multi-layer system schematics with continuous health degradation projections and component wear drivers.',
      metric: '40 Monitored Airframes',
      path: '/aircraft',
    },
    {
      icon: <Cpu className="w-5 h-5 text-[#0D6553]" />,
      tag: 'ML EXPLAINABILITY',
      title: 'TreeExplainer Wear Attribution',
      desc: 'Quantile regression Remaining Useful Life (P10/P50/P90) with real-time SHAP feature attribution.',
      metric: '14-Day Advance Lead Time',
      path: '/components',
    },
    {
      icon: <Sliders className="w-5 h-5 text-[#0D6553]" />,
      tag: 'WHAT-IF ANALYSIS',
      title: 'Monte Carlo Stochastic Engine',
      desc: 'Simulate policy shifts (proactive vs run-to-failure, lead time spikes, surged flight hours) over 30 to 90 days.',
      metric: '100+ Stochastic Iterations',
      path: '/scenarios',
    },
    {
      icon: <Package className="w-5 h-5 text-[#0D6553]" />,
      tag: 'SUPPLY CHAIN',
      title: 'Lead Time vs RUL Intelligence',
      desc: 'Preempt supply stockouts by automatically cross-referencing supplier procurement lead time against predicted failure horizons.',
      metric: 'Zero Unplanned AOG',
      path: '/spares',
    },
    {
      icon: <Layers className="w-5 h-5 text-[#0D6553]" />,
      tag: 'MAINTENANCE',
      title: 'Depot Work Order Bundling',
      desc: 'Optimize hangar bay labor and reduce total turnaround downtime through opportunistic co-located inspections.',
      metric: '-32% Turnaround Loss',
      path: '/planning',
    },
  ];

  return (
    <div className="min-h-screen bg-[#FAFAFE] text-[#3B1D5E] font-sans selection:bg-[#1DE9C0]/30 selection:text-[#3B1D5E] relative overflow-x-hidden">
      {/* Subtle curved background line-art */}
      <div className="fixed inset-0 pointer-events-none z-0 opacity-40">
        <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#C9A2F5" stopOpacity="0.15" />
              <stop offset="100%" stopColor="#1DE9C0" stopOpacity="0.05" />
            </linearGradient>
          </defs>
          <path d="M-100,200 C300,50 600,350 1200,100 C1500,-50 1800,200 2100,50" fill="none" stroke="url(#grad1)" strokeWidth="1.5" />
          <path d="M-50,450 C400,250 800,600 1300,300 C1700,100 1900,450 2200,250" fill="none" stroke="url(#grad1)" strokeWidth="1" />
        </svg>
      </div>

      {/* 2. Minimal Top Navigation Bar */}
      <nav className="sticky top-0 z-50 w-full bg-white/85 backdrop-blur-md border-b border-[#E6E2F0] transition-all duration-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-18 flex items-center justify-between">
          {/* Logo */}
          <div
            onClick={() => navigate('/landing')}
            className="flex items-center space-x-3 cursor-pointer group select-none"
          >
            <div className="h-9 w-9 rounded-[10px] bg-[#E0F8FA] border border-[#1DE9C0]/50 flex items-center justify-center text-[#0D6553] shadow-sm transition-transform duration-200 group-hover:scale-105">
              <Activity className="w-5 h-5 text-[#0D6553]" />
            </div>
            <div>
              <div className="text-base font-bold tracking-tight text-[#3B1D5E] flex items-center gap-2">
                <span>AeroPulse</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#DCEFF8] text-[#0284C7] font-semibold">
                  INTELLIGENCE
                </span>
              </div>
              <div className="text-[11px] text-[#6B5B84] hidden md:block">
                Predictive Maintenance & Fleet Availability
              </div>
            </div>
          </div>

          {/* Centered Menu with Smooth Chevron & Dropdown Cards */}
          <div className="hidden lg:flex items-center space-x-1 text-xs">
            {navMenuItems.map((menu) => (
              <div
                key={menu.id}
                className="relative"
                onMouseEnter={() => setActiveDropdown(menu.id)}
                onMouseLeave={() => setActiveDropdown(null)}
              >
                <button className="px-4 py-2 text-[#6B5B84] hover:text-[#3B1D5E] font-medium transition-colors flex items-center gap-1.5 rounded-[10px] hover:bg-[#F4F2FB]">
                  <span>{menu.label}</span>
                  <ChevronDown className={`w-3.5 h-3.5 text-[#8F7FA8] transition-transform duration-200 ${activeDropdown === menu.id ? 'rotate-180 text-[#3B1D5E]' : ''}`} />
                </button>

                {/* Dropdown Card */}
                {activeDropdown === menu.id && (
                  <div className="absolute top-full left-0 w-80 pt-2 z-50">
                    <div className="bg-white border border-[#E6E2F0] rounded-[20px] p-3 shadow-ap-floating space-y-1">
                      {menu.items.map((item, idx) => (
                        <div
                          key={idx}
                          onClick={() => {
                            setActiveDropdown(null);
                            navigate(item.path);
                          }}
                          className="p-2.5 rounded-[12px] hover:bg-[#F4F2FB] border border-transparent hover:border-[#E6E2F0] transition cursor-pointer group/item flex items-start gap-3"
                        >
                          <div className="p-2 rounded-[10px] bg-[#E0F8FA] border border-[#1DE9C0]/30 shrink-0 mt-0.5">
                            {item.icon}
                          </div>
                          <div>
                            <div className="text-xs font-semibold text-[#3B1D5E] group-hover/item:text-[#0D6553] transition-colors">
                              {item.title}
                            </div>
                            <div className="text-[11px] text-[#6B5B84] leading-tight mt-0.5">
                              {item.desc}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}

            <button
              onClick={() => navigate('/scenarios')}
              className="px-4 py-2 text-[#6B5B84] hover:text-[#3B1D5E] font-medium transition-colors rounded-[10px] hover:bg-[#F4F2FB]"
            >
              Scenario Simulator
            </button>
          </div>

          {/* Right Action Controls */}
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setSearchOpen(true)}
              className="p-2.5 rounded-full bg-[#F4F2FB] border border-[#E6E2F0] text-[#6B5B84] hover:text-[#3B1D5E] hover:bg-white transition shadow-sm"
              title="Quick Search"
            >
              <Search className="w-4 h-4" />
            </button>

            <button
              onClick={() => navigate('/login')}
              className="hidden sm:inline-flex px-4 py-2 rounded-full border border-[#E6E2F0] bg-white hover:bg-[#F4F2FB] text-xs font-medium text-[#6B5B84] hover:text-[#3B1D5E] transition shadow-sm"
            >
              Sign In
            </button>

            <button
              onClick={() => navigate('/dashboard')}
              className="px-5 py-2.5 rounded-full bg-[#1DE9C0] hover:bg-[#15d1ac] text-[#1E1035] text-xs font-bold transition-all duration-200 shadow-ap-mint hover:shadow-lg flex items-center gap-2 transform hover:-translate-y-0.5"
            >
              <span>Get Started</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </nav>

      {/* 3. Split Hero Section */}
      <section className="relative z-10 pt-12 pb-20 lg:pt-20 lg:pb-28 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          {/* Left Hero Content */}
          <div className="lg:col-span-7 space-y-6 text-left">
            {/* Pill Tag */}
            <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-[#DCEFF8] border border-[#BAE6FD] text-[#0369A1] text-xs font-semibold">
              <span className="h-2 w-2 rounded-full bg-[#0284C7] animate-ping" />
              <span>AEROPULSE PLATFORM</span>
              <span className="text-[#94A3B8]">•</span>
              <span className="text-[#0369A1]">Fleet Readiness & Health Decision Support</span>
            </div>

            {/* Light-weight Heading */}
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-normal tracking-tight text-[#3B1D5E] leading-[1.15]">
              Predictive Fleet Availability <br />
              <span className="font-semibold text-[#1E1035]">
                & Subsystem Health
              </span>
            </h1>

            {/* One-line Subtitle */}
            <p className="text-base sm:text-lg text-[#6B5B84] max-w-xl leading-relaxed">
              Unify sensor telemetry, wear diagnostics, and maintenance planning to maximize airframe mission availability.
            </p>

            {/* Pale Cyan Info Tile */}
            <div className="p-5 rounded-[20px] bg-[#E0F8FA] border border-[#BAE6FD] shadow-sm space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="text-[#0369A1] font-bold uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4 text-[#0284C7]" />
                  Quantified Fleet Outcomes
                </span>
                <span className="text-[11px] text-[#0284C7]/80">Operational Decision Benchmarks</span>
              </div>

              <div className="grid grid-cols-3 gap-4 pt-1">
                <div>
                  <div className="text-2xl sm:text-3xl font-bold text-[#0D6553] font-mono">+8.4%</div>
                  <div className="text-[11px] text-[#0369A1] mt-0.5">Availability ($A_o$) Uplift</div>
                </div>
                <div>
                  <div className="text-2xl sm:text-3xl font-bold text-[#3B1D5E] font-mono">14 Days</div>
                  <div className="text-[11px] text-[#0369A1] mt-0.5">Mean Advance Warning</div>
                </div>
                <div>
                  <div className="text-2xl sm:text-3xl font-bold text-[#0284C7] font-mono">0 Days</div>
                  <div className="text-[11px] text-[#0369A1] mt-0.5">Unplanned Supply AOG</div>
                </div>
              </div>
            </div>

            {/* Action CTA Buttons */}
            <div className="flex flex-col sm:flex-row items-center gap-3.5 pt-2 text-xs">
              <button
                onClick={() => navigate('/dashboard')}
                className="w-full sm:w-auto px-7 py-3.5 rounded-[10px] bg-[#1DE9C0] hover:bg-[#15d1ac] text-[#1E1035] font-bold transition-all duration-200 shadow-ap-mint hover:shadow-lg flex items-center justify-center space-x-2"
              >
                <span>Enter Command Cockpit</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <button
                onClick={() => navigate('/scenarios')}
                className="w-full sm:w-auto px-6 py-3.5 rounded-[10px] bg-white hover:bg-[#F4F2FB] text-[#3B1D5E] border border-[#E6E2F0] font-semibold transition flex items-center justify-center space-x-2 shadow-sm"
              >
                <Sliders className="w-4 h-4 text-[#0D6553]" />
                <span>Run Scenario Simulator</span>
              </button>
            </div>
          </div>

          {/* Right Floating White Card */}
          <div className="lg:col-span-5 relative">
            <div className="relative bg-white border border-[#E6E2F0] rounded-[20px] p-7 shadow-ap-floating space-y-5 text-left">
              {/* Card Header */}
              <div className="space-y-1 border-b border-[#E6E2F0] pb-4">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-[#0D6553] font-bold uppercase tracking-wider flex items-center gap-1.5">
                    <Shield className="w-3.5 h-3.5" />
                    Interactive Cockpit Access
                  </span>
                  <span className="h-2 w-2 rounded-full bg-[#1DE9C0] animate-pulse" />
                </div>
                <h3 className="text-lg font-bold text-[#3B1D5E]">
                  Launch Workspace Instance
                </h3>
                <p className="text-xs text-[#6B5B84]">
                  Select your operational mission profile to spin up dedicated fleet telemetry views.
                </p>
              </div>

              {/* Form Content */}
              <form onSubmit={handleHeroSubmit} className="space-y-4 text-xs">
                {/* Role Switcher */}
                <div>
                  <label className="block text-[#6B5B84] text-[11px] uppercase mb-1.5 font-medium">
                    1. Select Role Profile
                  </label>
                  <div className="grid grid-cols-3 gap-1.5 p-1 bg-[#F4F2FB] border border-[#E6E2F0] rounded-[10px]">
                    <button
                      type="button"
                      onClick={() => setHeroRole('commander')}
                      className={`py-2 px-1 rounded-[8px] text-center font-bold transition text-[11px] ${
                        heroRole === 'commander'
                          ? 'bg-[#1DE9C0] text-[#1E1035] shadow-sm'
                          : 'text-[#6B5B84] hover:text-[#3B1D5E]'
                      }`}
                    >
                      Commander
                    </button>
                    <button
                      type="button"
                      onClick={() => setHeroRole('planner')}
                      className={`py-2 px-1 rounded-[8px] text-center font-bold transition text-[11px] ${
                        heroRole === 'planner'
                          ? 'bg-[#1DE9C0] text-[#1E1035] shadow-sm'
                          : 'text-[#6B5B84] hover:text-[#3B1D5E]'
                      }`}
                    >
                      Planner
                    </button>
                    <button
                      type="button"
                      onClick={() => setHeroRole('technician')}
                      className={`py-2 px-1 rounded-[8px] text-center font-bold transition text-[11px] ${
                        heroRole === 'technician'
                          ? 'bg-[#1DE9C0] text-[#1E1035] shadow-sm'
                          : 'text-[#6B5B84] hover:text-[#3B1D5E]'
                      }`}
                    >
                      Technician
                    </button>
                  </div>
                </div>

                {/* Fleet Size Dropdown */}
                <div>
                  <label className="block text-[#6B5B84] text-[11px] uppercase mb-1.5 font-medium">
                    2. Fleet Configuration
                  </label>
                  <select
                    value={heroFleetSize}
                    onChange={(e) => setHeroFleetSize(e.target.value)}
                    className="w-full bg-[#F4F2FB] border border-[#E6E2F0] rounded-[10px] px-3.5 py-2.5 text-[#3B1D5E] font-medium focus:outline-none focus:border-[#1DE9C0] transition cursor-pointer"
                  >
                    <option value="24 Airframes (Tactical)">24 Airframes (Tactical Wing)</option>
                    <option value="40 Airframes">40 Airframes (Full Fleet Benchmark)</option>
                    <option value="80 Airframes (Theater Scale)">80 Airframes (Theater Scale)</option>
                  </select>
                </div>

                {/* Email Call Sign */}
                <div>
                  <label className="block text-[#6B5B84] text-[11px] uppercase mb-1.5 font-medium">
                    3. Station Identifier
                  </label>
                  <input
                    type="text"
                    required
                    value={heroEmail}
                    onChange={(e) => setHeroEmail(e.target.value)}
                    placeholder="commander@aeropulse.defense.local"
                    className="w-full bg-[#F4F2FB] border border-[#E6E2F0] rounded-[10px] px-3.5 py-2.5 text-[#3B1D5E] placeholder-[#8F7FA8] focus:outline-none focus:border-[#1DE9C0] transition font-mono"
                  />
                </div>

                {/* Mint Button */}
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="w-full py-3 px-4 rounded-[10px] bg-[#1DE9C0] hover:bg-[#15d1ac] text-[#1E1035] font-bold text-xs transition-all duration-200 shadow-ap-mint flex items-center justify-center space-x-2 mt-2"
                >
                  <span>{formSubmitting ? 'Initializing Workspace...' : 'Enter Command Center'}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </form>

              {/* Security & Compliance Badges */}
              <div className="pt-2 border-t border-[#E6E2F0] flex items-center justify-between text-[11px] text-[#8F7FA8]">
                <span className="flex items-center gap-1 text-[#0D6553] font-medium">
                  <Lock className="w-3.5 h-3.5" />
                  Deterministic Local Engine
                </span>
                <span>Role-Based Access</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Connected Node Architecture */}
      <section className="relative z-10 py-16 bg-white border-y border-[#E6E2F0]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          {/* Section Header */}
          <div className="text-center space-y-3 max-w-3xl mx-auto">
            <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-[#E0F8FA] border border-[#BAE6FD] text-[#0369A1] text-[11px] font-semibold">
              <GitBranch className="w-3.5 h-3.5 text-[#0284C7]" />
              <span>CONTEXTUAL DECISION CHAIN</span>
            </div>
            <h2 className="text-3xl sm:text-4xl font-normal text-[#3B1D5E] tracking-tight">
              Connect Telemetry Signals to Fleet Decisions
            </h2>
            <p className="text-sm text-[#6B5B84]">
              AeroPulse establishes direct causal links between raw sensor telemetry, machine learning RUL estimates, spares inventory pipelines, and maintenance bay schedules.
            </p>
          </div>

          {/* Interactive Flow Tabs */}
          <div className="flex justify-center">
            <div className="inline-flex p-1 bg-[#F4F2FB] border border-[#E6E2F0] rounded-[12px] text-xs gap-1">
              <button
                onClick={() => setActiveTab('entity')}
                className={`px-4 py-2 rounded-[8px] font-bold transition flex items-center gap-1.5 ${
                  activeTab === 'entity'
                    ? 'bg-[#1DE9C0] text-[#1E1035] shadow-sm'
                    : 'text-[#6B5B84] hover:text-[#3B1D5E]'
                }`}
              >
                <GitBranch className="w-3.5 h-3.5" />
                <span>1. Causal Decision Chain</span>
              </button>
              <button
                onClick={() => setActiveTab('trajectory')}
                className={`px-4 py-2 rounded-[8px] font-bold transition flex items-center gap-1.5 ${
                  activeTab === 'trajectory'
                    ? 'bg-[#1DE9C0] text-[#1E1035] shadow-sm'
                    : 'text-[#6B5B84] hover:text-[#3B1D5E]'
                }`}
              >
                <TrendingUp className="w-3.5 h-3.5" />
                <span>2. Degradation Trajectory</span>
              </button>
              <button
                onClick={() => setActiveTab('spares')}
                className={`px-4 py-2 rounded-[8px] font-bold transition flex items-center gap-1.5 ${
                  activeTab === 'spares'
                    ? 'bg-[#1DE9C0] text-[#1E1035] shadow-sm'
                    : 'text-[#6B5B84] hover:text-[#3B1D5E]'
                }`}
              >
                <Package className="w-3.5 h-3.5" />
                <span>3. Spares Buffering</span>
              </button>
            </div>
          </div>

          {/* Connected Graph Display Card */}
          <div className="p-6 sm:p-8 rounded-[20px] bg-[#FAFAFE] border border-[#E6E2F0] shadow-sm relative overflow-hidden">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative z-10 text-xs">
              {/* Step 1 */}
              <div className="p-4 rounded-[16px] bg-white border border-[#E6E2F0] space-y-2.5 relative group hover:border-[#1DE9C0] shadow-sm transition">
                <div className="flex items-center justify-between text-[#0D6553]">
                  <span className="text-[10px] font-bold uppercase tracking-wider">Node 01: Sensor Stream</span>
                  <Activity className="w-4 h-4" />
                </div>
                <div className="text-sm font-bold text-[#3B1D5E]">Hydraulic Delta-P Spike</div>
                <p className="text-[11px] text-[#6B5B84] leading-relaxed">
                  Post-flight telemetry flags anomalous pressure oscillations on Airframe AC-017.
                </p>
                <div className="pt-2 border-t border-[#E6E2F0] text-[10px] text-[#0D6553] font-bold font-mono">
                  Anomaly Score: 0.89 (P95)
                </div>
              </div>

              {/* Step 2 */}
              <div className="p-4 rounded-[16px] bg-white border border-[#1DE9C0]/60 space-y-2.5 relative group shadow-sm">
                <div className="flex items-center justify-between text-[#0D6553]">
                  <span className="text-[10px] font-bold uppercase tracking-wider">Node 02: ML Inference</span>
                  <Cpu className="w-4 h-4" />
                </div>
                <div className="text-sm font-bold text-[#3B1D5E]">LightGBM Quantile RUL</div>
                <p className="text-[11px] text-[#6B5B84] leading-relaxed">
                  Predicts median failure in 14.2 days (P10 lower bound: 8.5 days) with SHAP attribution.
                </p>
                <div className="pt-2 border-t border-[#E6E2F0] text-[10px] text-[#0D6553] font-bold font-mono">
                  Target: AC017-HYD-PUMP
                </div>
              </div>

              {/* Step 3 */}
              <div className="p-4 rounded-[16px] bg-white border border-[#E6E2F0] space-y-2.5 relative group hover:border-[#1DE9C0] shadow-sm transition">
                <div className="flex items-center justify-between text-[#0D6553]">
                  <span className="text-[10px] font-bold uppercase tracking-wider">Node 03: Spares Check</span>
                  <Package className="w-4 h-4" />
                </div>
                <div className="text-sm font-bold text-[#3B1D5E]">Lead Time: 12 Days</div>
                <p className="text-[11px] text-[#6B5B84] leading-relaxed">
                  Supplier lead time matches RUL threshold. Automatic reorder buffer triggers to prevent AOG.
                </p>
                <div className="pt-2 border-t border-[#E6E2F0] text-[10px] text-[#0284C7] font-bold font-mono">
                  2 On-Hand • 1 Reserved
                </div>
              </div>

              {/* Step 4 */}
              <div className="p-4 rounded-[16px] bg-white border border-[#E6E2F0] space-y-2.5 relative group hover:border-[#1DE9C0] shadow-sm transition">
                <div className="flex items-center justify-between text-[#0D6553]">
                  <span className="text-[10px] font-bold uppercase tracking-wider">Node 04: Scheduled Bay</span>
                  <Layers className="w-4 h-4" />
                </div>
                <div className="text-sm font-bold text-[#3B1D5E]">Bundled Depot Slot</div>
                <p className="text-[11px] text-[#6B5B84] leading-relaxed">
                  Opportunistic bay reservation at Main Base Hangar 02 bundles routine B-check with pump replacement.
                </p>
                <div className="pt-2 border-t border-[#E6E2F0] text-[10px] text-[#0D6553] font-bold font-mono">
                  0 Aircraft-Days Lost
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 5. Core Platform Architecture Grid */}
      <section className="relative z-10 py-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        <div className="text-center space-y-3 max-w-3xl mx-auto">
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-[#E0F8FA] border border-[#BAE6FD] text-[#0369A1] text-[11px] font-semibold">
            <Server className="w-3.5 h-3.5 text-[#0284C7]" />
            <span>PLATFORM MODULES</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-normal text-[#3B1D5E] tracking-tight">
            Integrated Modules for Fleet Availability
          </h2>
          <p className="text-sm text-[#6B5B84]">
            Designed to meet the operational decision-support requirements of commanders, maintenance planners, and logistics officers.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {coreModules.map((item, idx) => (
            <div
              key={idx}
              onClick={() => navigate(item.path)}
              className="p-7 rounded-[20px] bg-white border border-[#E6E2F0] hover:border-[#1DE9C0] transition-all duration-200 shadow-ap-card hover:shadow-ap-floating cursor-pointer group flex flex-col justify-between"
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="p-3 rounded-[12px] bg-[#E0F8FA] border border-[#BAE6FD] text-[#0D6553]">
                    {item.icon}
                  </div>
                  <span className="text-[10px] px-2.5 py-1 rounded-full bg-[#F4F2FB] text-[#6B5B84] group-hover:text-[#3B1D5E] border border-[#E6E2F0] font-bold">
                    {item.tag}
                  </span>
                </div>

                <div className="space-y-1.5">
                  <h4 className="text-base font-bold text-[#3B1D5E] group-hover:text-[#0D6553] transition-colors">
                    {item.title}
                  </h4>
                  <p className="text-xs text-[#6B5B84] leading-relaxed">
                    {item.desc}
                  </p>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-[#E6E2F0] flex items-center justify-between text-xs font-mono">
                <span className="text-[#0D6553] font-bold">{item.metric}</span>
                <span className="text-[#8F7FA8] group-hover:text-[#3B1D5E] flex items-center gap-1 transition-colors">
                  Explore <ChevronRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 6. High-Conversion Bottom CTA Banner */}
      <section className="relative z-10 py-16 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="p-8 sm:p-14 rounded-[20px] bg-gradient-to-br from-[#E0F8FA] via-white to-[#F4F2FB] border border-[#BAE6FD] shadow-ap-card text-center space-y-6 relative overflow-hidden">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-white border border-[#BAE6FD] text-[#0369A1] text-xs font-bold shadow-sm">
            <Sparkles className="w-3.5 h-3.5 text-[#0284C7]" />
            <span>INSTANT 1-CLICK ACCESS</span>
          </div>

          <h2 className="text-3xl sm:text-4xl font-normal text-[#3B1D5E] tracking-tight max-w-2xl mx-auto">
            Ready to Transform Your Fleet Availability?
          </h2>

          <p className="text-sm sm:text-base text-[#6B5B84] max-w-xl mx-auto">
            Experience the complete integrated predictive maintenance engine, digital twins, and Monte Carlo scenario simulator.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2 text-xs">
            <button
              onClick={() => navigate('/dashboard')}
              className="w-full sm:w-auto px-8 py-4 rounded-[10px] bg-[#1DE9C0] hover:bg-[#15d1ac] text-[#1E1035] font-bold text-sm transition-all duration-200 shadow-ap-mint hover:shadow-lg flex items-center justify-center space-x-2"
            >
              <span>Enter Command Cockpit</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            <button
              onClick={() => navigate('/login')}
              className="w-full sm:w-auto px-6 py-4 rounded-[10px] bg-white hover:bg-[#F4F2FB] text-[#3B1D5E] border border-[#E6E2F0] font-semibold transition shadow-sm"
            >
              <span>Switch Profile</span>
            </button>
          </div>
        </div>
      </section>

      {/* 7. Minimal Clean Footer */}
      <footer className="w-full bg-white border-t border-[#E6E2F0] px-6 py-12 text-xs text-[#6B5B84]">
        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-8 mb-8 text-left">
          {/* Col 1 */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2 text-[#3B1D5E] font-bold text-sm">
              <Activity className="w-4 h-4 text-[#0D6553]" />
              <span>AEROPULSE FLEET INTELLIGENCE</span>
            </div>
            <p className="text-[11px] text-[#6B5B84] leading-relaxed">
              Integrated Predictive Maintenance, Digital Twin, and Fleet Availability Decision Support Platform.
            </p>
            <div className="text-[10px] text-[#0D6553] font-semibold flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> Platform Engine Active
            </div>
          </div>

          {/* Col 2 */}
          <div className="space-y-2">
            <div className="text-[#3B1D5E] font-bold text-xs uppercase tracking-wider">Core Platform</div>
            <ul className="space-y-1.5 text-[11px] text-[#6B5B84]">
              <li><button onClick={() => navigate('/dashboard')} className="hover:text-[#3B1D5E] transition">Fleet Cockpit</button></li>
              <li><button onClick={() => navigate('/aircraft')} className="hover:text-[#3B1D5E] transition">Airframe Digital Twin</button></li>
              <li><button onClick={() => navigate('/components')} className="hover:text-[#3B1D5E] transition">SHAP Diagnostics</button></li>
              <li><button onClick={() => navigate('/advisories')} className="hover:text-[#3B1D5E] transition">Predictive Queue</button></li>
            </ul>
          </div>

          {/* Col 3 */}
          <div className="space-y-2">
            <div className="text-[#3B1D5E] font-bold text-xs uppercase tracking-wider">Planning & Analysis</div>
            <ul className="space-y-1.5 text-[11px] text-[#6B5B84]">
              <li><button onClick={() => navigate('/planning')} className="hover:text-[#3B1D5E] transition">Depot Gantt Scheduler</button></li>
              <li><button onClick={() => navigate('/spares')} className="hover:text-[#3B1D5E] transition">Spares Lead Time Matrix</button></li>
              <li><button onClick={() => navigate('/scenarios')} className="hover:text-[#3B1D5E] transition">Monte Carlo Simulator</button></li>
            </ul>
          </div>

          {/* Col 4 */}
          <div className="space-y-2">
            <div className="text-[#3B1D5E] font-bold text-xs uppercase tracking-wider">Platform Architecture</div>
            <ul className="space-y-1.5 text-[11px] text-[#6B5B84]">
              <li>Role-Based Access Control (RBAC)</li>
              <li>Explainable AI Driver Tree</li>
              <li>Decision-Support Architecture</li>
              <li>PostgreSQL 16 Audit Ledger</li>
            </ul>
          </div>
        </div>

        <div className="max-w-7xl mx-auto pt-6 border-t border-[#E6E2F0] flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px]">
          <span>© 2026 AEROPULSE Platform • Integrated Fleet Availability.</span>
          <span>Decision-Support Intelligence for Maintenance & Availability.</span>
        </div>
      </footer>

      {/* Quick Search Modal */}
      {searchOpen && (
        <div className="fixed inset-0 bg-[#3B1D5E]/30 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white border border-[#E6E2F0] rounded-[20px] p-6 max-w-lg w-full shadow-ap-floating space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-[#0D6553] uppercase tracking-wider font-bold flex items-center gap-2">
                <Search className="w-4 h-4" />
                Quick Module Search
              </span>
              <button
                onClick={() => setSearchOpen(false)}
                className="text-xs text-[#8F7FA8] hover:text-[#3B1D5E]"
              >
                ESC
              </button>
            </div>
            <input
              type="text"
              autoFocus
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Type e.g. Cockpit, Spares, Simulator, Twin, AC-017..."
              className="w-full bg-[#F4F2FB] border border-[#E6E2F0] rounded-[10px] px-4 py-3 text-[#3B1D5E] text-xs focus:outline-none focus:border-[#1DE9C0] transition font-sans placeholder-[#8F7FA8]"
            />
            <div className="space-y-2 text-xs">
              <div className="text-[10px] text-[#8F7FA8] uppercase font-bold">Suggested Modules</div>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => {
                    setSearchOpen(false);
                    navigate('/dashboard');
                  }}
                  className="p-2.5 rounded-[10px] bg-[#F4F2FB] hover:bg-white text-left text-[#3B1D5E] font-medium border border-[#E6E2F0] hover:border-[#1DE9C0] transition"
                >
                  🚀 Fleet Dashboard
                </button>
                <button
                  onClick={() => {
                    setSearchOpen(false);
                    navigate('/scenarios');
                  }}
                  className="p-2.5 rounded-[10px] bg-[#F4F2FB] hover:bg-white text-left text-[#3B1D5E] font-medium border border-[#E6E2F0] hover:border-[#1DE9C0] transition"
                >
                  🎲 Scenario Simulator
                </button>
                <button
                  onClick={() => {
                    setSearchOpen(false);
                    navigate('/aircraft');
                  }}
                  className="p-2.5 rounded-[10px] bg-[#F4F2FB] hover:bg-white text-left text-[#3B1D5E] font-medium border border-[#E6E2F0] hover:border-[#1DE9C0] transition"
                >
                  ✈️ Airframe Twins
                </button>
                <button
                  onClick={() => {
                    setSearchOpen(false);
                    navigate('/spares');
                  }}
                  className="p-2.5 rounded-[10px] bg-[#F4F2FB] hover:bg-white text-left text-[#3B1D5E] font-medium border border-[#E6E2F0] hover:border-[#1DE9C0] transition"
                >
                  📦 Spares & Inventory
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
