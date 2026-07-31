import 'package:flutter/material.dart';

import '../../theme/colors.dart';
import '../../theme/responsive.dart';
import '../../theme/typography.dart';
import '../../theme/theme_controller.dart';
import '../../data/app_state.dart';
import '../../data/auth_manager.dart';
import '../../data/services/auth_service.dart';
import '../../data/services/push_service.dart';
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
import '../../l10n/generated/app_localizations.dart';

class _VendorDestination {
  final String title;
  final IconData icon;
  final IconData activeIcon;
  final Widget screen;
  const _VendorDestination(this.title, this.icon, this.activeIcon, this.screen);
}

List<_VendorDestination> _destinations(BuildContext context) {
  final l10n = AppLocalizations.of(context)!;
  return [
    _VendorDestination(l10n.vendorNavDashboardLabel, Icons.dashboard_outlined, Icons.dashboard_rounded, const VendorDashboardScreen()),
    _VendorDestination(l10n.vendorNavBookingsLabel, Icons.event_note_outlined, Icons.event_note_rounded, const VendorBookingsScreen()),
    _VendorDestination(l10n.vendorNavPackagesLabel, Icons.add_box_outlined, Icons.add_box_rounded, const VendorPackagesScreen()),
    _VendorDestination(l10n.vendorNavEarningsLabel, Icons.payments_outlined, Icons.payments_rounded, const VendorEarningsScreen()),
    _VendorDestination(l10n.vendorNavProfileLabel, Icons.person_outline_rounded, Icons.person_rounded, const VendorProfileScreen()),
    _VendorDestination(l10n.vendorNavAvailabilityLabel, Icons.calendar_today_outlined, Icons.calendar_today_rounded, const VendorAvailabilityScreen()),
    _VendorDestination(l10n.vendorNavMultimediaLabel, Icons.video_library_outlined, Icons.video_library_rounded, const VendorMultimediaScreen()),
    _VendorDestination(l10n.vendorNavBankAccountsLabel, Icons.account_balance_outlined, Icons.account_balance_rounded, const VendorBankScreen()),
    _VendorDestination(l10n.vendorNavReviewsLabel, Icons.star_outline_rounded, Icons.star_rounded, const VendorReviewsScreen()),
    _VendorDestination(l10n.vendorNavNotificationsLabel, Icons.notifications_outlined, Icons.notifications_rounded, const VendorNotificationsScreen()),
    _VendorDestination(l10n.vendorNavSupportLabel, Icons.support_agent_outlined, Icons.support_agent_rounded, const VendorSupportScreen()),
  ];
}

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

  @override
  void initState() {
    super.initState();
    // Mirrors root_nav.dart (customer shell) — without this, vendors never
    // register an FCM device token and so never receive push notifications,
    // even though the backend dispatches PUSH-channel notifications for them.
    PushService.instance.initialize();
  }

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
    final destinations = _destinations(context);
    final current = destinations[_index];

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
      body: IndexedStack(index: _index, children: destinations.map((e) => e.screen).toList()),
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
    final resp = context.resp;
    final destinations = _destinations(context);

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
                      index == i ? destinations[i].activeIcon : destinations[i].icon,
                      color: index == i ? ty.saffron : ty.ink3,
                      size: 24,
                    ),
                    const SizedBox(height: 4),
                    Padding(
                      padding: EdgeInsets.symmetric(horizontal: resp.w(2)),
                      child: Text(
                        destinations[i].title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: resp.sp(10.5),
                          fontWeight: index == i ? FontWeight.w700 : FontWeight.w600,
                          color: index == i ? ty.saffron : ty.ink3,
                        ),
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
    final l10n = AppLocalizations.of(context)!;
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
                TyAvatar(name: user?.displayName ?? l10n.vendorNavDefaultAvatarName, size: 54),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(user?.displayName ?? l10n.vendorNavDefaultDisplayName,
                          style: TyType.sans(17, color: ty.ink, weight: FontWeight.w700),
                          maxLines: 1, overflow: TextOverflow.ellipsis),
                      Text(l10n.vendorNavAccountLabel, style: TyType.sans(12.5, color: ty.ink3)),
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
                _sectionLabel(ty, l10n.vendorNavSectionMain),
                _drawerItem(context, 0),
                _drawerItem(context, 1),
                _drawerItem(context, 2),
                _drawerItem(context, 5),
                _drawerItem(context, 6),
                const Divider(height: 24, indent: 24, endIndent: 24),
                _sectionLabel(ty, l10n.vendorNavSectionFinance),
                _drawerItem(context, 3),
                _drawerItem(context, 7),
                const Divider(height: 24, indent: 24, endIndent: 24),
                _sectionLabel(ty, l10n.vendorNavSectionAccount),
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
                title: Text(themeController.isDark ? l10n.vendorNavDarkModeLabel : l10n.vendorNavLightModeLabel,
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
              title: Text(l10n.vendorNavLogoutLabel, style: TyType.sans(15, color: ty.rose, weight: FontWeight.w700)),
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
    final dest = _destinations(context)[index];
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
