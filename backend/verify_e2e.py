import httpx
import psycopg2
import uuid
import uuid

BASE_URL = 'http://localhost:8000/api/v1'

print('=== 1. TEST BUYER CREATION (STEP 5 REGRESSION) ===')
buyer_resp = httpx.post(f'{BASE_URL}/buyers', json={
    'name': 'Global Aerospace Corp',
    'email': f'procurement_{uuid.uuid4().hex[:6]}@globalaero.com',
    'company_name': 'Global Aerospace'
})
assert buyer_resp.status_code == 201, f'Buyer creation failed: {buyer_resp.text}'
buyer = buyer_resp.json()
print(f'Created Buyer: {buyer["name"]} (ID: {buyer["id"]})')

print('\n=== 2. TEST RFQ CREATION (STEP 5 REGRESSION) ===')
rfq_resp = httpx.post(f'{BASE_URL}/rfqs', json={
    'buyer_id': buyer['id'],
    'title': 'Turbine Shaft Procurement',
    'description': 'High precision aerospace turbine shafts',
    'category': 'Aerospace',
    'currency': 'USD',
    'baseline_price': 75000.00,
    'items': [
        {'name': 'Titanium Turbine Shaft', 'description': 'Grade 5 Titanium', 'quantity': 50, 'unit': 'units'},
        {'name': 'High-Pressure Seal Ring', 'description': 'Inconel seal', 'quantity': 100, 'unit': 'sets'}
    ]
})
assert rfq_resp.status_code == 201, f'RFQ creation failed: {rfq_resp.text}'
rfq = rfq_resp.json()
print(f'Created RFQ: {rfq["title"]} (ID: {rfq["id"]}, Items: {len(rfq["items"])})')
item_1 = rfq['items'][0]
print(f'Line Item 1: {item_1["name"]} (ID: {item_1["id"]}, Qty: {item_1["quantity"]} {item_1["unit"]})')

print('\n=== 3. TEST SUPPLIER CREATION (STEP 6) ===')
supplier_resp = httpx.post(f'{BASE_URL}/suppliers', json={
    'name': 'Apex Precision Engineering',
    'email': f'bids_{uuid.uuid4().hex[:6]}@apexprecision.com',
    'company_name': 'Apex Precision Ltd'
})
assert supplier_resp.status_code == 201, f'Supplier creation failed: {supplier_resp.text}'
supplier = supplier_resp.json()
print(f'Created Supplier: {supplier["name"]} (ID: {supplier["id"]})')

print('\n=== 4. TEST SUPPLIER BID SUBMISSION (STEP 6) ===')
bid_resp = httpx.post(f'{BASE_URL}/bids', json={
    'rfq_id': rfq['id'],
    'supplier_id': supplier['id'],
    'amount': 68000.00,
    'rfq_item_id': item_1['id']
})
assert bid_resp.status_code == 201, f'Bid submission failed: {bid_resp.text}'
bid = bid_resp.json()
print(f'Submitted Bid ID: {bid["id"]}')
print(f'Bid Amount: {bid["amount"]}')
print(f'Auction ID: {bid["auction_id"]}')
print(f'Round ID: {bid["round_id"]}')
print(f'Status is_valid: {bid["is_valid"]}')
print(f'Submitted At: {bid["submitted_at"]}')

print('\n=== 5. DIRECT POSTGRESQL PERSISTENCE VERIFICATION ===')
conn = psycopg2.connect('postgresql://postgres@127.0.0.1:5433/british_auction')
cur = conn.cursor()

# Verify Bid in PostgreSQL
cur.execute('SELECT id, auction_id, round_id, supplier_id, amount, is_valid, submitted_at FROM bids WHERE id = %s', (bid['id'],))
db_bid = cur.fetchone()
assert db_bid is not None, 'Bid not found in PostgreSQL!'
print(f'DB Verified Bid: ID={db_bid[0]}, Amount={db_bid[4]}, Valid={db_bid[5]}')

# Verify Auction in PostgreSQL
cur.execute('SELECT id, rfq_id, status, current_round FROM auctions WHERE id = %s', (bid['auction_id'],))
db_auction = cur.fetchone()
assert db_auction is not None, 'Auction not found in PostgreSQL!'
print(f'DB Verified Auction: ID={db_auction[0]}, RFQ_ID={db_auction[1]}, Status={db_auction[2]}, Round={db_auction[3]}')

# Verify AuctionRound in PostgreSQL
cur.execute('SELECT id, auction_id, round_number, status FROM auction_rounds WHERE id = %s', (bid['round_id'],))
db_round = cur.fetchone()
assert db_round is not None, 'AuctionRound not found in PostgreSQL!'
print(f'DB Verified Round: ID={db_round[0]}, RoundNumber={db_round[2]}, Status={db_round[3]}')

# Verify ActivityLog in PostgreSQL
cur.execute('SELECT id, rfq_id, actor_type, event_type, message, metadata_json FROM activity_logs WHERE rfq_id = %s AND event_type = %s', (rfq['id'], 'BID_SUBMITTED'))
db_log = cur.fetchone()
assert db_log is not None, 'ActivityLog BID_SUBMITTED not found in PostgreSQL!'
print(f'DB Verified ActivityLog: Event={db_log[3]}, Actor={db_log[2]}, Message="{db_log[4]}"')

print('\n=== 6. NEGATIVE TESTING ===')
# Test non-existent RFQ
r_bad_rfq = httpx.post(f'{BASE_URL}/bids', json={'rfq_id': str(uuid.uuid4()), 'supplier_id': supplier['id'], 'amount': 50000})
assert r_bad_rfq.status_code == 404
print('Negative Test 1 (Non-existent RFQ 404): PASSED')

# Test non-existent Supplier
r_bad_sup = httpx.post(f'{BASE_URL}/bids', json={'rfq_id': rfq['id'], 'supplier_id': str(uuid.uuid4()), 'amount': 50000})
assert r_bad_sup.status_code == 404
print('Negative Test 2 (Non-existent Supplier 404): PASSED')

# Test negative amount
r_neg_amt = httpx.post(f'{BASE_URL}/bids', json={'rfq_id': rfq['id'], 'supplier_id': supplier['id'], 'amount': -100})
assert r_neg_amt.status_code == 422
print('Negative Test 3 (Negative Amount 422): PASSED')

# Test missing amount
r_miss_amt = httpx.post(f'{BASE_URL}/bids', json={'rfq_id': rfq['id'], 'supplier_id': supplier['id']})
assert r_miss_amt.status_code == 422
print('Negative Test 4 (Missing Amount 422): PASSED')

# Test invalid item ID
r_bad_item = httpx.post(f'{BASE_URL}/bids', json={'rfq_id': rfq['id'], 'supplier_id': supplier['id'], 'amount': 50000, 'rfq_item_id': str(uuid.uuid4())})
assert r_bad_item.status_code == 404
print('Negative Test 5 (Invalid RFQ Item ID 404): PASSED')

print('\n>>> ALL LIVE VERIFICATIONS AND DB PERSISTENCE CHECKS PASSED SUCCESSFULLY! <<<')

