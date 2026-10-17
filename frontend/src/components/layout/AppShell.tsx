import React, { useState } from 'react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  Activity,
  Plane,
  Cpu,
  AlertTriangle,
  CalendarDays,
  Package,
  Sliders,
  LogOut,
  Bell,
  CheckCircle2,
  X,
  Menu,
  ChevronLeft,
  ChevronRight,
  Shield,
  Zap,
} from 'lucide-react';
import { TimeReplayControl } from '../common/TimeReplayControl';
import { useAuth } from '../../hooks/useAuth';
import { useAlerts, useAckAlert } from '../../hooks/useEngineQueries';
import { useFleetSummary } from '../../hooks/useAvailabilityQueries';
import type { UserRole } from '../../types/api';

export const AppShell: React.FC = () => {
  const { user, role, logout, switchDemoRole, mockLogin, asOfDate, isMockMode } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [alertsOpen, setAlertsOpen] = useState(false);

  const { data: alertsData } = useAlerts({ acknowledged: false, page_size: 10 });
  const { data: summary } = useFleetSummary(asOfDate);
  const ackMutation = useAckAlert();

  const unackAlerts = alertsData?.items || [];
  const p1Count = summary?.open_p1 || 0;
  const p2Count = summary?.open_p2 || 0;

  const handleRoleChange = async (newRole: UserRole) => {
    try {
      await switchDemoRole(newRole);
    } catch {
      mockLogin(newRole);
    }
  };

  // Grouped Navigation Items
  const navGroups = [
    {
      label: 'OPERATIONS',
      items: [
        {
          to: '/dashboard',
          label: 'Fleet Dashboard',
          icon: <Activity className="w-4 h-4 shrink-0" />,
        },
        {
          to: '/aircraft',
          label: 'Aircraft & Twin',
          icon: <Plane className="w-4 h-4 shrink-0" />,
        },
        {
          to: '/components',
          label: 'Component Health',
          icon: <Cpu className="w-4 h-4 shrink-0" />,
        },
        {
          to: '/advisories',
          label: 'Predictive Queue',
          icon: <AlertTriangle className="w-4 h-4 shrink-0" />,
          badge: p1Count + p2Count > 0 ? `${p1Count + p2Count}` : undefined,
          badgeColor: p1Count > 0 ? 'bg-[#FEF2F2] text-[#DC2626] border border-[#FCA5A5]' : 'bg-[#E6FCF7] text-[#0D6553] border border-[#1DE9C0]/50 font-bold',
        },
      ],
    },
    {
      label: 'MAINTENANCE',
      items: [
        {
          to: '/planning',
          label: 'Planning & Orders',
          icon: <CalendarDays className="w-4 h-4 shrink-0" />,
        },
        {
          to: '/spares',
          label: 'Spares Inventory',
          icon: <Package className="w-4 h-4 shrink-0" />,
        },
      ],
    },
    {
      label: 'ANALYSIS',
      items: [
        {
          to: '/scenarios',
          label: 'Scenario Simulator',
          icon: <Sliders className="w-4 h-4 shrink-0" />,
        },
      ],
    },
  ];

  // Derive page title from active path
  const getPageTitle = () => {
    const p = location.pathname;
    if (p.includes('/dashboard')) return 'Fleet Operational Cockpit';
    if (p.includes('/aircraft')) return 'Aircraft Detail & Digital Twin';
    if (p.includes('/components')) return 'Component Health & Telemetry';
    if (p.includes('/advisories')) return 'Predictive Maintenance Queue';
    if (p.includes('/planning')) return 'Maintenance Planning & Turnaround';
    if (p.includes('/spares')) return 'Spares & Lead Time Intelligence';
    if (p.includes('/scenarios')) return 'Scenario Simulator (What-If)';
    return 'Fleet Platform';
  };

  return (
    <div className="min-h-screen bg-[#FAFAFE] text-[#3B1D5E] flex flex-col font-sans selection:bg-[#1DE9C0]/30 selection:text-[#3B1D5E]">
      {/* Top Header Navigation Bar */}
      <header className="w-full bg-white/90 border-b border-[#E6E2F0] px-4 py-2.5 flex items-center justify-between sticky top-0 z-40 backdrop-blur-md">
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-1.5 rounded-[10px] border border-[#E6E2F0] bg-[#F4F2FB] text-[#6B5B84] hover:text-[#3B1D5E] hover:bg-white"
          >
            <Menu className="w-5 h-5" />
          </button>

          {/* Logo & Title */}
          <div
            onClick={() => navigate('/dashboard')}
            className="flex items-center space-x-2.5 cursor-pointer select-none group"
          >
            <div className="h-8 w-8 rounded-[10px] bg-[#E0F8FA] border border-[#1DE9C0]/50 flex items-center justify-center text-[#0D6553] font-bold shadow-sm group-hover:scale-105 transition-transform">
              <Activity className="w-4 h-4 text-[#0D6553]" />
            </div>
            <div>
              <div className="text-sm font-bold tracking-tight text-[#3B1D5E] flex items-center gap-1.5">
                <span>AeroPulse</span>
              </div>
              <div className="text-[11px] text-[#6B5B84] hidden sm:block font-normal">
                {getPageTitle()}
              </div>
            </div>
          </div>
        </div>

        {/* Global Controls: Time-Replay Bar & Alert Bell & Role Switcher */}
        <div className="flex items-center space-x-2 sm:space-x-3 text-xs">
          <TimeReplayControl />

          {/* Active Alerts Bell */}
          <div className="relative">
            <button
              onClick={() => setAlertsOpen(!alertsOpen)}
              className="p-2 rounded-[10px] border border-[#E6E2F0] bg-[#F4F2FB] hover:bg-white text-[#6B5B84] hover:text-[#3B1D5E] relative transition shadow-sm"
              title="Active platform alerts"
            >
              <Bell className="w-4 h-4" />
              {unackAlerts.length > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-[#EF4444] text-white text-[9px] flex items-center justify-center font-bold animate-pulse">
                  {unackAlerts.length}
                </span>
              )}
            </button>

            {/* Alerts Dropdown Modal */}
            {alertsOpen && (
              <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white border border-[#E6E2F0] rounded-[20px] shadow-ap-floating p-4 z-50">
                <div className="flex items-center justify-between pb-2 border-b border-[#E6E2F0]">
                  <span className="font-semibold text-xs text-[#3B1D5E]">
                    Active Operational Alerts ({unackAlerts.length})
                  </span>
                  <button onClick={() => setAlertsOpen(false)} className="text-[#8F7FA8] hover:text-[#3B1D5E]">
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <div className="mt-2 space-y-2 max-h-72 overflow-y-auto pr-1">
                  {unackAlerts.length === 0 ? (
                    <div className="text-center py-5 text-xs text-[#8F7FA8]">No active alerts pending.</div>
                  ) : (
                    unackAlerts.map((a) => (
                      <div
                        key={a.alert_id}
                        className="p-2.5 rounded-[12px] bg-[#F4F2FB] border border-[#E6E2F0] text-xs space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <span
                            className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                              a.severity === 'critical'
                                ? 'bg-[#FEF2F2] text-[#DC2626] border border-[#FCA5A5]'
                                : 'bg-[#FFFBEB] text-[#D97706] border border-[#FDE68A]'
                            }`}
                          >
                            {a.severity} • {a.type}
                          </span>
                          <button
                            onClick={() => ackMutation.mutate({ id: a.alert_id, ack: true })}
                            className="text-[10px] text-[#0D6553] hover:underline font-semibold flex items-center gap-0.5"
                          >
                            <CheckCircle2 className="w-3 h-3" /> Ack
                          </button>
                        </div>
                        <p className="text-[#3B1D5E] text-[11px] leading-snug">{a.message}</p>
                        <div className="text-[10px] text-[#8F7FA8] font-mono">{new Date(a.created_at).toLocaleString()}</div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Role Switcher & User Profile */}
          <div className="flex items-center space-x-2 pl-2 border-l border-[#E6E2F0]">
            {isMockMode && (
              <span
                className="hidden sm:inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#EDE9FE] text-[#6D28D9] border border-[#DDD6FE]"
                title="Running in offline mock mode (backend bypassed)"
              >
                <Zap className="w-3 h-3 text-[#7C3AED]" /> Mock Bypass
              </span>
            )}
            <span className="hidden md:inline text-[11px] text-[#6B5B84]">Role:</span>
            <select
              value={role || 'commander'}
              onChange={(e) => handleRoleChange(e.target.value as UserRole)}
              className="bg-[#F4F2FB] border border-[#E6E2F0] text-[#3B1D5E] font-semibold text-xs rounded-[10px] px-2.5 py-1.5 focus:outline-none focus:border-[#1DE9C0] cursor-pointer shadow-sm capitalize"
            >
              <option value="commander">Commander</option>
              <option value="planner">Planner</option>
              <option value="technician">Technician</option>
            </select>

            <button
              onClick={logout}
              className="p-2 text-[#6B5B84] hover:text-[#DC2626] hover:bg-[#F4F2FB] rounded-[10px] transition"
              title={`Sign out (${user?.username || 'demo'})`}
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Workspace Layout: Sidebar + Page Outlet */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
        {/* Sidebar Navigation */}
        <aside
          className={`${
            sidebarCollapsed ? 'md:w-16' : 'md:w-60'
          } w-full bg-white border-r border-[#E6E2F0] flex flex-col justify-between py-4 px-3 flex-shrink-0 transition-all duration-200 z-30 ${
            mobileMenuOpen ? 'block' : 'hidden md:flex'
          }`}
        >
          <div className="space-y-4">
            {/* Collapse Toggle (Desktop) */}
            <div className="hidden md:flex items-center justify-between px-2 pb-1">
              {!sidebarCollapsed && (
                <span className="text-[10px] uppercase tracking-wider text-[#8F7FA8] font-bold">
                  Fleet Modules
                </span>
              )}
              <button
                onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                className="p-1 rounded-[6px] text-[#8F7FA8] hover:text-[#3B1D5E] hover:bg-[#F4F2FB] ml-auto transition"
                title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              >
                {sidebarCollapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5" />}
              </button>
            </div>

            {/* Navigation Groups */}
            <div className="space-y-3">
              {navGroups.map((grp) => (
                <div key={grp.label} className="space-y-1">
                  {!sidebarCollapsed && (
                    <div className="px-2.5 py-1 text-[9px] uppercase tracking-wider text-[#8F7FA8] font-bold">
                      {grp.label}
                    </div>
                  )}
                  {grp.items.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      onClick={() => setMobileMenuOpen(false)}
                      title={sidebarCollapsed ? item.label : undefined}
                      className={({ isActive }) =>
                        `flex items-center justify-between px-2.5 py-2 rounded-[10px] text-xs font-medium transition-all ${
                          isActive
                            ? 'bg-[#E6FCF7] text-[#0D6553] font-semibold border border-[#1DE9C0]/50 shadow-sm'
                            : 'text-[#6B5B84] hover:bg-[#F4F2FB] hover:text-[#3B1D5E] border border-transparent'
                        }`
                      }
                    >
                      <div className="flex items-center space-x-2.5 min-w-0">
                        <span className="shrink-0">{item.icon}</span>
                        {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
                      </div>
                      {!sidebarCollapsed && item.badge && (
                        <span
                          className={`text-[10px] font-bold px-1.5 py-0.2 rounded-full shrink-0 ${
                            item.badgeColor || 'bg-[#1DE9C0] text-[#1E1035]'
                          }`}
                        >
                          {item.badge}
                        </span>
                      )}
                    </NavLink>
                  ))}
                </div>
              ))}
            </div>
          </div>

          {/* Sidebar Footer Info */}
          {!sidebarCollapsed ? (
            <div className="pt-3 border-t border-[#E6E2F0] px-2 text-[11px] text-[#6B5B84] space-y-1.5">
              <div className="flex justify-between">
                <span>Fleet Airframes:</span>
                <span className="text-[#3B1D5E] font-mono font-bold">{summary?.total_aircraft ?? 40}</span>
              </div>
              <div className="flex justify-between">
                <span>Serviceable:</span>
                <span className="text-[#059669] font-mono font-bold">{summary?.serviceable_count ?? '—'}</span>
              </div>
              <div className="text-[10px] text-[#8F7FA8] pt-1">AeroPulse Operational Engine</div>
            </div>
          ) : (
            <div className="pt-3 border-t border-[#E6E2F0] text-center">
              <Shield className="w-4 h-4 text-[#0D6553] mx-auto" />
            </div>
          )}
        </aside>

        {/* Content Outlet */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-8 bg-[#FAFAFE]">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
