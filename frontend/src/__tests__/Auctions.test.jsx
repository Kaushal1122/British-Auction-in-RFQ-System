import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Auctions from '../pages/Auctions';
import * as api from '../services/api';

vi.mock('../services/api', () => ({
  getAuctions: vi.fn(),
}));

describe('Auctions Listing Component', () => {
  const routerFuture = {
    v7_startTransition: true,
    v7_relativeSplatPath: true,
  };

  const mockAuctions = [
    {
      id: 'auc-001',
      rfq_id: 'rfq-001',
      rfq_title: 'Precision Metal CNC Milling Batch',
      currency: 'USD',
      baseline_price: 50000,
      lowest_bid: 42000,
      lowest_bidder_name: 'Apex Precision Metals',
      lowest_bidder_id: 'sup-001',
      bid_start_time: '2026-08-29T10:00:00Z',
      bid_close_time: '2026-08-29T12:00:00Z',
      forced_bid_close_time: '2026-08-29T14:00:00Z',
      trigger_window_minutes: 10,
      extension_duration_minutes: 5,
      extension_trigger: 'BID_RECEIVED',
      status: 'LIVE',
      display_status: 'Active',
      total_bids: 3,
      created_at: '2026-08-29T09:00:00Z',
      updated_at: '2026-08-29T11:55:00Z',
    },
    {
      id: 'auc-002',
      rfq_id: 'rfq-002',
      rfq_title: 'Server Rack Enclosure Supply',
      currency: 'USD',
      baseline_price: 25000,
      lowest_bid: null,
      lowest_bidder_name: null,
      lowest_bidder_id: null,
      bid_start_time: '2026-08-29T10:00:00Z',
      bid_close_time: '2026-08-29T11:00:00Z',
      forced_bid_close_time: '2026-08-29T12:00:00Z',
      trigger_window_minutes: 15,
      extension_duration_minutes: 10,
      extension_trigger: 'L1_RANK_CHANGE',
      status: 'CLOSED',
      display_status: 'Force Closed',
      total_bids: 0,
      created_at: '2026-08-29T08:00:00Z',
      updated_at: '2026-08-29T12:00:00Z',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state and then displays auction cards with real data', async () => {
    api.getAuctions.mockResolvedValue(mockAuctions);

    render(
      <MemoryRouter future={routerFuture}>
        <Auctions />
      </MemoryRouter>
    );

    expect(screen.getByText(/Loading British Auctions from database/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Precision Metal CNC Milling Batch')).toBeInTheDocument();
      expect(screen.getByText('Server Rack Enclosure Supply')).toBeInTheDocument();
    });

    // Check RFQ ID display
    expect(screen.getByText(/RFQ: rfq-001/i)).toBeInTheDocument();

    // Check Lowest Bid value and supplier
    expect(screen.getByText('42000')).toBeInTheDocument();
    expect(screen.getByText(/by Apex Precision Metals/i)).toBeInTheDocument();

    // Check Status Badges
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByText('Force Closed')).toBeInTheDocument();

    // Check configuration rules display
    expect(screen.getByText(/Window X = 10m, Duration Y = \+5m/i)).toBeInTheDocument();
  });

  it('filters auctions by search query', async () => {
    api.getAuctions.mockResolvedValue(mockAuctions);

    render(
      <MemoryRouter future={routerFuture}>
        <Auctions />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Precision Metal CNC Milling Batch')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Search by RFQ title or auction ID/i);
    fireEvent.change(searchInput, { target: { value: 'Server Rack' } });

    expect(screen.queryByText('Precision Metal CNC Milling Batch')).not.toBeInTheDocument();
    expect(screen.getByText('Server Rack Enclosure Supply')).toBeInTheDocument();
  });

  it('filters auctions by status badge', async () => {
    api.getAuctions.mockResolvedValue(mockAuctions);

    render(
      <MemoryRouter future={routerFuture}>
        <Auctions />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Precision Metal CNC Milling Batch')).toBeInTheDocument();
    });

    const forceClosedFilter = screen.getByRole('button', { name: /^Force Closed$/i });
    fireEvent.click(forceClosedFilter);

    expect(screen.queryByText('Precision Metal CNC Milling Batch')).not.toBeInTheDocument();
    expect(screen.getByText('Server Rack Enclosure Supply')).toBeInTheDocument();
  });

  it('renders empty state when no auctions exist', async () => {
    api.getAuctions.mockResolvedValue([]);

    render(
      <MemoryRouter future={routerFuture}>
        <Auctions />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/No Auctions Created Yet/i)).toBeInTheDocument();
    });

    expect(screen.getByRole('link', { name: /Create RFQ & Launch Auction/i })).toBeInTheDocument();
  });

  it('renders error alert when API call fails', async () => {
    api.getAuctions.mockRejectedValue({
      response: { data: { detail: 'Database connection failure' } },
    });

    render(
      <MemoryRouter future={routerFuture}>
        <Auctions />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Database connection failure')).toBeInTheDocument();
    });
  });
});
