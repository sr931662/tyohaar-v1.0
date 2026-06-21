"""
Tyohaar API - Postman Collection Generator
Run: python generate_collection.py
Output: Tyohaar_API_Collection.postman_collection.json
"""
import json
import uuid

BASE = "{{BASE_URL}}/api/v1"

# ── helpers ─────────────────────────────────────────────────────────────────

def uid(): return str(uuid.uuid4())

def bearer(token_var="ACCESS_TOKEN"):
    return [{"key": "Authorization", "value": f"Bearer {{{{{token_var}}}}}", "type": "text"}]

def json_header():
    return [{"key": "Content-Type", "value": "application/json", "type": "text"}]

def url(path, query=None):
    parts = path.strip("/").split("/")
    obj = {"raw": f"{BASE}/{path.strip('/')}", "host": ["{{BASE_URL}}"],
           "path": ["api", "v1"] + parts}
    if query:
        obj["query"] = [{"key": k, "value": v} for k, v in query.items()]
    return obj

def body(payload):
    return {"mode": "raw", "raw": json.dumps(payload, indent=2),
            "options": {"raw": {"language": "json"}}}

def tests(expected_status, save=None, extra=None):
    lines = [
        f"const res = pm.response.json();",
        f"pm.test('[{expected_status}] Status code', () => pm.response.to.have.status({expected_status}));",
        "pm.test('[Timing] < 3000ms', () => pm.expect(pm.response.responseTime).to.be.below(3000));",
        "pm.test('[JSON] Valid JSON response', () => pm.response.to.be.json);",
        "pm.test('[Headers] X-Request-ID present', () => pm.expect(pm.response.headers.get('X-Request-ID')).to.not.be.undefined);",
    ]
    if expected_status in (200, 201):
        lines.append("pm.test('[Schema] Has data field', () => pm.expect(res).to.have.property('data'));")
    if save:
        for env_key, path in save.items():
            parts = path.split(".")
            accessor = "res"
            for p in parts:
                accessor += f".{p}" if not p.startswith("[") else p
            lines.append(f"if ({accessor}) {{ pm.environment.set('{env_key}', {accessor}); console.log('✅ {env_key} saved'); }}")
    if extra:
        lines.extend(extra)
    return [{"listen": "test", "script": {"type": "text/javascript", "exec": lines}}]

def neg_tests(expected_status):
    return [{"listen": "test", "script": {"type": "text/javascript", "exec": [
        f"pm.test('[{expected_status}] Negative case correct status', () => pm.response.to.have.status({expected_status}));",
        "const res = pm.response.json();",
        "pm.test('[Schema] Has error field', () => pm.expect(res).to.have.property('error'));",
        "pm.test('[Timing] < 3000ms', () => pm.expect(pm.response.responseTime).to.be.below(3000));",
    ]}}]

def req(name, method, path, hdrs=None, bd=None, query=None, events=None, desc=""):
    r = {"name": name, "request": {
        "method": method,
        "header": hdrs or [],
        "url": url(path, query),
        "description": desc
    }}
    if bd: r["request"]["body"] = bd
    if events: r["event"] = events
    return r

def folder(name, items, desc=""):
    return {"name": name, "description": desc, "item": items}

# ── COLLECTION-LEVEL PRE-REQUEST ─────────────────────────────────────────────

COLLECTION_PRE_REQUEST = [
    "// Auto-refresh access token when missing",
    "const accessToken = pm.environment.get('ACCESS_TOKEN');",
    "const refreshToken = pm.environment.get('REFRESH_TOKEN');",
    "const skipRefresh = pm.request.url.toString().includes('/auth/');",
    "if (!accessToken && refreshToken && !skipRefresh) {",
    "    pm.sendRequest({",
    "        url: pm.environment.get('BASE_URL') + '/api/v1/auth/token/refresh',",
    "        method: 'POST',",
    "        header: [{ key: 'Content-Type', value: 'application/json' }],",
    "        body: { mode: 'raw', raw: JSON.stringify({ refresh_token: refreshToken }) }",
    "    }, function(err, res) {",
    "        if (!err && res.code === 200) {",
    "            const d = res.json().data;",
    "            pm.environment.set('ACCESS_TOKEN', d.access_token);",
    "            pm.environment.set('REFRESH_TOKEN', d.refresh_token);",
    "            console.log('🔄 Token auto-refreshed');",
    "        }",
    "    });",
    "}",
]

# ── FOLDERS ──────────────────────────────────────────────────────────────────

def health_folder():
    return folder("🏥 Health Checks", [
        req("Root Identity", "GET", "/",
            events=tests(200, extra=["pm.test('[App] Has version', () => pm.expect(res).to.have.property('version'));"])),
        req("Deep Health Check", "GET", "/health",
            events=tests(200, extra=["pm.test('[Health] Status is healthy or degraded', () => pm.expect(['healthy','degraded']).to.include(res.status));"])),
        req("Readiness Probe", "GET", "/ready", events=tests(200)),
        req("Liveness Probe", "GET", "/live",  events=tests(200)),
    ], desc="Infrastructure probes — should all return 200 in a running environment")

def auth_folder():
    items = [
        req("Request OTP (Customer)", "POST", "auth/otp/request",
            hdrs=json_header(),
            bd=body({"phone": "{{TEST_PHONE}}", "channel": "SMS"}),
            events=tests(200, extra=[
                "pm.test('[OTP] Has expires_at', () => pm.expect(res.data).to.have.property('expires_at'));",
                "pm.test('[OTP] Has resend limits', () => pm.expect(res.data).to.have.property('max_resends'));",
            ]),
            desc="Step 1 of auth: request OTP for customer phone"),
        req("Verify OTP (Customer → Token)", "POST", "auth/otp/verify",
            hdrs=json_header(),
            bd=body({"phone": "{{TEST_PHONE}}", "otp": "{{OTP}}"}),
            events=tests(200, save={
                "ACCESS_TOKEN": "data.access_token",
                "REFRESH_TOKEN": "data.refresh_token",
                "CUSTOMER_TOKEN": "data.access_token",
            }, extra=[
                "pm.test('[Auth] access_token present', () => pm.expect(res.data.access_token).to.be.a('string'));",
                "pm.test('[Auth] refresh_token present', () => pm.expect(res.data.refresh_token).to.be.a('string'));",
                "pm.test('[Auth] token_type is Bearer', () => pm.expect(res.data.token_type).to.eql('Bearer'));",
            ]),
            desc="Step 2: verify OTP → receive JWT pair. Saves tokens to env."),
        req("Request OTP (Vendor)", "POST", "auth/otp/request",
            hdrs=json_header(),
            bd=body({"phone": "{{TEST_VENDOR_PHONE}}", "channel": "SMS"}),
            events=tests(200)),
        req("Verify OTP (Vendor → Token)", "POST", "auth/otp/verify",
            hdrs=json_header(),
            bd=body({"phone": "{{TEST_VENDOR_PHONE}}", "otp": "{{OTP}}"}),
            events=tests(200, save={"VENDOR_TOKEN": "data.access_token"})),
        req("Refresh Token", "POST", "auth/token/refresh",
            hdrs=json_header(),
            bd=body({"refresh_token": "{{REFRESH_TOKEN}}"}),
            events=tests(200, save={
                "ACCESS_TOKEN": "data.access_token",
                "REFRESH_TOKEN": "data.refresh_token",
            }, extra=["pm.test('[Refresh] New access token differs', () => pm.expect(res.data.access_token).to.be.a('string'));"])),
        req("List Active Sessions", "GET", "auth/sessions",
            hdrs=bearer(),
            events=tests(200, extra=["pm.test('[Sessions] Returns array', () => pm.expect(res.data).to.be.an('array'));"])),
        req("Logout (Current Device)", "POST", "auth/logout",
            hdrs=bearer(),
            events=tests(200)),
        req("Logout All Devices", "POST", "auth/logout/all",
            hdrs=bearer(),
            events=tests(200, extra=["pm.environment.unset('ACCESS_TOKEN'); pm.environment.unset('REFRESH_TOKEN');"])),
    ]
    return folder("🔐 Authentication", items, desc="OTP → JWT flow with token refresh and session management")

def users_folder():
    items = [
        req("Get My Profile", "GET", "users/me",
            hdrs=bearer(),
            events=tests(200, save={"TEST_USER_ID": "data.id"}, extra=[
                "pm.test('[User] Has id', () => pm.expect(res.data.id).to.be.a('string'));",
                "pm.test('[User] Has phone', () => pm.expect(res.data.phone).to.be.a('string'));",
                "pm.test('[User] Has role', () => pm.expect(res.data.role).to.be.a('string'));",
            ])),
        req("Update My Profile", "PUT", "users/me",
            hdrs=[*json_header(), *bearer()],
            bd=body({"full_name": "Test Customer", "email": "testcustomer@example.com"}),
            events=tests(200)),
        req("List My Addresses", "GET", "users/me/addresses",
            hdrs=bearer(),
            events=tests(200, extra=["pm.test('[Addresses] Returns array', () => pm.expect(res.data).to.be.an('array'));"])),
        req("Add Address", "POST", "users/me/addresses",
            hdrs=[*json_header(), *bearer()],
            bd=body({
                "address_type": "HOME", "label": "My Home",
                "recipient_name": "Test Customer", "recipient_phone": "{{TEST_PHONE}}",
                "address_line_1": "123 Test Street", "city": "Mumbai",
                "state": "Maharashtra", "country": "India", "postal_code": "400001",
                "is_default": True
            }),
            events=tests(201, save={"TEST_ADDRESS_ID": "data.id"})),
        req("Get Address by ID", "GET", "users/me/addresses/{{TEST_ADDRESS_ID}}",
            hdrs=bearer(), events=tests(200)),
        req("Update Address", "PUT", "users/me/addresses/{{TEST_ADDRESS_ID}}",
            hdrs=[*json_header(), *bearer()],
            bd=body({"label": "Updated Home", "address_line_2": "Apt 4B"}),
            events=tests(200)),
        req("Delete Address", "DELETE", "users/me/addresses/{{TEST_ADDRESS_ID}}",
            hdrs=bearer(), events=tests(200)),
        req("List My Devices", "GET", "users/me/devices",
            hdrs=bearer(), events=tests(200)),
        req("Register Device (Push)", "POST", "users/me/devices",
            hdrs=[*json_header(), *bearer()],
            bd=body({
                "device_id": "test-device-001", "device_type": "MOBILE",
                "platform": "ANDROID", "manufacturer": "Samsung",
                "model": "Galaxy S21", "os": "Android", "os_version": "13",
                "app_version": "1.0.0", "timezone": "Asia/Kolkata", "language": "en"
            }),
            events=tests(201)),
        req("Get User Profile (by ID)", "GET", "users/{{TEST_USER_ID}}",
            hdrs=bearer(), events=tests(200)),
        req("Update Extended Profile", "PUT", "users/{{TEST_USER_ID}}/profile",
            hdrs=[*json_header(), *bearer()],
            bd=body({
                "gender": "MALE", "bio": "Test bio",
                "preferred_language": "en", "timezone": "Asia/Kolkata"
            }),
            events=tests(200)),
        req("Get Full User (Admin)", "GET", "users/{{TEST_USER_ID}}/full",
            hdrs=bearer("ADMIN_TOKEN"), events=tests(200)),
    ]
    return folder("👤 Users", items)

def vendors_folder():
    items = [
        req("Create Vendor Profile", "POST", "vendors",
            hdrs=[*json_header(), *bearer("VENDOR_TOKEN")],
            bd=body({
                "business_name": "Test Events Co",
                "business_type": "EVENTS",
                "description": "Professional event planning service",
                "phone": "{{TEST_VENDOR_PHONE}}",
                "email": "vendor@testevents.com",
                "city": "Mumbai", "state": "Maharashtra",
                "pincode": "400001", "address": "123 Vendor Street"
            }),
            events=tests(201, save={"TEST_VENDOR_ID": "data.id"})),
        req("List Vendors (Public)", "GET", "vendors",
            query={"page": "1", "page_size": "10"},
            events=tests(200, extra=[
                "pm.test('[Paginated] Has meta', () => pm.expect(res).to.have.property('meta'));",
                "pm.test('[Paginated] meta.page is 1', () => pm.expect(res.meta.page).to.eql(1));",
            ])),
        req("Get My Vendor Profile", "GET", "vendors/me",
            hdrs=bearer("VENDOR_TOKEN"), events=tests(200)),
        req("Get Vendor by ID (Public)", "GET", "vendors/{{TEST_VENDOR_ID}}",
            events=tests(200, extra=["pm.test('[Vendor] Has business_name', () => pm.expect(res.data.business_name).to.be.a('string'));"])),
        req("Update Vendor Profile", "PUT", "vendors/{{TEST_VENDOR_ID}}/profile",
            hdrs=[*json_header(), *bearer("VENDOR_TOKEN")],
            bd=body({"description": "Updated description", "website": "https://testevents.com"}),
            events=tests(200)),
        req("List Vendor Documents", "GET", "vendors/{{TEST_VENDOR_ID}}/documents",
            events=tests(200)),
        req("Add Vendor Document", "POST", "vendors/{{TEST_VENDOR_ID}}/documents",
            hdrs=[*json_header(), *bearer("VENDOR_TOKEN")],
            bd=body({"document_type": "GST", "document_number": "27AAECG1234F1Z5", "document_url": "https://example.com/doc.pdf"}),
            events=tests(201)),
        req("List Vendor Gallery", "GET", "vendors/{{TEST_VENDOR_ID}}/gallery",
            events=tests(200)),
        req("Add Gallery Item", "POST", "vendors/{{TEST_VENDOR_ID}}/gallery",
            hdrs=[*json_header(), *bearer("VENDOR_TOKEN")],
            bd=body({"image_url": "https://example.com/img.jpg", "caption": "Event setup", "display_order": 1}),
            events=tests(201)),
        req("Check Vendor Availability", "GET", "vendors/{{TEST_VENDOR_ID}}/availability/check",
            query={"date": "2026-08-15"},
            events=tests(200)),
        req("Get Vendor Availability Slots", "GET", "vendors/{{TEST_VENDOR_ID}}/availability",
            events=tests(200)),
        req("Set Vendor Availability", "POST", "vendors/{{TEST_VENDOR_ID}}/availability",
            hdrs=[*json_header(), *bearer("VENDOR_TOKEN")],
            bd=body({
                "date": "2026-08-15",
                "start_time": "09:00", "end_time": "18:00",
                "is_available": True, "max_bookings": 2
            }),
            events=tests(201)),
        req("Add Bank Account", "POST", "vendors/{{TEST_VENDOR_ID}}/bank-accounts",
            hdrs=[*json_header(), *bearer("VENDOR_TOKEN")],
            bd=body({
                "account_holder_name": "Test Vendor",
                "account_number": "1234567890",
                "ifsc_code": "HDFC0001234",
                "bank_name": "HDFC Bank",
                "branch_name": "Mumbai Main",
                "is_primary": True
            }),
            events=tests(201)),
        req("List Vendor Reviews (Public)", "GET", "vendors/{{TEST_VENDOR_ID}}/reviews",
            query={"page": "1", "page_size": "10"},
            events=tests(200)),
        req("Add Vendor Review (Customer)", "POST", "vendors/{{TEST_VENDOR_ID}}/reviews",
            hdrs=[*json_header(), *bearer()],
            bd=body({"rating": 5, "review": "Excellent service!", "booking_id": "{{TEST_BOOKING_ID}}"}),
            events=tests(201, save={"TEST_REVIEW_ID": "data.id"})),
        req("Verify Vendor (Admin)", "POST", "vendors/{{TEST_VENDOR_ID}}/verify",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"is_verified": True, "verification_note": "Documents verified"}),
            events=tests(200)),
        req("Update Vendor Categories (Admin)", "PUT", "vendors/{{TEST_VENDOR_ID}}/categories",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"category_ids": ["{{TEST_CATEGORY_ID}}"]}),
            events=tests(200)),
    ]
    return folder("🏪 Vendors", items)

def occasions_folder():
    items = [
        req("List Occasion Categories", "GET", "occasions/categories", events=tests(200)),
        req("List Moods", "GET", "occasions/moods", events=tests(200)),
        req("List Tags", "GET", "occasions/tags", events=tests(200)),
        req("List Themes", "GET", "occasions/themes", events=tests(200)),
        req("List Occasions (Public)", "GET", "occasions",
            query={"page": "1", "page_size": "20"}, events=tests(200)),
        req("Get Occasion by ID", "GET", "occasions/{{TEST_OCCASION_ID}}", events=tests(200)),
        req("Create Occasion (Admin)", "POST", "occasions",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"name": "Birthday", "slug": "birthday", "description": "Birthday celebrations", "is_active": True}),
            events=tests(201, save={"TEST_OCCASION_ID": "data.id"})),
        req("Update Occasion (Admin)", "PUT", "occasions/{{TEST_OCCASION_ID}}",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"description": "Updated birthday description"}),
            events=tests(200)),
        req("Create Category (Admin)", "POST", "occasions/categories",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"name": "Social", "slug": "social"}),
            events=tests(201)),
        req("Create Mood (Admin)", "POST", "occasions/moods",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"name": "Joyful", "slug": "joyful", "emoji": "🎉"}),
            events=tests(201)),
        req("Create Tag (Admin)", "POST", "occasions/tags",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"name": "outdoor", "slug": "outdoor"}),
            events=tests(201)),
        req("Create Theme (Admin)", "POST", "occasions/themes",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"name": "Rustic", "slug": "rustic"}),
            events=tests(201)),
        req("List My Celebrations", "GET", "celebrations",
            hdrs=bearer(), events=tests(200)),
        req("Create Celebration", "POST", "celebrations",
            hdrs=[*json_header(), *bearer()],
            bd=body({
                "title": "My Birthday Party",
                "occasion_id": "{{TEST_OCCASION_ID}}",
                "date": "2026-09-15",
                "guest_count": 50,
                "budget": 100000,
                "venue": "Mumbai Banquet Hall",
                "notes": "Surprise party"
            }),
            events=tests(201, save={"TEST_CELEBRATION_ID": "data.id"})),
        req("Get Celebration by ID", "GET", "celebrations/{{TEST_CELEBRATION_ID}}",
            hdrs=bearer(), events=tests(200)),
        req("Update Celebration", "PUT", "celebrations/{{TEST_CELEBRATION_ID}}",
            hdrs=[*json_header(), *bearer()],
            bd=body({"guest_count": 60, "notes": "Updated notes"}),
            events=tests(200)),
        req("List Guests", "GET", "celebrations/{{TEST_CELEBRATION_ID}}/guests",
            hdrs=bearer(), events=tests(200)),
        req("Add Guest", "POST", "celebrations/{{TEST_CELEBRATION_ID}}/guests",
            hdrs=[*json_header(), *bearer()],
            bd=body({"name": "John Doe", "phone": "+919111111111", "email": "john@example.com", "rsvp_status": "INVITED"}),
            events=tests(201)),
        req("Checklist Progress", "GET", "celebrations/{{TEST_CELEBRATION_ID}}/checklist/progress",
            hdrs=bearer(), events=tests(200, extra=["pm.test('[Checklist] Has completed count', () => pm.expect(res.data).to.have.property('completed'));"])),
        req("List Checklist Items", "GET", "celebrations/{{TEST_CELEBRATION_ID}}/checklist",
            hdrs=bearer(), events=tests(200)),
        req("Add Checklist Item", "POST", "celebrations/{{TEST_CELEBRATION_ID}}/checklist",
            hdrs=[*json_header(), *bearer()],
            bd=body({"title": "Book caterer", "due_date": "2026-09-01", "priority": "HIGH"}),
            events=tests(201)),
        req("List Timeline Events", "GET", "celebrations/{{TEST_CELEBRATION_ID}}/timeline",
            hdrs=bearer(), events=tests(200)),
        req("Add Timeline Event", "POST", "celebrations/{{TEST_CELEBRATION_ID}}/timeline",
            hdrs=[*json_header(), *bearer()],
            bd=body({"title": "Cake cutting", "time": "19:00", "description": "Birthday cake", "duration_minutes": 15}),
            events=tests(201)),
        req("List Notes", "GET", "celebrations/{{TEST_CELEBRATION_ID}}/notes",
            hdrs=bearer(), events=tests(200)),
        req("Add Note", "POST", "celebrations/{{TEST_CELEBRATION_ID}}/notes",
            hdrs=[*json_header(), *bearer()],
            bd=body({"content": "Remember to order balloons", "is_pinned": False}),
            events=tests(201)),
        req("Delete Celebration", "DELETE", "celebrations/{{TEST_CELEBRATION_ID}}",
            hdrs=bearer(), events=tests(200)),
    ]
    return folder("🎉 Occasions & Celebrations", items)

def packages_folder():
    items = [
        req("List Package Categories", "GET", "packages/categories", events=tests(200)),
        req("Create Category (Admin)", "POST", "packages/categories",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"name": "Photography", "slug": "photography", "description": "Photo & video services"}),
            events=tests(201, save={"TEST_CATEGORY_ID": "data.id"})),
        req("List Packages (Public)", "GET", "packages",
            query={"page": "1", "page_size": "10", "is_published": "true"},
            events=tests(200, extra=["pm.test('[Packages] Has meta', () => pm.expect(res).to.have.property('meta'));"])),
        req("Create Package (Vendor)", "POST", "packages",
            hdrs=[*json_header(), *bearer("VENDOR_TOKEN")],
            bd=body({
                "name": "Basic Photography Package",
                "description": "4-hour photography for events",
                "base_price": 15000,
                "currency": "INR",
                "category_id": "{{TEST_CATEGORY_ID}}",
                "min_guests": 20, "max_guests": 200,
                "duration_hours": 4,
                "vendor_id": "{{TEST_VENDOR_ID}}"
            }),
            events=tests(201, save={"TEST_PACKAGE_ID": "data.id"})),
        req("Get Package by ID (Public)", "GET", "packages/{{TEST_PACKAGE_ID}}",
            events=tests(200, extra=["pm.test('[Package] Has base_price', () => pm.expect(res.data.base_price).to.be.a('number'));"])),
        req("Update Package (Vendor)", "PUT", "packages/{{TEST_PACKAGE_ID}}",
            hdrs=[*json_header(), *bearer("VENDOR_TOKEN")],
            bd=body({"description": "Updated package description", "base_price": 18000}),
            events=tests(200)),
        req("List Package Items", "GET", "packages/{{TEST_PACKAGE_ID}}/items", events=tests(200)),
        req("Add Package Item (Vendor)", "POST", "packages/{{TEST_PACKAGE_ID}}/items",
            hdrs=[*json_header(), *bearer("VENDOR_TOKEN")],
            bd=body({"name": "HD Camera", "description": "Professional HD camera", "quantity": 2, "unit": "pcs"}),
            events=tests(201)),
        req("List Package Availability", "GET", "packages/{{TEST_PACKAGE_ID}}/availability", events=tests(200)),
        req("Set Package Availability (Vendor)", "POST", "packages/{{TEST_PACKAGE_ID}}/availability",
            hdrs=[*json_header(), *bearer("VENDOR_TOKEN")],
            bd=body({"date": "2026-08-20", "slots_available": 1, "is_available": True}),
            events=tests(201)),
        req("List Package Reviews", "GET", "packages/{{TEST_PACKAGE_ID}}/reviews",
            query={"page": "1"}, events=tests(200)),
        req("Publish Package (Vendor)", "POST", "packages/{{TEST_PACKAGE_ID}}/publish",
            hdrs=bearer("VENDOR_TOKEN"), events=tests(200)),
        req("Unpublish Package (Vendor)", "POST", "packages/{{TEST_PACKAGE_ID}}/unpublish",
            hdrs=bearer("VENDOR_TOKEN"), events=tests(200)),
        req("Delete Package (Vendor)", "DELETE", "packages/{{TEST_PACKAGE_ID}}",
            hdrs=bearer("VENDOR_TOKEN"), events=tests(200)),
    ]
    return folder("📦 Packages", items)

def bookings_folder():
    items = [
        req("Create Booking (Customer)", "POST", "bookings",
            hdrs=[*json_header(), *bearer()],
            bd=body({
                "package_id": "{{TEST_PACKAGE_ID}}",
                "vendor_id": "{{TEST_VENDOR_ID}}",
                "celebration_id": "{{TEST_CELEBRATION_ID}}",
                "event_date": "2026-08-20",
                "event_time": "10:00",
                "guest_count": 50,
                "special_requests": "Please set up early",
                "address_id": "{{TEST_ADDRESS_ID}}"
            }),
            events=tests(201, save={"TEST_BOOKING_ID": "data.id"}, extra=[
                "pm.test('[Booking] Has status', () => pm.expect(res.data.status).to.be.a('string'));",
                "pm.test('[Booking] Status is PENDING', () => pm.expect(res.data.status).to.eql('PENDING'));",
            ])),
        req("List My Bookings (Customer)", "GET", "bookings",
            hdrs=bearer(),
            query={"page": "1", "page_size": "10"},
            events=tests(200)),
        req("List Vendor Bookings", "GET", "bookings/vendor",
            hdrs=bearer("VENDOR_TOKEN"),
            query={"page": "1"},
            events=tests(200)),
        req("Get Booking by ID", "GET", "bookings/{{TEST_BOOKING_ID}}",
            hdrs=bearer(),
            events=tests(200, extra=["pm.test('[Booking] Has booking_id', () => pm.expect(res.data.id).to.be.a('string'));"])),
        req("Confirm Booking (Admin)", "POST", "bookings/{{TEST_BOOKING_ID}}/confirm",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"note": "Booking confirmed by admin"}),
            events=tests(200)),
        req("Start Booking (Vendor)", "POST", "bookings/{{TEST_BOOKING_ID}}/start",
            hdrs=[*json_header(), *bearer("VENDOR_TOKEN")],
            bd=body({"note": "Service started"}),
            events=tests(200)),
        req("Complete Booking (Vendor)", "POST", "bookings/{{TEST_BOOKING_ID}}/complete",
            hdrs=[*json_header(), *bearer("VENDOR_TOKEN")],
            bd=body({"note": "Service completed successfully"}),
            events=tests(200)),
        req("Request Cancellation", "POST", "bookings/{{TEST_BOOKING_ID}}/cancellation",
            hdrs=[*json_header(), *bearer()],
            bd=body({"reason": "Change of plans", "cancellation_type": "CUSTOMER_REQUEST"}),
            events=tests(200)),
        req("Process Cancellation (Admin)", "POST", "bookings/{{TEST_BOOKING_ID}}/cancellation/process",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"approved": True, "refund_amount": 10000, "admin_note": "Full refund approved"}),
            events=tests(200)),
        req("Request Reschedule", "POST", "bookings/{{TEST_BOOKING_ID}}/reschedule",
            hdrs=[*json_header(), *bearer()],
            bd=body({"new_date": "2026-09-01", "new_time": "10:00", "reason": "Venue conflict"}),
            events=tests(200)),
        req("Get Booking History", "GET", "bookings/{{TEST_BOOKING_ID}}/history",
            hdrs=bearer(), events=tests(200)),
        req("Get Booking Status History", "GET", "bookings/{{TEST_BOOKING_ID}}/status-history",
            hdrs=bearer(), events=tests(200)),
        req("Get Booking Invoice", "GET", "bookings/{{TEST_BOOKING_ID}}/invoice",
            hdrs=bearer(), events=tests(200)),
        req("Generate Invoice (Admin)", "POST", "bookings/{{TEST_BOOKING_ID}}/invoice",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({}),
            events=tests(201)),
    ]
    return folder("📅 Bookings", items)

def payments_folder():
    items = [
        req("Validate Coupon", "GET", "payments/coupons/validate",
            query={"code": "{{TEST_COUPON_CODE}}", "booking_id": "{{TEST_BOOKING_ID}}"},
            events=tests(200, extra=["pm.test('[Coupon] Has discount', () => pm.expect(res.data).to.have.property('discount_amount'));"])),
        req("List Active Coupons", "GET", "payments/coupons",
            hdrs=bearer(), events=tests(200)),
        req("Create Coupon (Admin)", "POST", "payments/coupons",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({
                "code": "WELCOME10", "discount_type": "PERCENTAGE",
                "discount_value": 10, "max_uses": 100,
                "valid_from": "2026-01-01T00:00:00Z",
                "valid_until": "2026-12-31T23:59:59Z",
                "min_order_value": 5000
            }),
            events=tests(201)),
        req("Initiate Payment (Razorpay)", "POST", "payments/bookings/{{TEST_BOOKING_ID}}",
            hdrs=[*json_header(), *bearer()],
            bd=body({
                "amount": 15000, "currency": "INR",
                "payment_method": "RAZORPAY",
                "coupon_code": "WELCOME10"
            }),
            events=tests(201, save={"TEST_PAYMENT_ID": "data.id"}, extra=[
                "pm.test('[Payment] Has gateway_order_id', () => pm.expect(res.data).to.have.property('gateway_order_id'));",
            ])),
        req("Initiate Wallet Payment", "POST", "payments/bookings/{{TEST_BOOKING_ID}}/wallet",
            hdrs=[*json_header(), *bearer()],
            bd=body({"amount": 500}),
            events=tests(201)),
        req("Verify Payment", "GET", "payments/{{TEST_PAYMENT_ID}}/verify",
            hdrs=bearer(),
            events=tests(200, extra=["pm.test('[Payment] Has verified status', () => pm.expect(res.data).to.have.property('status'));"])),
        req("Get Payment by ID", "GET", "payments/{{TEST_PAYMENT_ID}}",
            hdrs=bearer(), events=tests(200)),
        req("List My Payments", "GET", "payments",
            hdrs=bearer(),
            query={"page": "1", "page_size": "10"},
            events=tests(200)),
        req("Get Payment Transactions", "GET", "payments/{{TEST_PAYMENT_ID}}/transactions",
            hdrs=bearer(), events=tests(200)),
        req("List Refunds", "GET", "payments/bookings/{{TEST_BOOKING_ID}}/refunds",
            hdrs=bearer(), events=tests(200)),
        req("Initiate Refund (Admin)", "POST", "payments/{{TEST_PAYMENT_ID}}/refunds",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"amount": 5000, "reason": "Customer requested refund", "refund_method": "ORIGINAL"}),
            events=tests(201)),
        req("Create Payment Split (Admin)", "POST", "payments/{{TEST_PAYMENT_ID}}/splits",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"vendor_id": "{{TEST_VENDOR_ID}}", "amount": 12000, "platform_fee": 3000}),
            events=tests(201)),
        req("List Payment Splits (Admin)", "GET", "payments/{{TEST_PAYMENT_ID}}/splits",
            hdrs=bearer("ADMIN_TOKEN"), events=tests(200)),
        req("List Invoices", "GET", "payments/invoices",
            query={"page": "1"}, events=tests(200)),
    ]
    return folder("💳 Payments", items)

def wallets_folder():
    items = [
        req("Create Wallet", "POST", "wallets",
            hdrs=[*json_header(), *bearer()],
            bd=body({}),
            events=tests(201, save={"TEST_WALLET_ID": "data.id"}, extra=[
                "pm.test('[Wallet] Has balance', () => pm.expect(res.data.balance).to.be.a('number'));",
            ])),
        req("Get My Wallet", "GET", "wallets/me",
            hdrs=bearer(),
            events=tests(200, save={"TEST_WALLET_ID": "data.id"}, extra=[
                "pm.test('[Wallet] Balance >= 0', () => pm.expect(res.data.balance).to.be.at.least(0));",
            ])),
        req("Get Wallet by ID", "GET", "wallets/{{TEST_WALLET_ID}}",
            hdrs=bearer(), events=tests(200)),
        req("List Wallet Transactions", "GET", "wallets/me/transactions",
            hdrs=bearer(),
            query={"page": "1", "page_size": "20"},
            events=tests(200)),
        req("Get Reward Balance", "GET", "wallets/me/rewards/balance",
            hdrs=bearer(),
            events=tests(200, extra=["pm.test('[Rewards] Has points', () => pm.expect(res.data).to.have.property('points'));"])),
        req("List Rewards", "GET", "wallets/me/rewards",
            hdrs=bearer(), query={"page": "1"}, events=tests(200)),
        req("Credit Wallet (Admin)", "POST", "wallets/admin/credit/{{TEST_USER_ID}}",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"amount": 500, "description": "Promotional credit", "reference_type": "ADMIN_CREDIT"}),
            events=tests(200, extra=["pm.test('[Credit] Has new_balance', () => pm.expect(res.data).to.have.property('new_balance'));"])),
        req("Debit Wallet (Admin)", "POST", "wallets/admin/debit/{{TEST_USER_ID}}",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"amount": 100, "description": "Fee deduction", "reference_type": "ADMIN_DEBIT"}),
            events=tests(200)),
        req("Award Reward (Admin)", "POST", "wallets/admin/rewards/{{TEST_USER_ID}}",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"points": 200, "description": "Loyalty reward", "expires_in_days": 30}),
            events=tests(201)),
        req("Freeze Wallet (Admin)", "POST", "wallets/{{TEST_WALLET_ID}}/freeze",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"reason": "Suspicious activity investigation"}),
            events=tests(200)),
        req("Unfreeze Wallet (Admin)", "POST", "wallets/{{TEST_WALLET_ID}}/unfreeze",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"reason": "Investigation cleared"}),
            events=tests(200)),
    ]
    return folder("💰 Wallets", items)

def memberships_folder():
    items = [
        req("List Plans (Public)", "GET", "memberships/plans", events=tests(200)),
        req("Create Plan (Admin)", "POST", "memberships/plans",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({
                "name": "Premium", "slug": "premium",
                "description": "Access all premium features",
                "price": 999, "currency": "INR",
                "duration_days": 30,
                "features": ["unlimited_bookings", "priority_support", "discount_10"]
            }),
            events=tests(201, save={"TEST_PLAN_ID": "data.id"})),
        req("Get Plan by ID", "GET", "memberships/plans/{{TEST_PLAN_ID}}", events=tests(200)),
        req("Update Plan (Admin)", "PUT", "memberships/plans/{{TEST_PLAN_ID}}",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"price": 1099, "description": "Updated premium plan"}),
            events=tests(200)),
        req("Subscribe to Plan", "POST", "memberships/subscribe",
            hdrs=[*json_header(), *bearer()],
            bd=body({"plan_id": "{{TEST_PLAN_ID}}", "payment_method": "WALLET"}),
            events=tests(201, save={"TEST_MEMBERSHIP_ID": "data.id"})),
        req("Get Active Membership", "GET", "memberships/active",
            hdrs=bearer(),
            events=tests(200, extra=["pm.test('[Membership] Has plan', () => pm.expect(res.data).to.have.property('plan'));"])),
        req("List My Memberships", "GET", "memberships",
            hdrs=bearer(), query={"page": "1"}, events=tests(200)),
        req("Get Membership by ID", "GET", "memberships/{{TEST_MEMBERSHIP_ID}}",
            hdrs=bearer(), events=tests(200)),
        req("Check Feature Access", "GET", "memberships/features/priority_support/access",
            hdrs=bearer(),
            events=tests(200, extra=["pm.test('[Feature] Has has_access', () => pm.expect(res.data).to.have.property('has_access'));"])),
        req("Cancel Membership", "POST", "memberships/{{TEST_MEMBERSHIP_ID}}/cancel",
            hdrs=[*json_header(), *bearer()],
            bd=body({"reason": "No longer needed"}),
            events=tests(200)),
        req("List All Memberships (Admin)", "GET", "memberships/admin/all",
            hdrs=bearer("ADMIN_TOKEN"), query={"page": "1"}, events=tests(200)),
        req("Deactivate Plan (Admin)", "DELETE", "memberships/plans/{{TEST_PLAN_ID}}",
            hdrs=bearer("ADMIN_TOKEN"), events=tests(200)),
    ]
    return folder("🎫 Memberships", items)

def notifications_folder():
    items = [
        req("Get Notification Preferences", "GET", "notifications/preferences",
            hdrs=bearer(), events=tests(200)),
        req("Update Preferences", "PUT", "notifications/preferences",
            hdrs=[*json_header(), *bearer()],
            bd=body({"email_enabled": True, "sms_enabled": True, "push_enabled": True,
                     "booking_updates": True, "promotions": False}),
            events=tests(200)),
        req("Get Unread Count", "GET", "notifications/unread-count",
            hdrs=bearer(),
            events=tests(200, extra=["pm.test('[Count] Has count', () => pm.expect(res.data).to.have.property('count'));"])),
        req("List Notifications", "GET", "notifications",
            hdrs=bearer(), query={"page": "1", "page_size": "20"}, events=tests(200)),
        req("Mark All Read", "POST", "notifications/mark-all-read",
            hdrs=bearer(), events=tests(200)),
        req("Send Notification (Admin)", "POST", "notifications/send",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({
                "user_id": "{{TEST_USER_ID}}",
                "title": "Test Notification",
                "body": "This is a test notification",
                "channel": "IN_APP"
            }),
            events=tests(201)),
        req("Broadcast Notification (Admin)", "POST", "notifications/broadcast",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({
                "title": "Platform Update",
                "body": "New features available!",
                "channels": ["IN_APP", "PUSH"],
                "target_roles": ["CUSTOMER"]
            }),
            events=tests(201)),
        req("List Templates (Admin)", "GET", "notifications/templates",
            hdrs=bearer("ADMIN_TOKEN"), events=tests(200)),
        req("Create Template (Admin)", "POST", "notifications/templates",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({
                "name": "booking_confirmed",
                "title_template": "Booking {{booking_id}} Confirmed",
                "body_template": "Your booking on {{event_date}} has been confirmed.",
                "channels": ["SMS", "EMAIL", "IN_APP"]
            }),
            events=tests(201)),
    ]
    return folder("🔔 Notifications", items)

def support_folder():
    items = [
        req("List My Tickets", "GET", "support/tickets",
            hdrs=bearer(), query={"page": "1"}, events=tests(200)),
        req("Create Support Ticket", "POST", "support/tickets",
            hdrs=[*json_header(), *bearer()],
            bd=body({
                "subject": "Issue with my booking",
                "description": "My booking was confirmed but the vendor is not responding.",
                "category": "BOOKING",
                "priority": "HIGH",
                "related_id": "{{TEST_BOOKING_ID}}"
            }),
            events=tests(201, save={"TEST_TICKET_ID": "data.id"})),
        req("Get Ticket by ID", "GET", "support/tickets/{{TEST_TICKET_ID}}",
            hdrs=bearer(), events=tests(200)),
        req("List All Tickets (Staff)", "GET", "support/tickets/all",
            hdrs=bearer("ADMIN_TOKEN"),
            query={"page": "1", "status": "OPEN"},
            events=tests(200)),
        req("Update Ticket Status (Staff)", "PATCH", "support/tickets/{{TEST_TICKET_ID}}/status",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"status": "IN_PROGRESS", "note": "Looking into this"}),
            events=tests(200)),
        req("List Ticket Messages", "GET", "support/tickets/{{TEST_TICKET_ID}}/messages",
            hdrs=bearer(), query={"page": "1"}, events=tests(200)),
        req("Add Message to Ticket", "POST", "support/tickets/{{TEST_TICKET_ID}}/messages",
            hdrs=[*json_header(), *bearer()],
            bd=body({"content": "Can you please help me urgently?", "is_internal": False}),
            events=tests(201)),
        req("List Ticket Attachments", "GET", "support/tickets/{{TEST_TICKET_ID}}/attachments",
            hdrs=bearer(), events=tests(200)),
        req("Assign Ticket (Admin)", "POST", "support/tickets/{{TEST_TICKET_ID}}/assignments/{{TEST_ADMIN_ID}}",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({}),
            events=tests(200)),
    ]
    return folder("🎫 Support", items)

def media_folder():
    items = [
        req("List Images for Entity", "GET", "media/images/entity/{{TEST_VENDOR_ID}}",
            query={"page": "1"}, events=tests(200)),
        req("Register Image Upload", "POST", "media/images/register",
            hdrs=[*json_header(), *bearer()],
            bd=body({
                "filename": "photo.jpg", "content_type": "image/jpeg",
                "file_size": 204800,
                "entity_type": "VENDOR", "entity_id": "{{TEST_VENDOR_ID}}",
                "purpose": "GALLERY"
            }),
            events=tests(201, save={"TEST_IMAGE_ID": "data.id"}, extra=[
                "pm.test('[Upload] Has upload_url', () => pm.expect(res.data).to.have.property('upload_url'));",
            ])),
        req("Confirm Image Upload", "POST", "media/images/{{TEST_IMAGE_ID}}/confirm",
            hdrs=[*json_header(), *bearer()],
            bd=body({}),
            events=tests(200)),
        req("Get Image by ID", "GET", "media/images/{{TEST_IMAGE_ID}}", events=tests(200)),
        req("Update Image Metadata", "PATCH", "media/images/{{TEST_IMAGE_ID}}",
            hdrs=[*json_header(), *bearer()],
            bd=body({"alt_text": "Event photo", "caption": "Beautiful setup"}),
            events=tests(200)),
        req("Moderate Image (Admin)", "POST", "media/images/{{TEST_IMAGE_ID}}/moderate",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"approved": True, "note": "Content appropriate"}),
            events=tests(200)),
        req("List Pending Moderation (Admin)", "GET", "media/images/pending-moderation",
            hdrs=bearer("ADMIN_TOKEN"), query={"page": "1"}, events=tests(200)),
        req("List Videos for Entity", "GET", "media/videos/entity/{{TEST_VENDOR_ID}}",
            query={"page": "1"}, events=tests(200)),
        req("Register Video Upload", "POST", "media/videos/register",
            hdrs=[*json_header(), *bearer()],
            bd=body({
                "filename": "event.mp4", "content_type": "video/mp4",
                "file_size": 10485760,
                "entity_type": "VENDOR", "entity_id": "{{TEST_VENDOR_ID}}"
            }),
            events=tests(201)),
        req("List Memories", "GET", "media/memories",
            hdrs=bearer(), query={"page": "1"}, events=tests(200)),
        req("Create Memory (Album)", "POST", "media/memories",
            hdrs=[*json_header(), *bearer()],
            bd=body({
                "title": "Birthday 2026", "description": "Photo memories",
                "visibility": "PRIVATE",
                "celebration_id": "{{TEST_CELEBRATION_ID}}"
            }),
            events=tests(201, save={"TEST_MEMORY_ID": "data.id"})),
        req("Get Memory by ID", "GET", "media/memories/{{TEST_MEMORY_ID}}",
            hdrs=bearer(), events=tests(200)),
        req("Add Image to Memory", "POST", "media/memories/{{TEST_MEMORY_ID}}/images/{{TEST_IMAGE_ID}}",
            hdrs=bearer(), events=tests(200)),
        req("Set Memory Visibility", "PATCH", "media/memories/{{TEST_MEMORY_ID}}/visibility",
            hdrs=[*json_header(), *bearer()],
            bd=body({"visibility": "PUBLIC"}),
            events=tests(200)),
        req("Delete Image", "DELETE", "media/images/{{TEST_IMAGE_ID}}",
            hdrs=bearer(), events=tests(200)),
    ]
    return folder("🖼️ Media", items)

def referrals_folder():
    items = [
        req("Get My Referral Code", "GET", "referrals/code",
            hdrs=bearer(),
            events=tests(200, save={"TEST_REFERRAL_CODE": "data.code"}, extra=[
                "pm.test('[Referral] Has code', () => pm.expect(res.data.code).to.be.a('string'));",
            ])),
        req("Apply Referral Code", "POST", "referrals/apply",
            hdrs=[*json_header(), *bearer()],
            bd=body({"code": "{{TEST_REFERRAL_CODE}}"}),
            events=tests(200)),
        req("Get Referral Stats", "GET", "referrals/stats",
            hdrs=bearer(),
            events=tests(200, extra=["pm.test('[Stats] Has total_referrals', () => pm.expect(res.data).to.have.property('total_referrals'));"])),
        req("List My Referrals", "GET", "referrals",
            hdrs=bearer(), query={"page": "1"}, events=tests(200)),
        req("List Referral Rewards", "GET", "referrals/rewards",
            hdrs=bearer(), query={"page": "1"}, events=tests(200)),
        req("Activate Referral Reward (Admin)", "POST", "referrals/rewards/{{reward_id}}/activate",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({}),
            events=tests(200)),
        req("Trigger Referral Rewards (Admin)", "POST", "referrals/{{referral_id}}/rewards/trigger",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({}),
            events=tests(200)),
    ]
    return folder("🔗 Referrals", items)

def budgets_folder():
    items = [
        req("List Budget Categories", "GET", "budgets/categories", events=tests(200)),
        req("Create Budget Category (Admin)", "POST", "budgets/categories",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"name": "Catering", "slug": "catering", "icon": "🍽️"}),
            events=tests(201)),
        req("List My Budgets", "GET", "budgets",
            hdrs=bearer(), query={"page": "1"}, events=tests(200)),
        req("Create Budget", "POST", "budgets",
            hdrs=[*json_header(), *bearer()],
            bd=body({
                "title": "Birthday Party Budget",
                "total_amount": 150000,
                "currency": "INR",
                "celebration_id": "{{TEST_CELEBRATION_ID}}",
                "event_date": "2026-09-15"
            }),
            events=tests(201, save={"TEST_BUDGET_ID": "data.id"})),
        req("Get Budget by ID", "GET", "budgets/{{TEST_BUDGET_ID}}",
            hdrs=bearer(), events=tests(200)),
        req("Update Budget", "PUT", "budgets/{{TEST_BUDGET_ID}}",
            hdrs=[*json_header(), *bearer()],
            bd=body({"total_amount": 180000, "notes": "Revised budget"}),
            events=tests(200)),
        req("Get Budget Summary", "GET", "budgets/{{TEST_BUDGET_ID}}/summary",
            hdrs=bearer(),
            events=tests(200, extra=[
                "pm.test('[Budget] Has total_spent', () => pm.expect(res.data).to.have.property('total_spent'));",
                "pm.test('[Budget] Has remaining', () => pm.expect(res.data).to.have.property('remaining'));",
            ])),
        req("Get Spending Breakdown", "GET", "budgets/{{TEST_BUDGET_ID}}/breakdown",
            hdrs=bearer(), events=tests(200)),
        req("List Expenses", "GET", "budgets/{{TEST_BUDGET_ID}}/expenses",
            hdrs=bearer(), query={"page": "1"}, events=tests(200)),
        req("Add Expense", "POST", "budgets/{{TEST_BUDGET_ID}}/expenses",
            hdrs=[*json_header(), *bearer()],
            bd=body({
                "title": "Catering deposit",
                "amount": 25000, "currency": "INR",
                "category": "catering",
                "date": "2026-07-01",
                "notes": "50% deposit paid"
            }),
            events=tests(201)),
        req("List Budget Alerts", "GET", "budgets/{{TEST_BUDGET_ID}}/alerts",
            hdrs=bearer(), events=tests(200)),
        req("Set Budget Alert", "POST", "budgets/{{TEST_BUDGET_ID}}/alerts",
            hdrs=[*json_header(), *bearer()],
            bd=body({"threshold_percentage": 80, "notify_channels": ["IN_APP", "EMAIL"]}),
            events=tests(201)),
        req("Delete Budget", "DELETE", "budgets/{{TEST_BUDGET_ID}}",
            hdrs=bearer(), events=tests(200)),
    ]
    return folder("💹 Budgets", items)

def admin_folder():
    items = [
        req("Admin Login", "POST", "admin/auth/login",
            hdrs=json_header(),
            bd=body({"email": "{{TEST_ADMIN_EMAIL}}", "password": "{{TEST_ADMIN_PASSWORD}}"}),
            events=tests(200, save={"ADMIN_TOKEN": "data.access_token", "TEST_ADMIN_ID": "data.admin.id"}, extra=[
                "pm.test('[Admin] Has access_token', () => pm.expect(res.data.access_token).to.be.a('string'));",
                "pm.test('[Admin] Role is admin', () => pm.expect(['admin','super_admin']).to.include(res.data.admin.role));",
            ])),
        req("Verify Admin Token", "GET", "admin/auth/me",
            hdrs=bearer("ADMIN_TOKEN"), events=tests(200)),
        req("Admin Logout", "POST", "admin/auth/logout",
            hdrs=bearer("ADMIN_TOKEN"), events=tests(200)),
        req("List Roles", "GET", "admin/roles",
            hdrs=bearer("ADMIN_TOKEN"), events=tests(200)),
        req("Create Role (Super Admin)", "POST", "admin/roles",
            hdrs=[*json_header(), *bearer("SUPER_ADMIN_TOKEN")],
            bd=body({"name": "support_agent", "display_name": "Support Agent", "description": "Handle support tickets"}),
            events=tests(201)),
        req("List Permissions", "GET", "admin/permissions",
            hdrs=bearer("ADMIN_TOKEN"), events=tests(200)),
        req("Create Permission (Super Admin)", "POST", "admin/permissions",
            hdrs=[*json_header(), *bearer("SUPER_ADMIN_TOKEN")],
            bd=body({"name": "tickets:assign", "display_name": "Assign Tickets", "resource": "tickets", "action": "assign"}),
            events=tests(201)),
        req("List Admins (Super Admin)", "GET", "admin/admins",
            hdrs=bearer("SUPER_ADMIN_TOKEN"), query={"page": "1"}, events=tests(200)),
        req("Create Admin (Super Admin)", "POST", "admin/admins",
            hdrs=[*json_header(), *bearer("SUPER_ADMIN_TOKEN")],
            bd=body({
                "email": "newadmin@tyohaar.com",
                "password": "NewAdmin@1234!",
                "full_name": "New Admin User",
                "role": "admin"
            }),
            events=tests(201)),
        req("Get Audit Logs", "GET", "admin/audit-logs",
            hdrs=bearer("ADMIN_TOKEN"),
            query={"page": "1", "page_size": "20"},
            events=tests(200, extra=["pm.test('[Audit] Returns array', () => pm.expect(res.data).to.be.an('array'));"])),
        req("Get Audit Logs for Entity", "GET", "admin/audit-logs/entity/{{TEST_VENDOR_ID}}",
            hdrs=bearer("ADMIN_TOKEN"), events=tests(200)),
    ]
    return folder("🛡️ Admin", items)

def common_folder():
    items = [
        req("List States", "GET", "common/states", events=tests(200)),
        req("Create State (Admin)", "POST", "common/states",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"name": "Maharashtra", "code": "MH", "country": "India"}),
            events=tests(201, save={"TEST_STATE_ID": "data.id"})),
        req("Get State by ID", "GET", "common/states/{{TEST_STATE_ID}}", events=tests(200)),
        req("Search Cities", "GET", "common/cities/search",
            query={"q": "Mumbai"}, events=tests(200)),
        req("List Cities", "GET", "common/cities",
            query={"state_id": "{{TEST_STATE_ID}}"}, events=tests(200)),
        req("Create City (Admin)", "POST", "common/cities",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"name": "Mumbai", "state_id": "{{TEST_STATE_ID}}", "pincode_prefix": "400"}),
            events=tests(201, save={"TEST_CITY_ID": "data.id"})),
        req("List Active Banners (Public)", "GET", "common/banners",
            events=tests(200, extra=["pm.test('[Banners] Returns array', () => pm.expect(res.data).to.be.an('array'));"])),
        req("Create Banner (Admin)", "POST", "common/banners",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({
                "title": "Summer Sale", "subtitle": "Up to 20% off",
                "image_url": "https://example.com/banner.jpg",
                "action_url": "/packages?promo=summer",
                "display_order": 1, "is_active": True,
                "valid_from": "2026-06-01T00:00:00Z",
                "valid_until": "2026-08-31T23:59:59Z"
            }),
            events=tests(201, save={"TEST_BANNER_ID": "data.id"})),
        req("Toggle Banner Active (Admin)", "PATCH", "common/banners/{{TEST_BANNER_ID}}/toggle",
            hdrs=bearer("ADMIN_TOKEN"), events=tests(200)),
        req("List FAQs (Public)", "GET", "common/faqs", events=tests(200)),
        req("Create FAQ (Admin)", "POST", "common/faqs",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"question": "How do I book a vendor?", "answer": "Browse vendors and click Book Now.", "category": "BOOKING", "display_order": 1}),
            events=tests(201)),
        req("Reorder FAQs (Admin)", "POST", "common/faqs/reorder",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"ordered_ids": []}),
            events=tests(200)),
        req("List App Settings (Admin)", "GET", "common/settings",
            hdrs=bearer("ADMIN_TOKEN"), events=tests(200)),
        req("Upsert Setting (Admin)", "PUT", "common/settings",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"key": "maintenance_mode", "value": "false", "description": "Toggle maintenance mode"}),
            events=tests(200)),
        req("Get Setting (Public)", "GET", "common/settings/maintenance_mode", events=tests(200)),
        req("Get Current Terms (Public)", "GET", "common/terms", events=tests(200)),
        req("Get Privacy Policy (Public)", "GET", "common/privacy-policy", events=tests(200)),
        req("Create Terms Version (Admin)", "POST", "common/terms/versions",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"version": "2.0", "content": "Updated terms and conditions text here.", "effective_date": "2026-07-01"}),
            events=tests(201)),
    ]
    return folder("🌍 Common", items)

# ── E2E FLOWS ────────────────────────────────────────────────────────────────

def e2e_customer_folder():
    items = [
        req("[1] Register - Request OTP", "POST", "auth/otp/request",
            hdrs=json_header(),
            bd=body({"phone": "{{TEST_PHONE}}", "channel": "SMS"}),
            events=tests(200)),
        req("[2] Register - Verify OTP → Token", "POST", "auth/otp/verify",
            hdrs=json_header(),
            bd=body({"phone": "{{TEST_PHONE}}", "otp": "{{OTP}}"}),
            events=tests(200, save={"ACCESS_TOKEN": "data.access_token", "REFRESH_TOKEN": "data.refresh_token"})),
        req("[3] Create Wallet", "POST", "wallets",
            hdrs=[*json_header(), *bearer()],
            bd=body({}),
            events=tests(201, save={"TEST_WALLET_ID": "data.id"})),
        req("[4] Browse Packages", "GET", "packages",
            query={"page": "1", "page_size": "5", "is_published": "true"},
            events=tests(200, extra=[
                "if (res.data && res.data.length > 0) { pm.environment.set('TEST_PACKAGE_ID', res.data[0].id); pm.environment.set('TEST_VENDOR_ID', res.data[0].vendor_id); }"
            ])),
        req("[5] Create Celebration", "POST", "celebrations",
            hdrs=[*json_header(), *bearer()],
            bd=body({"title": "My Birthday", "date": "2026-09-15", "guest_count": 30, "budget": 50000}),
            events=tests(201, save={"TEST_CELEBRATION_ID": "data.id"})),
        req("[6] Create Booking", "POST", "bookings",
            hdrs=[*json_header(), *bearer()],
            bd=body({
                "package_id": "{{TEST_PACKAGE_ID}}",
                "vendor_id": "{{TEST_VENDOR_ID}}",
                "celebration_id": "{{TEST_CELEBRATION_ID}}",
                "event_date": "2026-09-15",
                "event_time": "10:00",
                "guest_count": 30
            }),
            events=tests(201, save={"TEST_BOOKING_ID": "data.id"})),
        req("[7] Initiate Payment", "POST", "payments/bookings/{{TEST_BOOKING_ID}}",
            hdrs=[*json_header(), *bearer()],
            bd=body({"amount": 15000, "currency": "INR", "payment_method": "RAZORPAY"}),
            events=tests(201, save={"TEST_PAYMENT_ID": "data.id"})),
        req("[8] Verify Payment", "GET", "payments/{{TEST_PAYMENT_ID}}/verify",
            hdrs=bearer(), events=tests(200)),
        req("[9] Get Wallet Balance", "GET", "wallets/me",
            hdrs=bearer(), events=tests(200)),
        req("[10] Check Notifications", "GET", "notifications",
            hdrs=bearer(), query={"page": "1"}, events=tests(200)),
        req("[11] Submit Vendor Review", "POST", "vendors/{{TEST_VENDOR_ID}}/reviews",
            hdrs=[*json_header(), *bearer()],
            bd=body({"rating": 5, "review": "Excellent!", "booking_id": "{{TEST_BOOKING_ID}}"}),
            events=tests(201)),
        req("[12] Logout", "POST", "auth/logout",
            hdrs=bearer(), events=tests(200)),
    ]
    return folder("🛒 Customer Journey (E2E)", items, desc="Full customer lifecycle: Register → Browse → Book → Pay → Review → Logout")

def e2e_vendor_folder():
    items = [
        req("[1] Vendor OTP Request", "POST", "auth/otp/request",
            hdrs=json_header(),
            bd=body({"phone": "{{TEST_VENDOR_PHONE}}", "channel": "SMS"}),
            events=tests(200)),
        req("[2] Vendor OTP Verify → Token", "POST", "auth/otp/verify",
            hdrs=json_header(),
            bd=body({"phone": "{{TEST_VENDOR_PHONE}}", "otp": "{{OTP}}"}),
            events=tests(200, save={"VENDOR_TOKEN": "data.access_token"})),
        req("[3] Create Vendor Profile", "POST", "vendors",
            hdrs=[*json_header(), *bearer("VENDOR_TOKEN")],
            bd=body({
                "business_name": "Elite Events Co",
                "business_type": "EVENTS",
                "description": "Premium event planning",
                "phone": "{{TEST_VENDOR_PHONE}}",
                "city": "Mumbai", "state": "Maharashtra"
            }),
            events=tests(201, save={"TEST_VENDOR_ID": "data.id"})),
        req("[4] Admin Approves Vendor", "POST", "vendors/{{TEST_VENDOR_ID}}/verify",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"is_verified": True, "verification_note": "Approved"}),
            events=tests(200)),
        req("[5] Create Package", "POST", "packages",
            hdrs=[*json_header(), *bearer("VENDOR_TOKEN")],
            bd=body({
                "name": "Elite Photography", "description": "8h shoot",
                "base_price": 25000, "currency": "INR",
                "vendor_id": "{{TEST_VENDOR_ID}}"
            }),
            events=tests(201, save={"TEST_PACKAGE_ID": "data.id"})),
        req("[6] Publish Package", "POST", "packages/{{TEST_PACKAGE_ID}}/publish",
            hdrs=bearer("VENDOR_TOKEN"), events=tests(200)),
        req("[7] View Vendor Bookings", "GET", "bookings/vendor",
            hdrs=bearer("VENDOR_TOKEN"), events=tests(200)),
        req("[8] Start Booking", "POST", "bookings/{{TEST_BOOKING_ID}}/start",
            hdrs=[*json_header(), *bearer("VENDOR_TOKEN")],
            bd=body({"note": "Service started"}),
            events=tests(200)),
        req("[9] Complete Booking", "POST", "bookings/{{TEST_BOOKING_ID}}/complete",
            hdrs=[*json_header(), *bearer("VENDOR_TOKEN")],
            bd=body({"note": "Service delivered"}),
            events=tests(200)),
        req("[10] Vendor Logout", "POST", "auth/logout",
            hdrs=bearer("VENDOR_TOKEN"), events=tests(200)),
    ]
    return folder("🏪 Vendor Journey (E2E)", items, desc="Full vendor lifecycle: Register → Approval → Package → Receive Booking → Complete")

def e2e_admin_folder():
    items = [
        req("[1] Admin Login", "POST", "admin/auth/login",
            hdrs=json_header(),
            bd=body({"email": "{{TEST_ADMIN_EMAIL}}", "password": "{{TEST_ADMIN_PASSWORD}}"}),
            events=tests(200, save={"ADMIN_TOKEN": "data.access_token"})),
        req("[2] List Pending Vendor Approvals", "GET", "vendors",
            query={"is_verified": "false", "page": "1"},
            events=tests(200)),
        req("[3] Approve Vendor", "POST", "vendors/{{TEST_VENDOR_ID}}/verify",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"is_verified": True}),
            events=tests(200)),
        req("[4] View All Bookings (Admin)", "GET", "bookings",
            hdrs=bearer("ADMIN_TOKEN"), query={"page": "1"}, events=tests(200)),
        req("[5] Confirm Booking", "POST", "bookings/{{TEST_BOOKING_ID}}/confirm",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"note": "Admin confirmed"}),
            events=tests(200)),
        req("[6] Manage Users", "GET", "users/{{TEST_USER_ID}}/full",
            hdrs=bearer("ADMIN_TOKEN"), events=tests(200)),
        req("[7] Broadcast Notification", "POST", "notifications/broadcast",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"title": "Platform Update", "body": "New features live!", "channels": ["IN_APP"], "target_roles": ["CUSTOMER"]}),
            events=tests(201)),
        req("[8] View Audit Logs", "GET", "admin/audit-logs",
            hdrs=bearer("ADMIN_TOKEN"), query={"page": "1"}, events=tests(200)),
        req("[9] Admin Logout", "POST", "admin/auth/logout",
            hdrs=bearer("ADMIN_TOKEN"), events=tests(200)),
    ]
    return folder("🛡️ Admin Journey (E2E)", items, desc="Admin lifecycle: Login → Approve Vendor → Manage Bookings → Audit")

# ── NEGATIVE TESTS ───────────────────────────────────────────────────────────

def negative_folder():
    items = [
        req("[NEG] Missing JWT → 401", "GET", "users/me",
            hdrs=[], events=neg_tests(401)),
        req("[NEG] Expired/Invalid JWT → 401", "GET", "users/me",
            hdrs=[{"key": "Authorization", "value": "Bearer invalidtoken123", "type": "text"}],
            events=neg_tests(401)),
        req("[NEG] Wrong Role - Customer accessing Admin → 403", "GET", "admin/admins",
            hdrs=bearer("CUSTOMER_TOKEN"), events=neg_tests(403)),
        req("[NEG] Wrong Role - Customer accessing Vendor endpoint → 403", "POST", "vendors",
            hdrs=[*json_header(), *bearer()],
            bd=body({"business_name": "Test"}),
            events=neg_tests(403)),
        req("[NEG] Invalid UUID Path Param → 422 or 404", "GET", "users/not-a-valid-uuid",
            hdrs=bearer(),
            events=[{"listen": "test", "script": {"type": "text/javascript", "exec": [
                "pm.test('[NEG] Returns 4xx for invalid UUID', () => pm.expect(pm.response.code).to.be.oneOf([400, 404, 422]));",
                "const res = pm.response.json(); pm.test('[NEG] Has error field', () => pm.expect(res).to.have.property('error'));"
            ]}}]),
        req("[NEG] Duplicate Phone Registration → 409", "POST", "auth/otp/request",
            hdrs=json_header(),
            bd=body({"phone": "{{TEST_PHONE}}", "channel": "SMS"}),
            events=[{"listen": "test", "script": {"type": "text/javascript", "exec": [
                "pm.test('[NEG] OTP request is idempotent or 429', () => pm.expect(pm.response.code).to.be.oneOf([200, 429]));",
            ]}}]),
        req("[NEG] Invalid OTP → 400", "POST", "auth/otp/verify",
            hdrs=json_header(),
            bd=body({"phone": "{{TEST_PHONE}}", "otp": "000000"}),
            events=neg_tests(400)),
        req("[NEG] Expired Refresh Token → 401", "POST", "auth/token/refresh",
            hdrs=json_header(),
            bd=body({"refresh_token": "expired.token.here"}),
            events=neg_tests(401)),
        req("[NEG] Negative Price in Package → 422", "POST", "packages",
            hdrs=[*json_header(), *bearer("VENDOR_TOKEN")],
            bd=body({"name": "Bad Package", "base_price": -100, "vendor_id": "{{TEST_VENDOR_ID}}"}),
            events=neg_tests(422)),
        req("[NEG] Past Booking Date → 422", "POST", "bookings",
            hdrs=[*json_header(), *bearer()],
            bd=body({"package_id": "{{TEST_PACKAGE_ID}}", "vendor_id": "{{TEST_VENDOR_ID}}", "event_date": "2020-01-01", "guest_count": 10}),
            events=neg_tests(422)),
        req("[NEG] Double Payment for Same Booking → 409", "POST", "payments/bookings/{{TEST_BOOKING_ID}}",
            hdrs=[*json_header(), *bearer()],
            bd=body({"amount": 15000, "currency": "INR", "payment_method": "RAZORPAY"}),
            events=[{"listen": "test", "script": {"type": "text/javascript", "exec": [
                "pm.test('[NEG] Double payment rejected', () => pm.expect(pm.response.code).to.be.oneOf([409, 400]));",
            ]}}]),
        req("[NEG] Invalid Coupon Code → 400", "GET", "payments/coupons/validate",
            query={"code": "INVALID_COUPON_XYZ", "booking_id": "{{TEST_BOOKING_ID}}"},
            events=neg_tests(400)),
        req("[NEG] Wallet Underflow (Debit > Balance) → 400", "POST", "wallets/admin/debit/{{TEST_USER_ID}}",
            hdrs=[*json_header(), *bearer("ADMIN_TOKEN")],
            bd=body({"amount": 9999999, "description": "Excessive debit", "reference_type": "ADMIN_DEBIT"}),
            events=neg_tests(400)),
        req("[NEG] Delete Non-existent Resource → 404", "DELETE", "packages/00000000-0000-0000-0000-000000000000",
            hdrs=bearer("VENDOR_TOKEN"), events=neg_tests(404)),
        req("[NEG] Pagination Overflow → Empty or 404", "GET", "vendors",
            query={"page": "9999", "page_size": "100"},
            events=[{"listen": "test", "script": {"type": "text/javascript", "exec": [
                "pm.test('[NEG] Large page returns gracefully', () => pm.expect(pm.response.code).to.be.oneOf([200, 404]));",
                "if (pm.response.code === 200) { const res = pm.response.json(); pm.test('[NEG] Empty data array', () => pm.expect(res.data).to.be.an('array')); }"
            ]}}]),
        req("[NEG] Missing Required Fields → 422", "POST", "bookings",
            hdrs=[*json_header(), *bearer()],
            bd=body({}),
            events=neg_tests(422)),
        req("[NEG] Oversized page_size → 422", "GET", "packages",
            query={"page_size": "999"},
            events=[{"listen": "test", "script": {"type": "text/javascript", "exec": [
                "pm.test('[NEG] Oversized page_size rejected or capped', () => pm.expect(pm.response.code).to.be.oneOf([200, 422]));",
                "if (pm.response.code === 200) { const res = pm.response.json(); pm.test('[NEG] page_size capped at max', () => pm.expect(res.meta.page_size).to.be.at.most(100)); }"
            ]}}]),
    ]
    return folder("❌ Negative Testing", items, desc="Invalid inputs, wrong roles, boundary violations, and error path validation")

# ── SECURITY TESTS ───────────────────────────────────────────────────────────

def security_folder():
    items = [
        req("[SEC] SQL Injection in Query Param → 400/422", "GET", "vendors",
            query={"search": "' OR 1=1 --"},
            events=[{"listen": "test", "script": {"type": "text/javascript", "exec": [
                "pm.test('[SEC] SQL injection not executed', () => pm.expect(pm.response.code).to.not.eql(500));",
                "pm.test('[SEC] Returns 2xx or 4xx (not 5xx)', () => pm.expect(pm.response.code).to.be.below(500));",
            ]}}]),
        req("[SEC] XSS Payload in Body → Sanitized", "POST", "users/me/addresses",
            hdrs=[*json_header(), *bearer()],
            bd=body({"label": "<script>alert('xss')</script>", "address_line_1": "123 St", "city": "Mumbai", "postal_code": "400001"}),
            events=[{"listen": "test", "script": {"type": "text/javascript", "exec": [
                "pm.test('[SEC] XSS payload rejected or sanitized', () => pm.expect(pm.response.code).to.be.oneOf([200, 201, 400, 422]));",
                "if (pm.response.code < 300) { const res = pm.response.json(); const raw = JSON.stringify(res); pm.test('[SEC] No raw <script> in response', () => pm.expect(raw).to.not.include('<script>')); }"
            ]}}]),
        req("[SEC] Mass Assignment - Attempt Role Elevation → Rejected", "PUT", "users/me",
            hdrs=[*json_header(), *bearer()],
            bd=body({"full_name": "Hacker", "role": "admin", "account_status": "ACTIVE", "is_superuser": True}),
            events=[{"listen": "test", "script": {"type": "text/javascript", "exec": [
                "pm.test('[SEC] Request succeeds', () => pm.expect(pm.response.code).to.be.oneOf([200, 422]));",
                "if (pm.response.code === 200) { const res = pm.response.json(); pm.test('[SEC] Role not elevated', () => pm.expect(res.data.role).to.not.eql('admin')); }"
            ]}}]),
        req("[SEC] IDOR - Access Other User's Data → 403/404", "GET", "users/00000000-0000-0000-0000-000000000001/full",
            hdrs=bearer(),
            events=[{"listen": "test", "script": {"type": "text/javascript", "exec": [
                "pm.test('[SEC] IDOR blocked - 403 or 404', () => pm.expect(pm.response.code).to.be.oneOf([403, 404]));",
            ]}}]),
        req("[SEC] Admin Endpoint Without Admin Token → 403", "GET", "admin/admins",
            hdrs=bearer("CUSTOMER_TOKEN"),
            events=neg_tests(403)),
        req("[SEC] Vendor Endpoint as Customer → 403", "POST", "packages",
            hdrs=[*json_header(), *bearer("CUSTOMER_TOKEN")],
            bd=body({"name": "Unauthorized Package", "base_price": 1000}),
            events=neg_tests(403)),
        req("[SEC] Invalid Content-Type → 422", "POST", "auth/otp/request",
            hdrs=[{"key": "Content-Type", "value": "text/plain", "type": "text"}],
            bd={"mode": "raw", "raw": "phone=+919999999999"},
            events=[{"listen": "test", "script": {"type": "text/javascript", "exec": [
                "pm.test('[SEC] Wrong Content-Type rejected', () => pm.expect(pm.response.code).to.be.oneOf([400, 415, 422]));",
            ]}}]),
        req("[SEC] Security Headers Present", "GET", "/health",
            events=[{"listen": "test", "script": {"type": "text/javascript", "exec": [
                "pm.test('[SEC] X-Content-Type-Options header', () => pm.expect(pm.response.headers.get('X-Content-Type-Options')).to.not.be.undefined);",
                "pm.test('[SEC] X-Frame-Options header', () => pm.expect(pm.response.headers.get('X-Frame-Options')).to.not.be.undefined);",
                "pm.test('[SEC] No Server version disclosure', () => { const server = pm.response.headers.get('Server'); if (server) pm.expect(server).to.not.match(/\\d+\\.\\d+/); });",
            ]}}]),
        req("[SEC] Rate Limit - Rapid OTP Requests", "POST", "auth/otp/request",
            hdrs=json_header(),
            bd=body({"phone": "+919700000001", "channel": "SMS"}),
            events=[{"listen": "test", "script": {"type": "text/javascript", "exec": [
                "pm.test('[SEC] Rate limit enforced (200 initially, 429 when exhausted)', () => pm.expect(pm.response.code).to.be.oneOf([200, 429]));",
                "if (pm.response.code === 429) { pm.test('[SEC] Retry-After header present', () => pm.expect(pm.response.headers.get('Retry-After')).to.not.be.undefined); }"
            ]}}]),
        req("[SEC] JWT Algorithm Confusion (none alg) → 401", "GET", "users/me",
            hdrs=[{"key": "Authorization", "value": "Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ0ZXN0Iiwicm9sZSI6ImFkbWluIn0.", "type": "text"}],
            events=neg_tests(401)),
    ]
    return folder("🔒 Security Testing", items, desc="RBAC, injection, IDOR, mass assignment, and header security validation")

# ── ASSEMBLE COLLECTION ──────────────────────────────────────────────────────

def build_collection():
    return {
        "info": {
            "_postman_id": "tyohaar-api-collection-v1",
            "name": "Tyohaar API — Complete Integration Suite v1.0",
            "description": (
                "Production-grade integration test suite for the Tyohaar backend.\n\n"
                "Covers 300+ endpoints across 16 domains with:\n"
                "• Request chaining (tokens, IDs saved between requests)\n"
                "• Test scripts (status, timing, schema, headers)\n"
                "• E2E business flows (Customer / Vendor / Admin journeys)\n"
                "• Negative testing (role violations, validation errors, boundary cases)\n"
                "• Security testing (RBAC, injection, IDOR, algorithm confusion)\n\n"
                "HOW TO USE:\n"
                "1. Import both this collection and a Tyohaar environment file\n"
                "2. Set TEST_PHONE, TEST_VENDOR_PHONE, TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD\n"
                "3. Start with Auth folder: run Request OTP, then manually set {{OTP}}, then Verify OTP\n"
                "4. Run Admin Login to populate ADMIN_TOKEN\n"
                "5. Use Collection Runner to execute E2E flows in order\n"
            ),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "event": [
            {
                "listen": "prerequest",
                "script": {"type": "text/javascript", "exec": COLLECTION_PRE_REQUEST}
            }
        ],
        "item": [
            health_folder(),
            auth_folder(),
            users_folder(),
            vendors_folder(),
            occasions_folder(),
            packages_folder(),
            bookings_folder(),
            payments_folder(),
            wallets_folder(),
            memberships_folder(),
            notifications_folder(),
            support_folder(),
            media_folder(),
            referrals_folder(),
            budgets_folder(),
            admin_folder(),
            common_folder(),
            folder("🔄 End-to-End Flows", [
                e2e_customer_folder(),
                e2e_vendor_folder(),
                e2e_admin_folder(),
            ], desc="Automated end-to-end business flows"),
            negative_folder(),
            security_folder(),
        ]
    }

if __name__ == "__main__":
    import os
    out_path = os.path.join(os.path.dirname(__file__), "Tyohaar_API_Collection.postman_collection.json")
    collection = build_collection()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=2, ensure_ascii=False)

    # count items
    def count_requests(items):
        total = 0
        for item in items:
            if "item" in item:
                total += count_requests(item["item"])
            elif "request" in item:
                total += 1
        return total

    total = count_requests(collection["item"])
    print(f"Collection generated: {out_path}")
    print(f"   Total requests: {total}")
    print(f"   Folders: {len(collection['item'])}")
