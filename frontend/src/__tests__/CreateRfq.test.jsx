import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import CreateRfq from '../pages/CreateRfq';
import * as api from '../services/api';

// Mock the API services
vi.mock('../services/api', () => ({
  createBuyer: vi.fn(),
  getBuyerById: vi.fn(),
  getBuyers: vi.fn(),
  listBuyers: vi.fn(),
  createRFQ: vi.fn(),
  checkHealth: vi.fn(),
}));

// Helper function to fill buyer, RFQ details, and items
const fillValidRfqBasics = async (buyerName = 'John Doe', buyerEmail = 'john@example.com') => {
  // Wait for buyers fetch to settle if any
  await waitFor(() => {
    expect(screen.queryByText(/Loading buyers\.\.\./i)).not.toBeInTheDocument();
  });

  // Select or create buyer
  const createBtn = screen.getByRole('button', { name: /Create Buyer|Create New Buyer/i });
  fireEvent.click(createBtn);
  const modal = await screen.findByRole('dialog');
  fireEvent.change(within(modal).getByLabelText(/Full Name/i), { target: { value: buyerName } });
  fireEvent.change(within(modal).getByLabelText(/Email Address/i), { target: { value: buyerEmail } });
  fireEvent.click(within(modal).getByRole('button', { name: /Create Buyer/i }));

  await waitFor(() => {
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  // Basic RFQ info
  fireEvent.change(screen.getByLabelText(/RFQ Title/i), { target: { value: 'Industrial Component Procurement' } });
  fireEvent.change(screen.getByLabelText(/Baseline Price/i), { target: { value: '50000' } });

  // Item 1
  const nameInputs = screen.getAllByPlaceholderText(/e\.g\. Steel Bearing/i);
  const qtyInputs = screen.getAllByPlaceholderText(/e\.g\. 100/i);
  fireEvent.change(nameInputs[0], { target: { value: 'Steel Bearing' } });
  fireEvent.change(qtyInputs[0], { target: { value: '100' } });
};

// Helper function to fill valid auction schedule & British auction configuration
const fillValidAuctionSchedule = (
  startTime = '2026-09-01T10:00',
  closeTime = '2026-09-01T11:00',
  forcedCloseTime = '2026-09-01T11:30'
) => {
  fireEvent.change(screen.getByLabelText(/^Bid Start Date & Time/i), { target: { value: startTime } });
  fireEvent.change(screen.getByLabelText(/^Bid Close Date & Time/i), { target: { value: closeTime } });
  fireEvent.change(screen.getByLabelText(/^Forced Bid Close Date & Time/i), { target: { value: forcedCloseTime } });
};

describe('Create RFQ Page & Auction Configuration (Step 8 Pre-Requisite)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getBuyers.mockResolvedValue([]);
    api.createBuyer.mockResolvedValue({
      id: 'buyer-uuid-1',
      name: 'John Doe',
      email: 'john@example.com',
      company_name: 'ABC Corp',
    });
  });


  // Test 1: Auction Schedule section renders
  it('Test 1: renders Auction Schedule section', async () => {
    render(<CreateRfq />);
    expect(await screen.findByText(/3\. Auction Schedule/i)).toBeInTheDocument();
    expect(screen.getByText(/When bidding opens for participating suppliers\./i)).toBeInTheDocument();
  });

  // Test 2: Bid Start Date & Time field renders
  it('Test 2: renders Bid Start Date & Time field', async () => {
    render(<CreateRfq />);
    const input = await screen.findByLabelText(/^Bid Start Date & Time/i);
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute('type', 'datetime-local');
  });

  // Test 3: Bid Close Date & Time field renders
  it('Test 3: renders Bid Close Date & Time field', async () => {
    render(<CreateRfq />);
    const input = await screen.findByLabelText(/^Bid Close Date & Time/i);
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute('type', 'datetime-local');
  });

  // Test 4: Forced Bid Close Date & Time field renders
  it('Test 4: renders Forced Bid Close Date & Time field', async () => {
    render(<CreateRfq />);
    const input = await screen.findByLabelText(/^Forced Bid Close Date & Time/i);
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute('type', 'datetime-local');
  });

  // Test 5: Pickup / Service Date field renders
  it('Test 5: renders Pickup / Service Date field', async () => {
    render(<CreateRfq />);
    const input = await screen.findByLabelText(/Pickup \/ Service Date/i);
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute('type', 'datetime-local');
  });

  // Test 6: Trigger Window field renders
  it('Test 6: renders Trigger Window field with default 10', async () => {
    render(<CreateRfq />);
    const input = await screen.findByLabelText(/Trigger Window \(X Minutes\)/i);
    expect(input).toBeInTheDocument();
    expect(input).toHaveValue(10);
  });

  // Test 7: Extension Duration field renders
  it('Test 7: renders Extension Duration field with default 5', async () => {
    render(<CreateRfq />);
    const input = await screen.findByLabelText(/Extension Duration \(Y Minutes\)/i);
    expect(input).toBeInTheDocument();
    expect(input).toHaveValue(5);
  });

  // Test 8: Extension Trigger dropdown renders
  it('Test 8: renders Extension Trigger dropdown with all assignment options', async () => {
    render(<CreateRfq />);
    const select = await screen.findByLabelText(/Extension Trigger/i);
    expect(select).toBeInTheDocument();
    expect(select).toHaveValue('BID_RECEIVED');

    expect(screen.getByRole('option', { name: /Bid Received in Last X Minutes/i })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /Any Supplier Rank Change in Last X Minutes/i })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /Lowest Bidder \(L1\) Rank Change in Last X Minutes/i })).toBeInTheDocument();
  });


  // Test 9: Forced close before bid close is rejected
  it('Test 9: rejects forced close before bid close with exact error message', async () => {
    render(<CreateRfq />);
    await fillValidRfqBasics();
    fillValidAuctionSchedule('2026-09-01T10:00', '2026-09-01T18:00', '2026-09-01T17:30');

    fireEvent.click(screen.getByRole('button', { name: /Create RFQ/i }));

    expect(screen.getByText(/Forced close time must be later than bid close time\./i)).toBeInTheDocument();
    expect(api.createRFQ).not.toHaveBeenCalled();
  });

  // Test 10: Forced close equal to bid close is rejected
  it('Test 10: rejects forced close equal to bid close', async () => {
    render(<CreateRfq />);
    await fillValidRfqBasics();
    fillValidAuctionSchedule('2026-09-01T10:00', '2026-09-01T18:00', '2026-09-01T18:00');

    fireEvent.click(screen.getByRole('button', { name: /Create RFQ/i }));

    expect(screen.getByText(/Forced close time must be later than bid close time\./i)).toBeInTheDocument();
    expect(api.createRFQ).not.toHaveBeenCalled();
  });

  // Test 10b: Start time equal to close time is rejected
  it('Test 10b: rejects start time equal to bid close time', async () => {
    render(<CreateRfq />);
    await fillValidRfqBasics();
    fillValidAuctionSchedule('2026-09-01T10:00', '2026-09-01T10:00', '2026-09-01T11:00');

    fireEvent.click(screen.getByRole('button', { name: /Create RFQ/i }));

    expect(screen.getByText(/Bid close time must be later than bid start time\./i)).toBeInTheDocument();
    expect(api.createRFQ).not.toHaveBeenCalled();
  });

  // Test 10c: Start time later than close time is rejected
  it('Test 10c: rejects start time later than bid close time', async () => {
    render(<CreateRfq />);
    await fillValidRfqBasics();
    fillValidAuctionSchedule('2026-09-01T12:00', '2026-09-01T10:00', '2026-09-01T13:00');

    fireEvent.click(screen.getByRole('button', { name: /Create RFQ/i }));

    expect(screen.getByText(/Bid close time must be later than bid start time\./i)).toBeInTheDocument();
    expect(api.createRFQ).not.toHaveBeenCalled();
  });

  // Test 10d: Missing required schedule fields are rejected
  it('Test 10d: rejects missing required schedule fields', async () => {
    render(<CreateRfq />);
    await fillValidRfqBasics();
    // Do not fill schedule

    fireEvent.click(screen.getByRole('button', { name: /Create RFQ/i }));

    expect(screen.getByText(/^Bid start date & time is required\./i)).toBeInTheDocument();
    expect(screen.getByText(/^Bid close date & time is required\./i)).toBeInTheDocument();
    expect(screen.getByText(/^Forced bid close date & time is required\./i)).toBeInTheDocument();
    expect(api.createRFQ).not.toHaveBeenCalled();
  });

  // Test 10e: Dynamic validation updates live when editing without page refresh
  it('Test 10e: dynamic validation updates immediately when changing forced close time and clears when corrected', async () => {
    render(<CreateRfq />);
    await fillValidRfqBasics();
    fillValidAuctionSchedule('2026-09-01T10:00', '2026-09-01T11:00', '2026-09-01T11:30');

    // Currently valid, no forced close error
    expect(screen.queryByText(/Forced close time must be later than bid close time\./i)).not.toBeInTheDocument();

    // User changes forced close to 10:30 (earlier than close 11:00)
    fireEvent.change(screen.getByLabelText(/^Forced Bid Close Date & Time/i), {
      target: { value: '2026-09-01T10:30' },
    });

    // Error immediately appears without form submit
    expect(screen.getByText(/Forced close time must be later than bid close time\./i)).toBeInTheDocument();

    // User changes it back to valid 11:30
    fireEvent.change(screen.getByLabelText(/^Forced Bid Close Date & Time/i), {
      target: { value: '2026-09-01T11:30' },
    });

    // Error immediately disappears
    expect(screen.queryByText(/Forced close time must be later than bid close time\./i)).not.toBeInTheDocument();
  });

  // Test 11: Valid chronological auction times are accepted
  it('Test 11: accepts valid chronological auction times', async () => {
    api.createRFQ.mockResolvedValueOnce({
      id: 'rfq-uuid-1',
      title: 'Industrial Component Procurement',
      baseline_price: 50000,
      currency: 'USD',
      status: 'DRAFT',
      trigger_window_minutes: 10,
      extension_duration_minutes: 5,
      extension_trigger: 'BID_RECEIVED',
      items: [{ name: 'Steel Bearing', quantity: 100, unit: 'units' }],
    });

    render(<CreateRfq />);
    await fillValidRfqBasics();
    fillValidAuctionSchedule('2026-09-01T10:00', '2026-09-01T11:00', '2026-09-01T11:30');

    fireEvent.click(screen.getByRole('button', { name: /Create RFQ/i }));

    await waitFor(() => {
      expect(api.createRFQ).toHaveBeenCalledTimes(1);
      expect(screen.getByText(/RFQ created successfully\./i)).toBeInTheDocument();
    });
  });

  // Test 12: Negative trigger window is rejected
  it('Test 12: rejects negative trigger window', async () => {
    render(<CreateRfq />);
    await fillValidRfqBasics();
    fillValidAuctionSchedule();

    fireEvent.change(screen.getByLabelText(/Trigger Window \(X Minutes\)/i), { target: { value: '-5' } });
    fireEvent.click(screen.getByRole('button', { name: /Create RFQ/i }));

    expect(screen.getByText(/Trigger window must be greater than 0 minutes\./i)).toBeInTheDocument();
    expect(api.createRFQ).not.toHaveBeenCalled();
  });

  // Test 13: Invalid/Zero trigger window is rejected
  it('Test 13: rejects zero or non-numeric trigger window', async () => {
    render(<CreateRfq />);
    await fillValidRfqBasics();
    fillValidAuctionSchedule();

    fireEvent.change(screen.getByLabelText(/Trigger Window \(X Minutes\)/i), { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: /Create RFQ/i }));

    expect(screen.getByText(/Trigger window must be greater than 0 minutes\./i)).toBeInTheDocument();
    expect(api.createRFQ).not.toHaveBeenCalled();
  });

  // Test 14: Negative extension duration is rejected
  it('Test 14: rejects negative extension duration', async () => {
    render(<CreateRfq />);
    await fillValidRfqBasics();
    fillValidAuctionSchedule();

    fireEvent.change(screen.getByLabelText(/Extension Duration \(Y Minutes\)/i), { target: { value: '-2' } });
    fireEvent.click(screen.getByRole('button', { name: /Create RFQ/i }));

    expect(screen.getByText(/Extension duration must be greater than 0 minutes\./i)).toBeInTheDocument();
    expect(api.createRFQ).not.toHaveBeenCalled();
  });

  // Test 15: Invalid/Zero extension duration is rejected
  it('Test 15: rejects zero or non-numeric extension duration', async () => {
    render(<CreateRfq />);
    await fillValidRfqBasics();
    fillValidAuctionSchedule();

    fireEvent.change(screen.getByLabelText(/Extension Duration \(Y Minutes\)/i), { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: /Create RFQ/i }));

    expect(screen.getByText(/Extension duration must be greater than 0 minutes\./i)).toBeInTheDocument();
    expect(api.createRFQ).not.toHaveBeenCalled();
  });

  // Test 16: Each extension trigger option can be selected
  it('Test 16: allows selecting each extension trigger option', async () => {
    render(<CreateRfq />);
    const select = await screen.findByLabelText(/Extension Trigger/i);

    fireEvent.change(select, { target: { value: 'ANY_RANK_CHANGE' } });
    expect(select).toHaveValue('ANY_RANK_CHANGE');

    fireEvent.change(select, { target: { value: 'L1_RANK_CHANGE' } });
    expect(select).toHaveValue('L1_RANK_CHANGE');

    fireEvent.change(select, { target: { value: 'BID_RECEIVED' } });
    expect(select).toHaveValue('BID_RECEIVED');
  });

  // Test 17: Auction configuration is included in RFQ API request
  it('Test 17: includes auction timing and configuration in the API payload', async () => {
    api.createRFQ.mockResolvedValueOnce({ id: 'rfq-1', title: 'Test RFQ', items: [] });

    render(<CreateRfq />);
    await fillValidRfqBasics();
    fillValidAuctionSchedule('2026-09-01T10:00', '2026-09-01T11:00', '2026-09-01T11:30');
    fireEvent.change(screen.getByLabelText(/Pickup \/ Service Date/i), { target: { value: '2026-09-15T09:00' } });
    fireEvent.change(screen.getByLabelText(/Trigger Window \(X Minutes\)/i), { target: { value: '15' } });
    fireEvent.change(screen.getByLabelText(/Extension Duration \(Y Minutes\)/i), { target: { value: '8' } });
    fireEvent.change(screen.getByLabelText(/Extension Trigger/i), { target: { value: 'ANY_RANK_CHANGE' } });

    fireEvent.click(screen.getByRole('button', { name: /Create RFQ/i }));

    await waitFor(() => {
      expect(api.createRFQ).toHaveBeenCalledWith(
        expect.objectContaining({
          buyer_id: 'buyer-uuid-1',
          title: 'Industrial Component Procurement',
          trigger_window_minutes: 15,
          extension_duration_minutes: 8,
          extension_trigger: 'ANY_RANK_CHANGE',
        })
      );
    });
  });

  // Test 18: Correct backend field names are used
  it('Test 18: formats request payload with correct field names', async () => {
    api.createRFQ.mockResolvedValueOnce({ id: 'rfq-1', title: 'Test RFQ', items: [] });

    render(<CreateRfq />);
    await fillValidRfqBasics();
    fillValidAuctionSchedule('2026-09-01T10:00', '2026-09-01T11:00', '2026-09-01T11:30');

    fireEvent.click(screen.getByRole('button', { name: /Create RFQ/i }));

    await waitFor(() => {
      const callArgs = api.createRFQ.mock.calls[0][0];
      expect(callArgs).toHaveProperty('bid_start_time');
      expect(callArgs).toHaveProperty('bid_close_time');
      expect(callArgs).toHaveProperty('forced_bid_close_time');
      expect(callArgs).toHaveProperty('trigger_window_minutes');
      expect(callArgs).toHaveProperty('extension_duration_minutes');
      expect(callArgs).toHaveProperty('extension_trigger');
      expect(callArgs).toHaveProperty('items');
    });
  });

  // Test 19: Successful RFQ creation works with auction configuration
  it('Test 19: displays success card with persisted auction configuration details', async () => {
    api.createRFQ.mockResolvedValueOnce({
      id: 'rfq-uuid-success',
      title: 'Industrial Bearing & Pump Order',
      baseline_price: 75000,
      currency: 'USD',
      trigger_window_minutes: 10,
      extension_duration_minutes: 5,
      extension_trigger: 'BID_RECEIVED',
      status: 'DRAFT',
      items: [{ name: 'Item A', quantity: 1, unit: 'units' }],
    });

    render(<CreateRfq />);
    await fillValidRfqBasics();
    fillValidAuctionSchedule('2026-09-01T10:00', '2026-09-01T11:00', '2026-09-01T11:30');

    fireEvent.click(screen.getByRole('button', { name: /Create RFQ/i }));

    await waitFor(() => {
      expect(screen.getByText(/RFQ created successfully\./i)).toBeInTheDocument();
      expect(screen.getByText('rfq-uuid-success')).toBeInTheDocument();
      expect(screen.getByText(/10 Minutes/i)).toBeInTheDocument();
      expect(screen.getByText(/5 Minutes/i)).toBeInTheDocument();
      expect(screen.getByText('BID_RECEIVED')).toBeInTheDocument();
    });
  });

  // Test 20: Backend validation errors are displayed cleanly
  it('Test 20: catches backend validation error and displays clean alert', async () => {
    api.createRFQ.mockRejectedValueOnce({
      response: {
        status: 422,
        data: { detail: 'Forced close time must be later than bid close time' },
      },
    });

    render(<CreateRfq />);
    await fillValidRfqBasics();
    fillValidAuctionSchedule('2026-09-01T10:00', '2026-09-01T11:00', '2026-09-01T11:30');

    fireEvent.click(screen.getByRole('button', { name: /Create RFQ/i }));

    await waitFor(() => {
      expect(screen.getByText(/Submission Failed/i)).toBeInTheDocument();
      expect(screen.getByText(/Forced close time must be later than bid close time/i)).toBeInTheDocument();
    });
  });

  // Test 21: Submit button is disabled while creating
  it('Test 21: disables Create RFQ button during submission', async () => {
    let resolveRfq;
    api.createRFQ.mockImplementationOnce(() => new Promise((res) => { resolveRfq = res; }));

    render(<CreateRfq />);
    await fillValidRfqBasics();
    fillValidAuctionSchedule('2026-09-01T10:00', '2026-09-01T11:00', '2026-09-01T11:30');

    fireEvent.click(screen.getByRole('button', { name: /Create RFQ/i }));

    expect(screen.getByRole('button', { name: /Creating RFQ\.\.\./i })).toBeDisabled();

    resolveRfq({
      id: 'rfq-resolved',
      title: 'Resolved RFQ',
      baseline_price: 50000,
      currency: 'USD',
      status: 'DRAFT',
      items: [],
    });

    await waitFor(() => {
      expect(screen.getByText(/RFQ created successfully\./i)).toBeInTheDocument();
    });
  });

  // Test 22: Existing RFQ creation behavior still works
  it('Test 22: preserves complete existing RFQ creation form, buyer modal, and item rows', async () => {
    render(<CreateRfq />);
    expect(await screen.findByText(/1\. Buyer Information/i)).toBeInTheDocument();
    expect(screen.getByText(/2\. RFQ Information/i)).toBeInTheDocument();
    expect(screen.getByText(/3\. Auction Schedule/i)).toBeInTheDocument();
    expect(screen.getByText(/4\. British Auction Configuration/i)).toBeInTheDocument();
    expect(screen.getByText(/5\. RFQ Line Items/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Add Item/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Create RFQ/i })).toBeInTheDocument();
  });

});

describe('Buyer Selection & Reuse Workflow (Step Update)', () => {
  const mockBuyers = [
    {
      id: 'buyer-uuid-101',
      name: 'Alice Johnson',
      email: 'alice@precisionmfg.com',
      company_name: 'Precision Manufacturing Corp',
    },
    {
      id: 'buyer-uuid-102',
      name: 'Bob Smith',
      email: 'bob@globalaero.com',
      company_name: 'Global Aerospace Ltd',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // 1. Loading state
  it('1. renders loading state while fetching buyers', async () => {
    let resolveBuyers;
    api.getBuyers.mockImplementationOnce(() => new Promise((res) => { resolveBuyers = res; }));

    render(<CreateRfq />);
    expect(screen.getByText(/Loading buyers\.\.\./i)).toBeInTheDocument();
    expect(screen.getByText(/Fetching registered buyers from backend\.\.\./i)).toBeInTheDocument();

    resolveBuyers(mockBuyers);
    await waitFor(() => {
      expect(screen.queryByText(/Loading buyers\.\.\./i)).not.toBeInTheDocument();
    });
  });

  // 2. Load error and retry
  it('2. displays clean error and retry option when buyer fetching fails', async () => {
    api.getBuyers.mockRejectedValueOnce(new Error('Network error'));

    render(<CreateRfq />);
    await waitFor(() => {
      expect(screen.getByText(/Buyer Loading Failed/i)).toBeInTheDocument();
      expect(screen.getByText(/Unable to load buyers\. Please try again\./i)).toBeInTheDocument();
    });

    // Test retry
    api.getBuyers.mockResolvedValueOnce(mockBuyers);
    fireEvent.click(screen.getByRole('button', { name: /Retry/i }));

    await waitFor(() => {
      expect(screen.queryByText(/Buyer Loading Failed/i)).not.toBeInTheDocument();
      expect(screen.getByLabelText(/Select Existing Buyer/i)).toBeInTheDocument();
    });
  });

  // 3. Empty buyers state
  it('3. displays empty state when no buyers exist in database', async () => {
    api.getBuyers.mockResolvedValueOnce([]);

    render(<CreateRfq />);
    await waitFor(() => {
      expect(screen.getByText(/No buyers found\./i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Create Buyer/i })).toBeInTheDocument();
    });
  });

  // 4. Dropdown populated with existing buyers
  it('4. renders buyer dropdown populated with existing buyers and clean labels', async () => {
    api.getBuyers.mockResolvedValueOnce(mockBuyers);

    render(<CreateRfq />);
    await waitFor(() => {
      expect(screen.getByLabelText(/Select Existing Buyer/i)).toBeInTheDocument();
    });

    const select = screen.getByLabelText(/Select Existing Buyer/i);
    expect(select).toBeInTheDocument();

    const options = within(select).getAllByRole('option');
    expect(options).toHaveLength(3); // 1 placeholder + 2 buyers
    expect(options[0]).toHaveTextContent(/-- Choose an existing buyer --/i);
    expect(options[1]).toHaveTextContent(/Alice Johnson — Precision Manufacturing Corp — alice@precisionmfg\.com/i);
    expect(options[2]).toHaveTextContent(/Bob Smith — Global Aerospace Ltd — bob@globalaero\.com/i);

    // Ensure UUIDs are not displayed in the option text
    expect(options[1].textContent).not.toContain('buyer-uuid-101');
    expect(options[2].textContent).not.toContain('buyer-uuid-102');
  });

  // 5. Selecting an existing buyer
  it('5. selecting an existing buyer stores buyer and displays selected buyer card', async () => {
    api.getBuyers.mockResolvedValueOnce(mockBuyers);

    render(<CreateRfq />);
    await waitFor(() => {
      expect(screen.getByLabelText(/Select Existing Buyer/i)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/Select Existing Buyer/i), {
      target: { value: 'buyer-uuid-101' },
    });

    await waitFor(() => {
      expect(screen.getByText('Alice Johnson')).toBeInTheDocument();
      expect(screen.getByText('Precision Manufacturing Corp')).toBeInTheDocument();
      expect(screen.getByText('alice@precisionmfg.com')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Change Buyer/i })).toBeInTheDocument();
    });
  });

  // 6. Submitting RFQ with selected existing buyer
  it('6. submitting RFQ uses selected existing buyer_id without creating a new buyer', async () => {
    api.getBuyers.mockResolvedValueOnce(mockBuyers);
    api.createRFQ.mockResolvedValueOnce({
      id: 'rfq-reuse-1',
      title: 'Aerospace Bearings RFQ',
      baseline_price: 50000,
      currency: 'USD',
      status: 'DRAFT',
      items: [{ name: 'Item 1', quantity: 10, unit: 'units' }],
    });

    render(<CreateRfq />);
    await waitFor(() => {
      expect(screen.getByLabelText(/Select Existing Buyer/i)).toBeInTheDocument();
    });

    // Select Bob Smith
    fireEvent.change(screen.getByLabelText(/Select Existing Buyer/i), {
      target: { value: 'buyer-uuid-102' },
    });

    // Fill other RFQ details
    fireEvent.change(screen.getByLabelText(/RFQ Title/i), { target: { value: 'Aerospace Bearings RFQ' } });
    fireEvent.change(screen.getByLabelText(/Baseline Price/i), { target: { value: '50000' } });
    fillValidAuctionSchedule('2026-09-01T10:00', '2026-09-01T11:00', '2026-09-01T11:30');

    const nameInputs = screen.getAllByPlaceholderText(/e\.g\. Steel Bearing/i);
    const qtyInputs = screen.getAllByPlaceholderText(/e\.g\. 100/i);
    fireEvent.change(nameInputs[0], { target: { value: 'Titanium Fastener' } });
    fireEvent.change(qtyInputs[0], { target: { value: '50' } });

    fireEvent.click(screen.getByRole('button', { name: /Create RFQ/i }));

    await waitFor(() => {
      expect(api.createBuyer).not.toHaveBeenCalled();
      expect(api.createRFQ).toHaveBeenCalledWith(
        expect.objectContaining({
          buyer_id: 'buyer-uuid-102',
          title: 'Aerospace Bearings RFQ',
          baseline_price: 50000,
        })
      );
      expect(screen.getByText(/RFQ created successfully\./i)).toBeInTheDocument();
    });
  });

  // 7. Changing buyer resets selection
  it('7. clicking Change Buyer clears selection and allows re-selecting another buyer', async () => {
    api.getBuyers.mockResolvedValueOnce(mockBuyers);

    render(<CreateRfq />);
    await waitFor(() => {
      expect(screen.getByLabelText(/Select Existing Buyer/i)).toBeInTheDocument();
    });

    // Select Alice
    fireEvent.change(screen.getByLabelText(/Select Existing Buyer/i), {
      target: { value: 'buyer-uuid-101' },
    });
    expect(screen.getByText('Alice Johnson')).toBeInTheDocument();

    // Click Change Buyer
    fireEvent.click(screen.getByRole('button', { name: /Change Buyer/i }));

    await waitFor(() => {
      expect(screen.queryByText('Alice Johnson')).not.toBeInTheDocument();
      expect(screen.getByLabelText(/Select Existing Buyer/i)).toBeInTheDocument();
    });

    // Select Bob
    fireEvent.change(screen.getByLabelText(/Select Existing Buyer/i), {
      target: { value: 'buyer-uuid-102' },
    });
    expect(screen.getByText('Bob Smith')).toBeInTheDocument();
  });

  // 8. Create new buyer workflow & automatic selection
  it('8. creating a new buyer calls POST /api/v1/buyers, adds to list, and automatically selects it', async () => {
    api.getBuyers.mockResolvedValueOnce(mockBuyers);
    const newBuyer = {
      id: 'buyer-uuid-103',
      name: 'Charlie Davis',
      email: 'charlie@nexgen.com',
      company_name: 'NexGen Technologies',
    };
    api.createBuyer.mockResolvedValueOnce(newBuyer);

    render(<CreateRfq />);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /\+ Create New Buyer/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /\+ Create New Buyer/i }));
    const modal = screen.getByRole('dialog');

    fireEvent.change(within(modal).getByLabelText(/Full Name/i), { target: { value: 'Charlie Davis' } });
    fireEvent.change(within(modal).getByLabelText(/Email Address/i), { target: { value: 'charlie@nexgen.com' } });
    fireEvent.change(within(modal).getByLabelText(/Company Name/i), { target: { value: 'NexGen Technologies' } });

    fireEvent.click(within(modal).getByRole('button', { name: /Create Buyer/i }));

    await waitFor(() => {
      expect(api.createBuyer).toHaveBeenCalledWith({
        name: 'Charlie Davis',
        email: 'charlie@nexgen.com',
        company_name: 'NexGen Technologies',
      });
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      expect(screen.getByText('Charlie Davis')).toBeInTheDocument();
      expect(screen.getByText('NexGen Technologies')).toBeInTheDocument();
      expect(screen.getByText('charlie@nexgen.com')).toBeInTheDocument();
    });
  });

  // 9. Duplicate email conflict handling in modal
  it('9. duplicate email returns 409 and displays friendly conflict message', async () => {
    api.getBuyers.mockResolvedValueOnce(mockBuyers);
    api.createBuyer.mockRejectedValueOnce({
      response: {
        status: 409,
        data: { detail: "A buyer with email 'alice@precisionmfg.com' already exists" },
      },
    });

    render(<CreateRfq />);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /\+ Create New Buyer/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /\+ Create New Buyer/i }));
    const modal = screen.getByRole('dialog');

    fireEvent.change(within(modal).getByLabelText(/Full Name/i), { target: { value: 'Alice Duplicate' } });
    fireEvent.change(within(modal).getByLabelText(/Email Address/i), { target: { value: 'alice@precisionmfg.com' } });

    fireEvent.click(within(modal).getByRole('button', { name: /Create Buyer/i }));

    await waitFor(() => {
      expect(within(modal).getByText(/A buyer with this email already exists\./i)).toBeInTheDocument();
      expect(within(modal).getByRole('button', { name: /Select Existing Buyer \(Alice Johnson\)/i })).toBeInTheDocument();
    });

    // Click select existing from conflict
    fireEvent.click(within(modal).getByRole('button', { name: /Select Existing Buyer \(Alice Johnson\)/i }));

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      expect(screen.getByText('Alice Johnson')).toBeInTheDocument();
    });
  });

  // 10. Buyer requirement validation
  it('10. validates that buyer is required when submitting without buyer', async () => {
    api.getBuyers.mockResolvedValueOnce(mockBuyers);

    render(<CreateRfq />);
    await waitFor(() => {
      expect(screen.getByLabelText(/Select Existing Buyer/i)).toBeInTheDocument();
    });

    // Fill other fields without selecting buyer
    fireEvent.change(screen.getByLabelText(/RFQ Title/i), { target: { value: 'Valid Title' } });
    fireEvent.change(screen.getByLabelText(/Baseline Price/i), { target: { value: '1000' } });
    fillValidAuctionSchedule();

    const nameInputs = screen.getAllByPlaceholderText(/e\.g\. Steel Bearing/i);
    const qtyInputs = screen.getAllByPlaceholderText(/e\.g\. 100/i);
    fireEvent.change(nameInputs[0], { target: { value: 'Valid Item' } });
    fireEvent.change(qtyInputs[0], { target: { value: '1' } });

    fireEvent.click(screen.getByRole('button', { name: /Create RFQ/i }));

    expect(screen.getByText(/Buyer is required\./i)).toBeInTheDocument();
    expect(api.createRFQ).not.toHaveBeenCalled();
  });
});


