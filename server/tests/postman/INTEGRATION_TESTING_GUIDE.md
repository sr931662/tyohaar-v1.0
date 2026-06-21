# Tyohaar API — Integration Testing Guide

## Files

| File | Purpose |
|------|---------|
| `Tyohaar_API_Collection.postman_collection.json` | 272 requests across 20 folders |
| `Tyohaar_Development.postman_environment.json` | Local dev environment variables |
| `Tyohaar_Production.postman_environment.json` | Production environment variables |
| `generate_collection.py` | Re-generates the collection from source |

---

## Quick Start

### 1. Import into Postman

1. Open Postman → **Import**
2. Import `Tyohaar_API_Collection.postman_collection.json`
3. Import `Tyohaar_Development.postman_environment.json`
4. Select the **Tyohaar - Development** environment from the top-right dropdown

### 2. Pre-flight — set required variables

In the environment editor, fill in:

| Variable | Value |
|----------|-------|
| `TEST_PHONE` | A real or mock phone number (e.g. `+919999999999`) |
| `TEST_VENDOR_PHONE` | Different phone for the vendor user |
| `TEST_ADMIN_EMAIL` | Admin email seeded in DB |
| `TEST_ADMIN_PASSWORD` | Admin password |

Everything else (tokens, IDs) is **auto-populated** by test scripts as you run requests.

### 3. Start the backend

```bash
cd server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify with: `GET {{BASE_URL}}/health` → should return `{"status": "healthy"}`

---

## Authentication Flow (manual first run)

The backend uses OTP-based auth — no password for customers/vendors. The sequence is:

```
POST /auth/otp/request   →  backend sends OTP (check logs/SMS)
                              manually set {{OTP}} in environment
POST /auth/otp/verify    →  returns JWT pair → auto-saved to ACCESS_TOKEN / CUSTOMER_TOKEN
POST /admin/auth/login   →  admin uses email+password → auto-saved to ADMIN_TOKEN
```

> **Tip:** In development, check the server console or database `auth_otps` table to get the OTP value.

---

## Collection Structure

```
Tyohaar API — Complete Integration Suite
├── 🏥 Health Checks            (4 requests)   — infrastructure probes
├── 🔐 Authentication           (8 requests)   — OTP, JWT, sessions
├── 👤 Users                    (13 requests)  — profile, addresses, devices
├── 🏪 Vendors                  (17 requests)  — profile, docs, gallery, reviews
├── 🎉 Occasions & Celebrations (26 requests)  — occasions, guests, checklists
├── 📦 Packages                 (14 requests)  — CRUD, items, availability
├── 📅 Bookings                 (14 requests)  — lifecycle, cancellations, invoices
├── 💳 Payments                 (14 requests)  — initiate, verify, refunds, splits
├── 💰 Wallets                  (11 requests)  — balance, transactions, rewards
├── 🎫 Memberships              (12 requests)  — plans, subscribe, features
├── 🔔 Notifications            (9 requests)   — preferences, send, broadcast
├── 🎫 Support                  (9 requests)   — tickets, messages, assignments
├── 🖼️ Media                    (15 requests)  — images, videos, memories
├── 🔗 Referrals                (7 requests)   — codes, stats, rewards
├── 💹 Budgets                  (14 requests)  — budgets, expenses, alerts
├── 🛡️ Admin                    (11 requests)  — auth, roles, permissions, audit
├── 🌍 Common                   (18 requests)  — states, cities, banners, FAQs
├── 🔄 End-to-End Flows
│   ├── 🛒 Customer Journey     (12 requests)  — Register → Browse → Book → Pay → Review
│   ├── 🏪 Vendor Journey       (10 requests)  — Register → Approve → Package → Complete
│   └── 🛡️ Admin Journey        (9 requests)   — Login → Approve → Manage → Audit
├── ❌ Negative Testing         (17 requests)  — validation errors, role violations
└── 🔒 Security Testing        (10 requests)  — RBAC, injection, IDOR, headers
```

**Total: 272 requests**

---

## Test Script Standards

Every request validates:

1. **Status code** — exact expected HTTP status
2. **Response time** — must complete in under 3000ms
3. **JSON** — response is valid JSON
4. **X-Request-ID header** — middleware is injecting request IDs
5. **Schema** — `data` field present on success, `error` field on failure

Additional per-endpoint assertions cover: pagination `meta`, JWT fields, specific business fields.

---

## Request Chaining

Tokens and resource IDs are automatically saved to environment variables by test scripts:

| After request | Saves to |
|--------------|---------|
| Verify OTP (Customer) | `ACCESS_TOKEN`, `REFRESH_TOKEN`, `CUSTOMER_TOKEN` |
| Verify OTP (Vendor) | `VENDOR_TOKEN` |
| Admin Login | `ADMIN_TOKEN`, `TEST_ADMIN_ID` |
| Create Vendor | `TEST_VENDOR_ID` |
| Create Package | `TEST_PACKAGE_ID` |
| Create Booking | `TEST_BOOKING_ID` |
| Initiate Payment | `TEST_PAYMENT_ID` |
| Create Wallet | `TEST_WALLET_ID` |
| Create Budget | `TEST_BUDGET_ID` |
| Create Celebration | `TEST_CELEBRATION_ID` |
| Add Address | `TEST_ADDRESS_ID` |
| Register Image | `TEST_IMAGE_ID` |
| Create Memory | `TEST_MEMORY_ID` |
| Subscribe Membership | `TEST_MEMBERSHIP_ID` |
| Create Ticket | `TEST_TICKET_ID` |

---

## Running the E2E Flows

### Using Collection Runner (recommended)

1. Click **Run collection** (play button on collection)
2. Select folder: `End-to-End Flows > Customer Journey`
3. Set delay: `500ms` between requests (avoids race conditions)
4. Click **Run**

### Recommended run order

```
1. Admin Login       (to get ADMIN_TOKEN for vendor approval mid-flow)
2. Customer Journey  (sets up user, booking, payment)
3. Vendor Journey    (sets up vendor, packages)
4. Admin Journey     (manages approvals, audits)
```

---

## Negative Testing

The Negative Testing folder covers:

| Case | Expected |
|------|---------|
| Missing JWT | 401 |
| Invalid/expired JWT | 401 |
| Customer → Admin route | 403 |
| Customer → Vendor route | 403 |
| Invalid UUID path param | 422 or 404 |
| Invalid OTP | 400 |
| Expired refresh token | 401 |
| Negative price in package | 422 |
| Past booking date | 422 |
| Double payment | 409 |
| Invalid coupon | 400 |
| Wallet underflow | 400 |
| Non-existent resource | 404 |
| Missing required fields | 422 |
| `page_size > 100` | 422 or capped at 100 |

---

## Security Testing

The Security Testing folder validates:

| Test | What It Checks |
|------|---------------|
| SQL Injection | Input is sanitized; no 500 errors |
| XSS Payload | `<script>` tags stripped from responses |
| Mass Assignment | Role elevation ignored by API |
| IDOR | Other users' private resources return 403/404 |
| Algorithm Confusion | `alg: none` JWT rejected |
| Security Headers | X-Content-Type-Options, X-Frame-Options present |
| Rate Limiting | 429 + Retry-After header on exhaustion |
| Wrong Content-Type | 400/415/422 returned |

---

## Regenerating the Collection

If routes change, update `generate_collection.py` and re-run:

```bash
cd server
python tests/postman/generate_collection.py
```

The script outputs the JSON and prints request count.

---

## Newman (CI/CD) — Automated Execution

Install Newman:
```bash
npm install -g newman
```

Run the full suite:
```bash
newman run tests/postman/Tyohaar_API_Collection.postman_collection.json \
  --environment tests/postman/Tyohaar_Development.postman_environment.json \
  --reporters cli,json \
  --reporter-json-export tests/postman/results/run_$(date +%Y%m%d_%H%M%S).json \
  --delay-request 300 \
  --timeout-request 10000
```

Run only E2E flows:
```bash
newman run tests/postman/Tyohaar_API_Collection.postman_collection.json \
  --environment tests/postman/Tyohaar_Development.postman_environment.json \
  --folder "End-to-End Flows" \
  --delay-request 500
```

Run only security tests:
```bash
newman run tests/postman/Tyohaar_API_Collection.postman_collection.json \
  --environment tests/postman/Tyohaar_Development.postman_environment.json \
  --folder "Security Testing"
```

---

## Known Constraints

- **OTP step is manual** — In real CI you'd need to seed the OTP or mock the SMS provider.
  Either use a test phone that returns a fixed OTP (via SMS mock), or query the DB:
  ```sql
  SELECT otp_code FROM auth_otps WHERE phone = '+919999999999' ORDER BY created_at DESC LIMIT 1;
  ```

- **Webhook tests not included** — Payment gateway webhooks require a public URL + valid HMAC signature. Test with ngrok or a gateway sandbox.

- **File upload tests (multipart/form-data)** — Support ticket attachments and direct binary uploads must be tested manually; Postman scripts cannot easily generate binary form data programmatically.

- **Media upload flow** — The API uses a two-step upload: (1) register → get `upload_url`, (2) PUT file to S3/GCS, (3) confirm. Steps 1 and 3 are tested; step 2 (external S3 PUT) requires a real upload URL.
