import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import SubmitBid from '../pages/SubmitBid';
import * as api from '../services/api';

// Mock the API module
vi.mock('../services/api', () => ({
  getRFQs: vi.fn(),
  getRFQById: vi.fn(),
  listSuppliers: vi.fn(),
  createSupplier: vi.fn(),
  createBid: vi.fn(),
}));

const mockRfqs = [
  {
    id: 'rfq-1111-aaaa',
    title: 'Industrial Component Procurement',
    baseline_price: 50000.0,
    currency: 'USD',
    status: 'PUBLISHED',
    items_count: 2,
  },
  {
    id: 'rfq-2222-bbbb',
    title: 'Server Hardware Batch',
    baseline_price: 120000.0,
    currency: 'USD',
    status: 'PUBLISHED',
    items_count: 1,
  },
];

const mockRfqDetail1 = {
  id: 'rfq-1111-aaaa',
  title: 'Industrial Component Procurement',
  description: 'Precision grade bearings',
  category: 'Industrial Machinery',
  currency: 'USD',
  baseline_price: 50000.0,
  status: 'PUBLISHED',
  buyer: {
    id: 'buyer-999',
    name: 'Global Tech Industries',
    email: 'buyer@globaltech.com',
  },
  items: [
    {
      id: 'item-1',
      rfq_id: 'rfq-1111-aaaa',
      name: 'Steel Roller Bearing',
      description: 'Inner diameter 50mm',
      quantity: 100,
      unit: 'units',
    },
    {
      id: 'item-2',
      rfq_id: 'rfq-1111-aaaa',
      name: 'Ceramic Ball Bearing',
      description: 'High heat resistant',
      quantity: 50,
      unit: 'units',
    },
  ],
};

const mockRfqDetail2 = {
  id: 'rfq-2222-bbbb',
  title: 'Server Hardware Batch',
  description: 'Rackmount servers',
  category: 'IT Hardware',
  currency: 'USD',
  baseline_price: 120000.0,
  status: 'PUBLISHED',
  items: [
    {
      id: 'item-server-1',
      rfq_id: 'rfq-2222-bbbb',
      name: '2U Server Node',
      description: 'Compute node',
      quantity: 10,
      unit: 'units',
    },
  ],
};

const mockSuppliers = [
  {
    id: 'sup-1111-kaushal',
    name: 'Kaushal Kumar',
    email: 'kk795109@gmail.com',
    company_name: 'ABC Company',
  },
  {
    id: 'sup-2222-apex',
    name: 'Apex Precision Engineering',
    email: 'supplier@apex.com',
    company_name: 'Apex Ltd',
  },
];

const mockBidResponse = {
  id: 'bid-7777-dddd',
  auction_id: 'auc-8888-eeee',
  round_id: 'rnd-9999-ffff',
  supplier_id: 'sup-1111-kaushal',
  rfq_id: 'rfq-1111-aaaa',
  amount: 47000.0,
  submitted_at: '2026-08-28T09:30:00Z',
  is_valid: true,
};

describe('SubmitBid Component - Supplier Reuse & Multi-RFQ Workflow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getRFQs.mockResolvedValue(mockRfqs);
    api.getRFQById.mockImplementation(async (id) => {
      if (id === 'rfq-2222-bbbb') return mockRfqDetail2;
      return mockRfqDetail1;
    });
    api.listSuppliers.mockResolvedValue(mockSuppliers);
    api.createSupplier.mockImplementation(async (data) => ({
      id: 'sup-new-3333',
      name: data.name,
      email: data.email,
      company_name: data.company_name || 'New Corp',
    }));
    api.createBid.mockResolvedValue(mockBidResponse);
  });

  const renderComponent = () =>
    render(
      <BrowserRouter>
        <SubmitBid />
      </BrowserRouter>
    );

  // 1. Submit Bid page renders
  it('1. renders Submit Bid page with all required form sections', async () => {
    renderComponent();

    expect(screen.getByText('Submit Supplier Bid')).toBeInTheDocument();
    expect(screen.getByText('1. Select RFQ')).toBeInTheDocument();
    expect(screen.getByText('2. Supplier Identity')).toBeInTheDocument();
    expect(screen.getByText('4. Bid Information')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /submit bid/i })).toBeInTheDocument();

    await waitFor(() => {
      expect(api.getRFQs).toHaveBeenCalled();
    });
  });

  // 2. Existing supplier selection UI renders
  it('2. renders existing supplier selection UI', async () => {
    renderComponent();

    expect(await screen.findByLabelText(/select existing supplier/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /\+ create new supplier/i })).toBeInTheDocument();
  });

  // 3. Supplier list is loaded from API service
  it('3. loads supplier list from API service on mount', async () => {
    renderComponent();

    await waitFor(() => {
      expect(api.listSuppliers).toHaveBeenCalledWith({ limit: 100 });
    });
  });

  // 4. Existing suppliers appear in the selection UI
  it('4. displays human-readable existing suppliers in the selection dropdown', async () => {
    renderComponent();

    const selectSupplierEl = await screen.findByLabelText(/select existing supplier/i);
    expect(selectSupplierEl).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Kaushal Kumar — ABC Company — kk795109@gmail.com/i)).toBeInTheDocument();
      expect(screen.getByText(/Apex Precision Engineering — Apex Ltd — supplier@apex.com/i)).toBeInTheDocument();
    });
  });

  // 5. Selecting an existing supplier stores its supplier_id
  it('5. selecting an existing supplier stores its supplier_id and updates selection', async () => {
    renderComponent();

    const selectSupplierEl = await screen.findByLabelText(/select existing supplier/i);
    fireEvent.change(selectSupplierEl, { target: { value: 'sup-1111-kaushal' } });

    expect(await screen.findByText('Kaushal Kumar')).toBeInTheDocument();
  });

  // 6. Selected supplier information is displayed
  it('6. clearly displays selected supplier name, company, and email', async () => {
    renderComponent();

    const selectSupplierEl = await screen.findByLabelText(/select existing supplier/i);
    fireEvent.change(selectSupplierEl, { target: { value: 'sup-1111-kaushal' } });

    expect(await screen.findByText('Kaushal Kumar')).toBeInTheDocument();
    expect(screen.getByText('ABC Company')).toBeInTheDocument();
    expect(screen.getByText('kk795109@gmail.com')).toBeInTheDocument();
  });

  // 7. Change Supplier works
  it('7. allows user to change selected supplier and return to dropdown', async () => {
    renderComponent();

    const selectSupplierEl = await screen.findByLabelText(/select existing supplier/i);
    fireEvent.change(selectSupplierEl, { target: { value: 'sup-1111-kaushal' } });

    const changeBtn = await screen.findByRole('button', { name: /change supplier/i });
    fireEvent.click(changeBtn);

    expect(await screen.findByLabelText(/select existing supplier/i)).toBeInTheDocument();
  });

  // 8. Create Supplier modal still opens
  it('8. opens Create Supplier modal when clicking + Create New Supplier', async () => {
    renderComponent();

    const openBtn = await screen.findByRole('button', { name: /\+ create new supplier/i });
    fireEvent.click(openBtn);

    expect(screen.getByText('Create Supplier Profile')).toBeInTheDocument();
    expect(screen.getByLabelText(/full name \/ contact/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
  });

  // 9. Creating a new supplier calls POST /api/v1/suppliers
  it('9. creating a new supplier calls POST /api/v1/suppliers with payload', async () => {
    renderComponent();

    const openBtn = await screen.findByRole('button', { name: /\+ create new supplier/i });
    fireEvent.click(openBtn);

    fireEvent.change(screen.getByLabelText(/full name \/ contact/i), { target: { value: 'Delta Technologies' } });
    fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: 'info@delta.com' } });
    fireEvent.change(screen.getByLabelText(/company name/i), { target: { value: 'Delta Inc' } });

    fireEvent.click(screen.getByRole('button', { name: /save supplier/i }));

    await waitFor(() => {
      expect(api.createSupplier).toHaveBeenCalledWith({
        name: 'Delta Technologies',
        email: 'info@delta.com',
        company_name: 'Delta Inc',
      });
    });
  });

  // 10. Newly created supplier is automatically selected
  it('10. newly created supplier is automatically selected for current bid', async () => {
    renderComponent();

    const openBtn = await screen.findByRole('button', { name: /\+ create new supplier/i });
    fireEvent.click(openBtn);

    fireEvent.change(screen.getByLabelText(/full name \/ contact/i), { target: { value: 'New Test Supplier' } });
    fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: 'test@supplier.com' } });
    fireEvent.click(screen.getByRole('button', { name: /save supplier/i }));

    expect(await screen.findByText('New Test Supplier')).toBeInTheDocument();
    expect(screen.getByText('test@supplier.com')).toBeInTheDocument();
  });

  // 11. Duplicate supplier email displays a friendly message
  it('11. displays friendly message on 409 duplicate email and allows selecting existing supplier', async () => {
    api.createSupplier.mockRejectedValueOnce({
      response: {
        status: 409,
        data: { detail: "A supplier with email 'kk795109@gmail.com' already exists" },
      },
    });

    renderComponent();

    const openBtn = await screen.findByRole('button', { name: /\+ create new supplier/i });
    fireEvent.click(openBtn);

    fireEvent.change(screen.getByLabelText(/full name \/ contact/i), { target: { value: 'Kaushal Kumar' } });
    fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: 'kk795109@gmail.com' } });
    fireEvent.click(screen.getByRole('button', { name: /save supplier/i }));

    expect(
      await screen.findByText(/a supplier with this email already exists\. please select the existing supplier\./i)
    ).toBeInTheDocument();

    const selectMatchBtn = screen.getByRole('button', { name: /select existing supplier \(kaushal kumar\)/i });
    fireEvent.click(selectMatchBtn);

    expect(await screen.findByText('Kaushal Kumar')).toBeInTheDocument();
    expect(screen.getByText('kk795109@gmail.com')).toBeInTheDocument();
  });

  it('11b. fetches existing supplier by email on 409 conflict when not in initial list and enables selection', async () => {
    api.listSuppliers.mockImplementation(async (params) => {
      if (params?.email === 'kk795@gmail.com') {
        return [
          {
            id: 'sup-9999-unlisted',
            name: 'Kaushal Kumar',
            email: 'kk795@gmail.com',
            company_name: 'ABC Company',
          },
        ];
      }
      return [];
    });
    api.createSupplier.mockRejectedValueOnce({
      response: {
        status: 409,
        data: { detail: "A supplier with email 'kk795@gmail.com' already exists" },
      },
    });

    renderComponent();

    const openBtn = await screen.findByRole('button', { name: /create.*supplier/i });
    fireEvent.click(openBtn);

    fireEvent.change(screen.getByLabelText(/full name \/ contact/i), { target: { value: 'Kaushal Kumar' } });
    fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: 'kk795@gmail.com' } });
    fireEvent.click(screen.getByRole('button', { name: /save supplier/i }));

    const selectMatchBtn = await screen.findByRole('button', { name: /select existing supplier \(kaushal kumar\)/i });
    fireEvent.click(selectMatchBtn);

    expect(await screen.findByText('Kaushal Kumar')).toBeInTheDocument();
    expect(screen.getByText('kk795@gmail.com')).toBeInTheDocument();
  });

  // 12. Submit Bid uses the selected existing supplier_id
  it('12. submits bid using the selected existing supplier_id UUID', async () => {
    renderComponent();

    // 1. Select RFQ
    const selectRfqEl = await screen.findByLabelText(/target rfq/i);
    fireEvent.change(selectRfqEl, { target: { value: 'rfq-1111-aaaa' } });

    // 2. Select Existing Supplier
    const selectSupplierEl = await screen.findByLabelText(/select existing supplier/i);
    fireEvent.change(selectSupplierEl, { target: { value: 'sup-1111-kaushal' } });

    await screen.findByText('Kaushal Kumar');

    // 3. Enter amount
    const amountInput = screen.getByLabelText(/bid amount/i);
    fireEvent.change(amountInput, { target: { value: '47000' } });

    // 4. Submit
    fireEvent.click(screen.getByRole('button', { name: /submit bid/i }));

    await waitFor(() => {
      expect(api.createBid).toHaveBeenCalledWith({
        rfq_id: 'rfq-1111-aaaa',
        supplier_id: 'sup-1111-kaushal',
        amount: 47000,
        rfq_item_id: 'item-1',
      });
    });

    expect(await screen.findByText('Bid submitted successfully.')).toBeInTheDocument();
  });

  // 13, 14, 15, 16. Existing supplier can bid on RFQ #1, then same supplier on RFQ #2 using SAME supplier_id without recreation
  it('13-16. allows same existing supplier to bid on RFQ #1 and RFQ #2 with identical supplier_id and NO recreate API calls', async () => {
    renderComponent();

    // --- STEP 1: Bid on RFQ #1 with Kaushal Kumar ---
    const selectRfqEl = await screen.findByLabelText(/target rfq/i);
    fireEvent.change(selectRfqEl, { target: { value: 'rfq-1111-aaaa' } });

    const selectSupplierEl = await screen.findByLabelText(/select existing supplier/i);
    fireEvent.change(selectSupplierEl, { target: { value: 'sup-1111-kaushal' } });

    await screen.findByText('Kaushal Kumar');

    fireEvent.change(screen.getByLabelText(/bid amount/i), { target: { value: '47000' } });
    fireEvent.click(screen.getByRole('button', { name: /submit bid/i }));

    await waitFor(() => {
      expect(api.createBid).toHaveBeenCalledWith(
        expect.objectContaining({
          rfq_id: 'rfq-1111-aaaa',
          supplier_id: 'sup-1111-kaushal',
          amount: 47000,
        })
      );
    });

    expect(await screen.findByText('Bid submitted successfully.')).toBeInTheDocument();

    // --- STEP 2: Reset and Bid on RFQ #2 with the SAME supplier ---
    fireEvent.click(screen.getByRole('button', { name: /submit another bid/i }));

    const selectRfqEl2 = await screen.findByLabelText(/target rfq/i);
    fireEvent.change(selectRfqEl2, { target: { value: 'rfq-2222-bbbb' } });

    const selectSupplierEl2 = await screen.findByLabelText(/select existing supplier/i);
    fireEvent.change(selectSupplierEl2, { target: { value: 'sup-1111-kaushal' } });

    await screen.findByText('Kaushal Kumar');

    fireEvent.change(screen.getByLabelText(/bid amount/i), { target: { value: '35000' } });
    fireEvent.click(screen.getByRole('button', { name: /submit bid/i }));

    await waitFor(() => {
      expect(api.createBid).toHaveBeenCalledWith(
        expect.objectContaining({
          rfq_id: 'rfq-2222-bbbb',
          supplier_id: 'sup-1111-kaushal',
          amount: 35000,
        })
      );
    });

    // Verify createSupplier was NEVER called during existing supplier reuse
    expect(api.createSupplier).not.toHaveBeenCalled();
    expect(await screen.findByText('Bid submitted successfully.')).toBeInTheDocument();
  });

  // 17. Supplier loading state is displayed
  it('17. displays supplier loading state while fetching suppliers from backend', async () => {
    api.listSuppliers.mockImplementation(() => new Promise(() => {})); // Never resolves
    renderComponent();

    expect(await screen.findByText('Loading suppliers...')).toBeInTheDocument();
  });

  // 18. Supplier loading error is handled
  it('18. handles supplier loading error gracefully and provides retry', async () => {
    api.listSuppliers.mockRejectedValueOnce(new Error('Network error'));
    renderComponent();

    expect(await screen.findByText('Unable to load suppliers. Please try again.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  // 19. Empty supplier list is handled
  it('19. handles empty supplier list gracefully and shows create supplier CTA', async () => {
    api.listSuppliers.mockResolvedValueOnce([]);
    renderComponent();

    expect(await screen.findByText('No suppliers found.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create supplier/i })).toBeInTheDocument();
  });

  // 20. Submit button is disabled while bid submission is in progress
  it('20. disables submit button during bid submission', async () => {
    api.createBid.mockImplementation(() => new Promise(() => {})); // Pending

    renderComponent();

    // Select RFQ
    const selectRfqEl = await screen.findByLabelText(/target rfq/i);
    fireEvent.change(selectRfqEl, { target: { value: 'rfq-1111-aaaa' } });

    // Select Supplier
    const selectSupplierEl = await screen.findByLabelText(/select existing supplier/i);
    fireEvent.change(selectSupplierEl, { target: { value: 'sup-1111-kaushal' } });

    await screen.findByText('Kaushal Kumar');

    // Amount & Submit
    fireEvent.change(screen.getByLabelText(/bid amount/i), { target: { value: '47000' } });
    const submitBtn = screen.getByRole('button', { name: /submit bid/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/submitting bid\.\.\./i)).toBeInTheDocument();
    });
    expect(submitBtn).toBeDisabled();
  });
});
