import { Routes, Route, Navigate } from 'react-router-dom';
import { lazy, Suspense } from 'react';

// Marketing site components
import Navbar from './components/layout/Navbar.jsx';

// Unified workspace login (vendor + admin/staff — routes to the right portal by role)
const WorkspaceLoginPage = lazy(() => import('./workspace/pages/WorkspaceLoginPage.jsx'));

import Footer from './components/layout/Footer.jsx';
import Hero from './components/sections/Hero.jsx';
import Marquee from './components/sections/Marquee.jsx';
import Occasions from './components/sections/Occasions.jsx';
import HowItWorks from './components/sections/HowItWorks.jsx';
import PackageServices from './components/sections/PackageServices.jsx';
import Memories from './components/sections/Memories.jsx';
import Testimonials from './components/sections/Testimonials.jsx';
import CTA from './components/sections/CTA.jsx';

// Admin portal
import { AdminAuthProvider } from './admin/context/AuthContext.jsx';
import AdminLayout from './admin/components/layout/AdminLayout.jsx';
import '@/admin/admin.css';

// Vendor portal
import { VendorAuthProvider } from './vendor/context/VendorAuthContext.jsx';
import VendorLayout from './vendor/components/layout/VendorLayout.jsx';

// Vendor pages — lazy loaded
const VendorRegisterPage        = lazy(() => import('./vendor/pages/auth/VendorRegisterPage.jsx'));
const VendorForgotPasswordPage  = lazy(() => import('./vendor/pages/auth/VendorForgotPasswordPage.jsx'));
const VendorOverviewPage        = lazy(() => import('./vendor/pages/overview/VendorOverviewPage.jsx'));
const VendorProfilePage         = lazy(() => import('./vendor/pages/profile/VendorProfilePage.jsx'));
const VendorPackagesPage        = lazy(() => import('./vendor/pages/packages/VendorPackagesPage.jsx'));
const VendorBankPage            = lazy(() => import('./vendor/pages/bank/VendorBankPage.jsx'));
const VendorBookingsPage        = lazy(() => import('./vendor/pages/bookings/VendorBookingsPage.jsx'));
const VendorBookingDetailPage   = lazy(() => import('./vendor/pages/bookings/VendorBookingDetailPage.jsx'));
const VendorAvailabilityPage    = lazy(() => import('./vendor/pages/availability/VendorAvailabilityPage.jsx'));
const VendorEarningsPage        = lazy(() => import('./vendor/pages/earnings/VendorEarningsPage.jsx'));
const VendorReviewsPage         = lazy(() => import('./vendor/pages/reviews/VendorReviewsPage.jsx'));
const VendorNotificationsPage   = lazy(() => import('./vendor/pages/notifications/VendorNotificationsPage.jsx'));
const VendorSupportPage         = lazy(() => import('./vendor/pages/support/VendorSupportPage.jsx'));

// Admin pages — lazy loaded for code splitting
const DashboardPage         = lazy(() => import('./admin/pages/dashboard/DashboardPage.jsx'));
const VendorsPage           = lazy(() => import('./admin/pages/vendors/VendorsPage.jsx'));
const VendorDetailPage      = lazy(() => import('./admin/pages/vendors/VendorDetailPage.jsx'));
const CustomersPage         = lazy(() => import('./admin/pages/customers/CustomersPage.jsx'));
const CustomerDetailPage    = lazy(() => import('./admin/pages/customers/CustomerDetailPage.jsx'));
const BookingsPage          = lazy(() => import('./admin/pages/bookings/BookingsPage.jsx'));
const BookingDetailPage     = lazy(() => import('./admin/pages/bookings/BookingDetailPage.jsx'));
const PackagesPage          = lazy(() => import('./admin/pages/packages/PackagesPage.jsx'));
const PackageDetailPage     = lazy(() => import('./admin/pages/packages/PackageDetailPage.jsx'));
const PackageCategoriesPage = lazy(() => import('./admin/pages/packages/PackageCategoriesPage.jsx'));
const PaymentsPage          = lazy(() => import('./admin/pages/payments/PaymentsPage.jsx'));
const MembershipsPage       = lazy(() => import('./admin/pages/memberships/MembershipsPage.jsx'));
const OccasionsPage         = lazy(() => import('./admin/pages/occasions/OccasionsPage.jsx'));
const NotificationsPage     = lazy(() => import('./admin/pages/notifications/NotificationsPage.jsx'));
const SupportPage           = lazy(() => import('./admin/pages/support/SupportPage.jsx'));
const SupportDetailPage     = lazy(() => import('./admin/pages/support/SupportDetailPage.jsx'));
const FeedbackPage          = lazy(() => import('./admin/pages/feedback/FeedbackPage.jsx'));
const MediaPage             = lazy(() => import('./admin/pages/media/MediaPage.jsx'));
const AdminManagementPage   = lazy(() => import('./admin/pages/admin-mgmt/AdminManagementPage.jsx'));
const SettingsPage          = lazy(() => import('./admin/pages/settings/SettingsPage.jsx'));
const ImportExportPage      = lazy(() => import('./admin/pages/io/ImportExportPage.jsx'));
const AutomationPage        = lazy(() => import('./admin/pages/automation/AutomationPage.jsx'));
const GlobalSearchPage      = lazy(() => import('./admin/pages/search/GlobalSearchPage.jsx'));
const ReferralsPage         = lazy(() => import('./admin/pages/referrals/ReferralsPage.jsx'));

function MarketingSite() {
  return (
    <>
      <Navbar />
      <main id="top">
        <Hero />
        <Marquee />
        <Occasions />
        <HowItWorks />
        <PackageServices />
        <Memories />
        <Testimonials />
        <CTA />
      </main>
      <Footer />
    </>
  );
}

function AdminFallback() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: '#666' }}>
      <div className="spinner" style={{ width: 28, height: 28 }} />
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      {/* Marketing site */}
      <Route path="/" element={<MarketingSite />} />

      {/* Unified workspace login — routes to /vendor or /admin by role */}
      <Route
        path="/workspace/login"
        element={
          <Suspense fallback={<AdminFallback />}>
            <WorkspaceLoginPage />
          </Suspense>
        }
      />

      {/* Vendor portal */}
      <Route
        path="/vendor/*"
        element={
          <VendorAuthProvider>
            <Routes>
              <Route path="login" element={<Navigate to="/workspace/login" replace />} />
              <Route
                path="register"
                element={
                  <Suspense fallback={<AdminFallback />}>
                    <VendorRegisterPage />
                  </Suspense>
                }
              />
              <Route
                path="forgot-password"
                element={
                  <Suspense fallback={<AdminFallback />}>
                    <VendorForgotPasswordPage />
                  </Suspense>
                }
              />
              <Route element={<VendorLayout />}>
                <Route index element={<VendorOverviewPage />} />
                <Route path="profile" element={<VendorProfilePage />} />
                <Route path="packages" element={<VendorPackagesPage />} />
                <Route path="bank" element={<VendorBankPage />} />
                <Route path="bookings" element={<VendorBookingsPage />} />
                <Route path="bookings/:bookingId" element={<VendorBookingDetailPage />} />
                <Route path="availability" element={<VendorAvailabilityPage />} />
                <Route path="earnings" element={<VendorEarningsPage />} />
                <Route path="reviews" element={<VendorReviewsPage />} />
                <Route path="notifications" element={<VendorNotificationsPage />} />
                <Route path="support" element={<VendorSupportPage />} />
              </Route>
            </Routes>
          </VendorAuthProvider>
        }
      />

      {/* Admin portal */}
      <Route
        path="/admin/*"
        element={
          <AdminAuthProvider>
            <Routes>
              <Route path="login" element={<Navigate to="/workspace/login" replace />} />

              {/* Protected layout — AdminLayout owns the inner Suspense + AnimatePresence */}
              <Route element={<AdminLayout />}>
                <Route index element={<DashboardPage />} />
                <Route path="vendors" element={<VendorsPage />} />
                <Route path="vendors/:vendorId" element={<VendorDetailPage />} />
                <Route path="customers" element={<CustomersPage />} />
                <Route path="customers/:userId" element={<CustomerDetailPage />} />
                <Route path="bookings" element={<BookingsPage />} />
                <Route path="bookings/:bookingId" element={<BookingDetailPage />} />
                <Route path="packages" element={<PackagesPage />} />
                <Route path="packages/categories" element={<PackageCategoriesPage />} />
                <Route path="packages/:packageId" element={<PackageDetailPage />} />
                <Route path="payments" element={<PaymentsPage />} />
                <Route path="memberships" element={<MembershipsPage />} />
                <Route path="occasions" element={<OccasionsPage />} />
                <Route path="notifications" element={<NotificationsPage />} />
                <Route path="support" element={<SupportPage />} />
                <Route path="support/:id" element={<SupportDetailPage />} />
                <Route path="feedback" element={<FeedbackPage />} />
                <Route path="media" element={<MediaPage />} />
                <Route path="admin-management" element={<AdminManagementPage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="io" element={<ImportExportPage />} />
                <Route path="automation" element={<AutomationPage />} />
                <Route path="search" element={<GlobalSearchPage />} />
                <Route path="referrals" element={<ReferralsPage />} />
              </Route>
            </Routes>
          </AdminAuthProvider>
        }
      />
    </Routes>
  );
}
