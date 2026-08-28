import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import AuctionDetails from '../pages/AuctionDetails';
import * as api from '../services/api';

vi.mock('../services/api', () => ({
  getAuctionById: vi.fn(),
}));

describe('AuctionDetails Component', () => {
  const routerFuture = {
    v7_startTransition: true,
    v7_relativeSplatPath: true,
  };

  const mockAuctionDetail = {
    id: 'auc-101',
    rfq_id: 'rfq-101',
    rfq_title: 'Precision Aerospace Fasteners',
    rfq_description: 'High-grade titanium alloy fastener procurement batch',
    rfq_category: 'Aerospace',
    currency: 'USD',
    baseline_price: 100000,
    pickup_service_date: '2026-09-15T00:00:00Z',
    rfq_status: 'AUCTION_ACTIVE',
    bid_start_time: '2026-08-29T10:00:00Z',
    bid_close_time: '2026-08-29T12:05:00Z',
    forced_bid_close_time: '2026-08-29T14:00:00Z',
    trigger_window_minutes: 10,
    extension_duration_minutes: 5,
    extension_trigger: 'BID_RECEIVED',
    status: 'LIVE',
    display_status: 'Active',
    current_round: 1,
    lowest_bid: 82000,
    lowest_bidder_name: 'AeroFasten Supplies Inc',
    total_bids: 2,
    buyer: {
      id: 'buyer-001',
      name: 'Jane Doe',
      email: 'jane@aerocorp.com',
      company_name: 'AeroCorp Global',
    },
    items: [
      {
        id: 'item-001',
        rfq_id: 'rfq-101',
        name: 'Titanium Bolts M8',
        description: 'Grade 5 Ti-6Al-4V fasteners',
        quantity: 500,
        unit: 'pcs',
        created_at: '2026-08-29T09:00:00Z',
        updated_at: '2026-08-29T09:00:00Z',
      },
    ],
    bids: [
      {
        rank: 1,
        bid_id: 'bid-001',
        supplier_id: 'sup-001',
        supplier_name: 'AeroFasten Supplies Inc',
        supplier_company: 'AeroFasten Group',
        amount: 82000,
        carrier_name: 'DHL Express Freight',
        freight_charges: 1500,
        origin_charges: 300,
        destination_charges: 450,
        transit_time: '3 business days',
        validity_of_quote: '45 days',
        submitted_at: '2026-08-29T11:58:00Z',
        is_valid: true,
        rfq_item_id: null,
      },
      {
        rank: 2,
        bid_id: 'bid-002',
        supplier_id: 'sup-002',
        supplier_name: 'Skyline Logistics & Parts',
        supplier_company: 'Skyline Global',
        amount: 88500,
        carrier_name: 'FedEx Cargo',
        freight_charges: 1800,
        origin_charges: 250,
        destination_charges: 400,
        transit_time: '4 business days',
        validity_of_quote: '30 days',
        submitted_at: '2026-08-29T11:45:00Z',
        is_valid: true,
        rfq_item_id: null,
      },
    ],
    activity_logs: [
      {
        id: 'act-002',
        rfq_id: 'rfq-101',
        auction_id: 'auc-101',
        actor_type: 'SYSTEM',
        actor_id: null,
        event_type: 'AUCTION_EXTENDED',
        message: 'Auction automatically extended by 5m to 2026-08-29T12:05:00Z (Bid received inside 10-minute trigger window)',
        metadata_json: {
          trigger_mode: 'BID_RECEIVED',
          reason: 'Bid received inside 10-minute trigger window',
          extension_duration_minutes: 5,
        },
        created_at: '2026-08-29T11:58:00Z',
      },
      {
        id: 'act-001',
        rfq_id: 'rfq-101',
        auction_id: 'auc-101',
        actor_type: 'SUPPLIER',
        actor_id: 'sup-001',
        event_type: 'BID_SUBMITTED',
        message: "Bid of 82000.00 USD submitted by supplier 'AeroFasten Supplies Inc'",
        metadata_json: {
          amount: '82000.00',
          supplier_name: 'AeroFasten Supplies Inc',
        },
        created_at: '2026-08-29T11:58:00Z',
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders top metric cards, British Auction parameters, and rankings with quote breakdown', async () => {
    api.getAuctionById.mockResolvedValue(mockAuctionDetail);

    render(
      <MemoryRouter initialEntries={['/auctions/auc-101']} future={routerFuture}>
        <Routes>
          <Route path="/auctions/:id" element={<AuctionDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Precision Aerospace Fasteners' })).toBeInTheDocument();
    });

    // Check Metrics
    expect(screen.getByText('82000')).toBeInTheDocument();
    expect(screen.getByText(/Leading Supplier: AeroFasten Supplies Inc/i)).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();

    // Check Configuration Parameters
    expect(screen.getByText('10 Minutes')).toBeInTheDocument();
    expect(screen.getByText('+5 Minutes')).toBeInTheDocument();
    expect(screen.getByText('Bid Received in Last X Minutes')).toBeInTheDocument();

    // Check Supplier Bids Table with L1 and L2 Badges
    expect(screen.getByText('L1')).toBeInTheDocument();
    expect(screen.getByText('L2')).toBeInTheDocument();
    expect(screen.getByText('AeroFasten Supplies Inc')).toBeInTheDocument();
    expect(screen.getByText('Skyline Logistics & Parts')).toBeInTheDocument();

    // Check Quote Breakdown Details
    expect(screen.getByText('DHL Express Freight')).toBeInTheDocument();
    expect(screen.getByText('FedEx Cargo')).toBeInTheDocument();
    expect(screen.getByText('3 business days')).toBeInTheDocument();
    expect(screen.getByText('45 days')).toBeInTheDocument();
  });

  it('navigates to Activity Log tab and displays event timeline with extension reasons', async () => {
    api.getAuctionById.mockResolvedValue(mockAuctionDetail);

    render(
      <MemoryRouter initialEntries={['/auctions/auc-101']} future={routerFuture}>
        <Routes>
          <Route path="/auctions/:id" element={<AuctionDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Precision Aerospace Fasteners')).toBeInTheDocument();
    });

    // Click Activity Log tab
    const activityTab = screen.getByRole('button', { name: /Activity Log/i });
    fireEvent.click(activityTab);

    // Verify activity event items and extension reason
    expect(screen.getByText(/Auction automatically extended by 5m/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Bid received inside 10-minute trigger window/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Bid of 82000.00 USD submitted by supplier/i)).toBeInTheDocument();
  });

  it('navigates to RFQ Specs tab and displays item line specifications', async () => {
    api.getAuctionById.mockResolvedValue(mockAuctionDetail);

    render(
      <MemoryRouter initialEntries={['/auctions/auc-101']} future={routerFuture}>
        <Routes>
          <Route path="/auctions/:id" element={<AuctionDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Precision Aerospace Fasteners')).toBeInTheDocument();
    });

    // Click RFQ Specs tab
    const specsTab = screen.getByRole('button', { name: /RFQ Items & Specs/i });
    fireEvent.click(specsTab);

    expect(screen.getByText('Titanium Bolts M8')).toBeInTheDocument();
    expect(screen.getByText('Grade 5 Ti-6Al-4V fasteners')).toBeInTheDocument();
    expect(screen.getByText(/500 pcs/i)).toBeInTheDocument();
  });

  it('handles error state when auction lookup fails', async () => {
    api.getAuctionById.mockRejectedValue({
      response: { data: { detail: 'Auction with id not found' } },
    });

    render(
      <MemoryRouter initialEntries={['/auctions/non-existent']} future={routerFuture}>
        <Routes>
          <Route path="/auctions/:id" element={<AuctionDetails />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Auction with id not found')).toBeInTheDocument();
    });
  });
});
