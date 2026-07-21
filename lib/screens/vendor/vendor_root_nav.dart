import 'package:flutter/material.dart';

import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../data/app_state.dart';
import '../../data/auth_manager.dart';
import '../../data/services/auth_service.dart';
import '../../widgets/avatar.dart';
import '../auth_screen.dart';
import 'dashboard/vendor_dashboard_screen.dart';
import 'bookings/vendor_bookings_screen.dart';
import 'packages/vendor_packages_screen.dart';
import 'earnings/vendor_earnings_screen.dart';
import 'profile/vendor_profile_screen.dart';
import 'vendor_availability_screen.dart';
import 'multimedia/vendor_multimedia_screen.dart';
import 'bank/vendor_bank_screen.dart';
import 'reviews/vendor_reviews_screen.dart';
import 'notifications/vendor_notifications_screen.dart';
import 'support/vendor_support_screen.dart';

/// The vendor shell: bottom navbar [Dashboard, My Bookings, Add packages,
/// Earnings, My Profile] + a drawer mirroring the web vendor portal's full
/// sidebar (Main / Finance / Account sections) for the destinations that
/// don't fit the bottom bar.
class VendorRootNav extends StatefulWidget {
  const VendorRootNav({super.key});

  @override
  State<VendorRootNav> createState() => _VendorRootNavState();
}

class _VendorRootNavState extends State<VendorRootNav> {
  int _index = 0;
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();

  late final List<Widget> _pages = const [
    VendorDashboardScreen(),
    VendorBookingsScreen(),
    VendorPackagesScreen(),
    VendorEarningsScreen(),
    VendorProfileScreen(),
  ];

  void _setIndex(int i) => setState(() => _index = i);

  void _openDrawerDestination(Widget screen) {
    Navigator.of(context).pop(); // close drawer
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));
  }

  Future<void> _handleLogout() async {
    Navigator.of(context).pop();
    try {
      await AuthService().logout();
    } catch (_) {}
    await AuthManager.instance.logout();
    AppState.instance.setPOV(UserPOV.customer);
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const AuthScreen()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Scaffold(
      key: _scaffoldKey,
      appBar: AppBar(
        backgroundColor: ty.paper,
        elevation: 0,
        iconTheme: IconThemeData(color: ty.ink),
        title: Text('Vendor', style: TyType.display(20, color: ty.ink)),
      ),
      drawer: _VendorDrawer(
        onNavigate: _openDrawerDestination,
        onLogout: _handleLogout,
      ),
      body: IndexedStack(index: _index, children: _pages),
      bottomNavigationBar: _VendorBottomBar(index: _index, onTap: _setIndex),
    );
  }
}

class _VendorBottomBar extends StatelessWidget {
  final int index;
  final ValueChanged<int> onTap;
  const _VendorBottomBar({required this.index, required this.onTap});

  static const _items = [
    (Icons.dashboard_outlined, Icons.dashboard_rounded, 'Dashboard'),
    (Icons.event_note_outlined, Icons.event_note_rounded, 'Bookings'),
    (Icons.add_box_outlined, Icons.add_box_rounded, 'Packages'),
    (Icons.payments_outlined, Icons.payments_rounded, 'Earnings'),
    (Icons.person_outline_rounded, Icons.person_rounded, 'Profile'),
  ];

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Container(
      decoration: BoxDecoration(
        color: ty.paper,
        border: Border(top: BorderSide(color: ty.line2)),
      ),
      padding: EdgeInsets.only(top: 10, bottom: MediaQuery.of(context).padding.bottom + 10),
      child: Row(
        children: [
          for (var i = 0; i < _items.length; i++)
            Expanded(
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () => onTap(i),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      index == i ? _items[i].$2 : _items[i].$1,
                      color: index == i ? ty.saffron : ty.ink3,
                      size: 24,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _items[i].$3,
                      style: TextStyle(
                        fontSize: 10.5,
                        fontWeight: index == i ? FontWeight.w700 : FontWeight.w600,
                        color: index == i ? ty.saffron : ty.ink3,
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _VendorDrawer extends StatelessWidget {
  final void Function(Widget screen) onNavigate;
  final VoidCallback onLogout;
  const _VendorDrawer({required this.onNavigate, required this.onLogout});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final user = AuthManager.instance.currentUser;

    return Drawer(
      backgroundColor: ty.paper,
      width: MediaQuery.of(context).size.width * 0.82,
      child: Column(
        children: [
          Container(
            padding: EdgeInsets.fromLTRB(20, MediaQuery.of(context).padding.top + 20, 20, 24),
            decoration: BoxDecoration(color: ty.surface, border: Border(bottom: BorderSide(color: ty.line2))),
            child: Row(
              children: [
                TyAvatar(name: user?.displayName ?? 'Vendor', size: 54),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(user?.displayName ?? 'Vendor Partner',
                          style: TyType.sans(17, color: ty.ink, weight: FontWeight.w700),
                          maxLines: 1, overflow: TextOverflow.ellipsis),
                      Text('Vendor', style: TyType.sans(12.5, color: ty.ink3)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(vertical: 8),
              children: [
                _sectionLabel(ty, 'MAIN'),
                _item(context, Icons.dashboard_outlined, 'Dashboard', () => onNavigate(const VendorDashboardScreen())),
                _item(context, Icons.event_note_outlined, 'My Bookings', () => onNavigate(const VendorBookingsScreen())),
                _item(context, Icons.add_box_outlined, 'My Packages', () => onNavigate(const VendorPackagesScreen())),
                _item(context, Icons.calendar_today_outlined, 'Availability', () => onNavigate(const VendorAvailabilityScreen())),
                _item(context, Icons.video_library_outlined, 'Multimedia', () => onNavigate(const VendorMultimediaScreen())),
                const Divider(height: 24),
                _sectionLabel(ty, 'FINANCE'),
                _item(context, Icons.payments_outlined, 'Earnings', () => onNavigate(const VendorEarningsScreen())),
                _item(context, Icons.account_balance_outlined, 'Bank Accounts', () => onNavigate(const VendorBankScreen())),
                const Divider(height: 24),
                _sectionLabel(ty, 'ACCOUNT'),
                _item(context, Icons.person_outline_rounded, 'My Profile', () => onNavigate(const VendorProfileScreen())),
                _item(context, Icons.star_outline_rounded, 'Reviews', () => onNavigate(const VendorReviewsScreen())),
                _item(context, Icons.notifications_outlined, 'Notifications', () => onNavigate(const VendorNotificationsScreen())),
                _item(context, Icons.support_agent_outlined, 'Support', () => onNavigate(const VendorSupportScreen())),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.fromLTRB(8, 8, 8, 24),
            decoration: BoxDecoration(border: Border(top: BorderSide(color: ty.line2))),
            child: ListTile(
              leading: Icon(Icons.logout_rounded, color: ty.rose),
              title: Text('Logout', style: TyType.sans(15, color: ty.rose, weight: FontWeight.w700)),
              onTap: onLogout,
            ),
          ),
        ],
      ),
    );
  }

  Widget _sectionLabel(TyColors ty, String label) => Padding(
        padding: const EdgeInsets.fromLTRB(24, 12, 24, 6),
        child: Text(label, style: TyType.eyebrow(11, color: ty.ink3)),
      );

  Widget _item(BuildContext context, IconData icon, String label, VoidCallback onTap) {
    final ty = context.ty;
    return ListTile(
      leading: Icon(icon, color: ty.ink2, size: 22),
      title: Text(label, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w600)),
      contentPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 0),
      onTap: onTap,
    );
  }
}
