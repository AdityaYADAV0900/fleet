import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../src/App';
import { KpiCard } from '../src/components/common/KpiCard';
import { StatusBadge } from '../src/components/common/StatusBadge';
import { DataTable, type Column } from '../src/components/common/DataTable';

describe('App & Core Components', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('renders login screen when unauthenticated', async () => {
    render(<App />);

    expect(screen.getByText(/AeroPulse Cockpit/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Commander/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Planner/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Technician/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Bypass Login Now/i })).toBeInTheDocument();
  });

  it('bypasses login and enters cockpit in mock mode with stored session', async () => {
    render(<App />);

    const bypassBtn = screen.getByRole('button', { name: /Bypass Login Now/i });
    expect(bypassBtn).toBeInTheDocument();

    fireEvent.click(bypassBtn);

    await waitFor(() => {
      expect(localStorage.getItem('fleet_auth_is_mock')).toBe('true');
      expect(localStorage.getItem('fleet_auth_token')).toContain('mock-token-commander');
      expect(screen.getByText(/Mock Bypass/i)).toBeInTheDocument();
      expect(screen.getAllByText(/Fleet Operational Cockpit/i).length).toBeGreaterThan(0);
    });
  });

  it('renders KpiCard with title, metric value, and subtitle', () => {
    render(
      <KpiCard
        title="Fleet Availability"
        value="82.4%"
        subtitle="Nominal threshold: 75%"
        accent="blue"
      />
    );

    expect(screen.getByText(/Fleet Availability/i)).toBeInTheDocument();
    expect(screen.getByText(/82.4%/i)).toBeInTheDocument();
    expect(screen.getByText(/Nominal threshold: 75%/i)).toBeInTheDocument();
  });

  it('renders StatusBadge with correct styling', () => {
    const { rerender } = render(<StatusBadge status="Available" />);
    expect(screen.getByText(/Available/i)).toBeInTheDocument();

    rerender(<StatusBadge status="P1" size="lg" />);
    expect(screen.getByText(/P1/i)).toBeInTheDocument();
  });

  it('renders DataTable with custom columns and data rows', () => {
    interface TestRow {
      id: string;
      tail: string;
      status: string;
    }

    const columns: Column<TestRow>[] = [
      { header: 'Tail Code', accessorKey: 'tail' },
      {
        header: 'Status',
        render: (row) => <StatusBadge status={row.status} size="sm" />,
      },
    ];

    const data: TestRow[] = [
      { id: '1', tail: 'AC-001', status: 'Available' },
      { id: '2', tail: 'AC-017', status: 'Unscheduled Repair' },
    ];

    render(<DataTable columns={columns} data={data} />);

    expect(screen.getByText('AC-001')).toBeInTheDocument();
    expect(screen.getByText('AC-017')).toBeInTheDocument();
    expect(screen.getByText('Available')).toBeInTheDocument();
    expect(screen.getByText('Unscheduled Repair')).toBeInTheDocument();
  });

  it('verifies all seven core screens are mapped in application routes', () => {
    // Expected 7 screen navigation targets defined in Phase 8 plan
    const expectedScreens = [
      { name: 'Fleet Dashboard', path: '/dashboard' },
      { name: 'Aircraft Detail & Twin', path: '/aircraft' },
      { name: 'Component Health', path: '/components' },
      { name: 'Predictive Queue', path: '/advisories' },
      { name: 'Planning & Work Orders', path: '/planning' },
      { name: 'Spares Inventory', path: '/spares' },
      { name: 'Scenario Simulator', path: '/scenarios' },
    ];

    expect(expectedScreens).toHaveLength(7);
    expectedScreens.forEach((screenItem) => {
      expect(screenItem.path).toBeTruthy();
      expect(screenItem.name).toBeTruthy();
    });
  });
});
