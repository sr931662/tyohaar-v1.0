import 'package:flutter/material.dart';

import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../theme/theme_controller.dart';
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

class _VendorDestination {
  final String title;
  final IconData icon;
  final IconData activeIcon;
  final Widget screen;
  const _VendorDestination(this.title, this.icon, this.activeIcon, this.screen);
}

const List<_VendorDestination> _destinations = [
  _VendorDestination('Dashboard', Icons.dashboard_outlined, Icons.dashboard_rounded, VendorDashboardScreen()),
  _VendorDestination('Bookings', Icons.event_note_outlined, Icons.event_note_rounded, VendorBookingsScreen()),
  _VendorDestination('Packages', Icons.add_box_outlined, Icons.add_box_rounded, VendorPackagesScreen()),
  _VendorDestination('Earnings', Icons.payments_outlined, Icons.payments_rounded, VendorEarningsScreen()),
  _VendorDestination('Profile', Icons.person_outline_rounded, Icons.person_rounded, VendorProfileScreen()),
  _VendorDestination('Availability', Icons.calendar_today_outlined, Icons.calendar_today_rounded, VendorAvailabilityScreen()),
  _VendorDestination('Multimedia', Icons.video_library_outlined, Icons.video_library_rounded, VendorMultimediaScreen()),
  _VendorDestination('Bank Accounts', Icons.account_balance_outlined, Icons.account_balance_rounded, VendorBankScreen()),
  _VendorDestination('Reviews', Icons.star_outline_rounded, Icons.star_rounded, VendorReviewsScreen()),
  _VendorDestination('Notifications', Icons.notifications_outlined, Icons.notifications_rounded, VendorNotificationsScreen()),
  _VendorDestination('Support', Icons.support_agent_outlined, Icons.support_agent_rounded, VendorSupportScreen()),
];

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

  void _setIndex(int i) => setState(() => _index = i);

  void _navigate(int i) {
    if (_scaffoldKey.currentState?.isDrawerOpen ?? false) {
      Navigator.of(context).pop();
    }
    setState(() => _index = i);
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
    final current = _destinations[_index];

    return Scaffold(
      key: _scaffoldKey,
      appBar: AppBar(
        backgroundColor: ty.paper,
        elevation: 0,
        centerTitle: true,
        iconTheme: IconThemeData(color: ty.ink),
        title: Text(current.title, style: TyType.display(20, color: ty.ink)),
        actions: [
          IconButton(
            icon: Icon(_index == 9 ? Icons.notifications_rounded : Icons.notifications_outlined),
            onPressed: () => _navigate(9),
          ),
          const SizedBox(width: 8),
        ],
      ),
      drawer: _VendorDrawer(
        currentIndex: _index,
        onNavigate: _navigate,
        onLogout: _handleLogout,
      ),
      body: IndexedStack(index: _index, children: _destinations.map((e) => e.screen).toList()),
      bottomNavigationBar: _VendorBottomBar(index: _index, onTap: _setIndex),
    );
  }
}

class _VendorBottomBar extends StatelessWidget {
  final int index;
  final ValueChanged<int> onTap;
  const _VendorBottomBar({required this.index, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Container(
      decoration: BoxDecoration(
        color: ty.paper,
        border: Border(top: BorderSide(color: ty.line2)),
      ),
      padding: EdgeInsets.only(top: 10, bottom: MediaQuery.of(context).padding.bottom + 18),
      child: Row(
        children: [
          for (var i = 0; i < 5; i++)
            Expanded(
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () => onTap(i),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      index == i ? _destinations[i].activeIcon : _destinations[i].icon,
                      color: index == i ? ty.saffron : ty.ink3,
                      size: 24,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _destinations[i].title,
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
  final int currentIndex;
  final void Function(int index) onNavigate;
  final VoidCallback onLogout;
  const _VendorDrawer({required this.currentIndex, required this.onNavigate, required this.onLogout});

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
                      Text('Vendor Account', style: TyType.sans(12.5, color: ty.ink3)),
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
                _drawerItem(context, 0),
                _drawerItem(context, 1),
                _drawerItem(context, 2),
                _drawerItem(context, 5),
                _drawerItem(context, 6),
                const Divider(height: 24, indent: 24, endIndent: 24),
                _sectionLabel(ty, 'FINANCE'),
                _drawerItem(context, 3),
                _drawerItem(context, 7),
                const Divider(height: 24, indent: 24, endIndent: 24),
                _sectionLabel(ty, 'ACCOUNT'),
                _drawerItem(context, 4),
                _drawerItem(context, 8),
                _drawerItem(context, 9),
                _drawerItem(context, 10),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.fromLTRB(8, 8, 8, 8),
            decoration: BoxDecoration(border: Border(top: BorderSide(color: ty.line2))),
            child: ListenableBuilder(
              listenable: themeController,
              builder: (context, _) => SwitchListTile(
                title: Text(themeController.isDark ? 'Dark Mode' : 'Light Mode', 
                    style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
                secondary: Icon(themeController.isDark ? Icons.dark_mode_rounded : Icons.light_mode_rounded, 
                    color: themeController.isDark ? ty.gold : ty.saffron),
                value: themeController.isDark,
                onChanged: (_) => themeController.toggle(),
              ),
            ),
          ),
          Container(
            padding: const EdgeInsets.fromLTRB(8, 0, 8, 24),
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

  Widget _drawerItem(BuildContext context, int index) {
    final ty = context.ty;
    final dest = _destinations[index];
    final isSelected = currentIndex == index;

    return ListTile(
      leading: Icon(isSelected ? dest.activeIcon : dest.icon, 
          color: isSelected ? ty.saffron : ty.ink2, size: 22),
      title: Text(dest.title, 
          style: TyType.sans(15, color: isSelected ? ty.saffron : ty.ink, weight: isSelected ? FontWeight.w700 : FontWeight.w600)),
      contentPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 0),
      selected: isSelected,
      selectedTileColor: ty.saffron.withValues(alpha: 0.08),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      onTap: () => onNavigate(index),
    );
  }
}
