import { Routes, Route } from 'react-router-dom';
import { lazy, Suspense } from 'react';

// Marketing site components
import Navbar from './components/layout/Navbar.jsx';
import Footer from './components/layout/Footer.jsx';
import Hero from './components/sections/Hero.jsx';
import Marquee from './components/sections/Marquee.jsx';
import Occasions from './components/sections/Occasions.jsx';
import HowItWorks from './components/sections/HowItWorks.jsx';
import PackageServices from './components/sections/PackageServices.jsx';
import Packages from './components/sections/Packages.jsx';
import Memories from './components/sections/Memories.jsx';
import Testimonials from './components/sections/Testimonials.jsx';
import CTA from './components/sections/CTA.jsx';

// Admin portal
import { AdminAuthProvider } from './admin/context/AuthContext.jsx';
import AdminLayout from './admin/components/layout/AdminLayout.jsx';
import '@/admin/admin.css';

// Admin pages — lazy loaded for code splitting
const LoginPage             = lazy(() => import('./admin/pages/auth/LoginPage.jsx'));
const DashboardPage         = lazy(() => import('./admin/pages/dashboard/DashboardPage.jsx'));
const VendorsPage           = lazy(() => import('./admin/pages/vendors/VendorsPage.jsx'));
const VendorDetailPage      = lazy(() => import('./admin/pages/vendors/VendorDetailPage.jsx'));
const CustomersPage         = lazy(() => import('./admin/pages/customers/CustomersPage.jsx'));
const CustomerDetailPage    = lazy(() => import('./admin/pages/customers/CustomerDetailPage.jsx'));
const BookingsPage          = lazy(() => import('./admin/pages/bookings/BookingsPage.jsx'));
const BookingDetailPage     = lazy(() => import('./admin/pages/bookings/BookingDetailPage.jsx'));
const PackagesPage          = lazy(() => import('./admin/pages/packages/PackagesPage.jsx'));
const PackageCategoriesPage = lazy(() => import('./admin/pages/packages/PackageCategoriesPage.jsx'));
const PaymentsPage          = lazy(() => import('./admin/pages/payments/PaymentsPage.jsx'));
const WalletsPage           = lazy(() => import('./admin/pages/payments/WalletsPage.jsx'));
const MembershipsPage       = lazy(() => import('./admin/pages/memberships/MembershipsPage.jsx'));
const OccasionsPage         = lazy(() => import('./admin/pages/occasions/OccasionsPage.jsx'));
const NotificationsPage     = lazy(() => import('./admin/pages/notifications/NotificationsPage.jsx'));
const SupportPage           = lazy(() => import('./admin/pages/support/SupportPage.jsx'));
const SupportDetailPage     = lazy(() => import('./admin/pages/support/SupportDetailPage.jsx'));
const MediaPage             = lazy(() => import('./admin/pages/media/MediaPage.jsx'));
const AdminManagementPage   = lazy(() => import('./admin/pages/admin-mgmt/AdminManagementPage.jsx'));
const SettingsPage          = lazy(() => import('./admin/pages/settings/SettingsPage.jsx'));
const ImportExportPage      = lazy(() => import('./admin/pages/io/ImportExportPage.jsx'));
const AutomationPage        = lazy(() => import('./admin/pages/automation/AutomationPage.jsx'));
const GlobalSearchPage      = lazy(() => import('./admin/pages/search/GlobalSearchPage.jsx'));

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
        <Packages />
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

      {/* Admin portal */}
      <Route
        path="/admin/*"
        element={
          <AdminAuthProvider>
            <Routes>
              {/* Login — own Suspense so layout is never replaced by a blank screen */}
              <Route
                path="login"
                element={
                  <Suspense fallback={<AdminFallback />}>
                    <LoginPage />
                  </Suspense>
                }
              />

              {/* Protected layout — AdminLayout owns the inner Suspense + AnimatePresence */}
              <Route element={<AdminLayout />}>
                <Route index element={<DashboardPage />} />
                <Route path="vendors" element={<VendorsPage />} />
                <Route path="vendors/:id" element={<VendorDetailPage />} />
                <Route path="customers" element={<CustomersPage />} />
                <Route path="customers/:id" element={<CustomerDetailPage />} />
                <Route path="bookings" element={<BookingsPage />} />
                <Route path="bookings/:id" element={<BookingDetailPage />} />
                <Route path="packages" element={<PackagesPage />} />
                <Route path="packages/categories" element={<PackageCategoriesPage />} />
                <Route path="payments" element={<PaymentsPage />} />
                <Route path="wallets" element={<WalletsPage />} />
                <Route path="memberships" element={<MembershipsPage />} />
                <Route path="occasions" element={<OccasionsPage />} />
                <Route path="notifications" element={<NotificationsPage />} />
                <Route path="support" element={<SupportPage />} />
                <Route path="support/:id" element={<SupportDetailPage />} />
                <Route path="media" element={<MediaPage />} />
                <Route path="admin-management" element={<AdminManagementPage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="io" element={<ImportExportPage />} />
                <Route path="automation" element={<AutomationPage />} />
                <Route path="search" element={<GlobalSearchPage />} />
              </Route>
            </Routes>
          </AdminAuthProvider>
        }
      />
    </Routes>
  );
}
