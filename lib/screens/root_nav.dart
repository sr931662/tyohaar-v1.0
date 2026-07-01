import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../theme/theme_controller.dart';
import '../data/app_state.dart';
import '../data/auth_manager.dart';
import '../data/models.dart';
import '../data/services/user_service.dart';
import '../data/services/notification_service.dart';
import 'home_screen.dart';
import 'plans_screen.dart';
import 'explore_screen.dart';
import 'account_screen.dart';
import 'plan_flow/plan_flow_screen.dart';
import 'wallet_screen.dart';

import 'notifications_screen.dart';
import 'membership_plan_screen.dart';
import 'manage_address_screen.dart';
import 'help_screen.dart';
import 'privacy_policy_screen.dart';

/// The app's primary shell: five destinations + a raised central
/// "Start a celebration" button that opens the planning flow.
class RootNav extends StatefulWidget {
  const RootNav({super.key});

  @override
  State<RootNav> createState() => _RootNavState();
}

class _RootNavState extends State<RootNav> {
  int _index = 0;
  bool _isScrolled = false;
  int _unreadNotifs = 0;
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();

  final _pages = const [
    HomeScreen(),
    PlansScreen(),
    ExploreScreen(),
    AccountScreen(),
  ];

  @override
  void initState() {
    super.initState();
    _ensureUserLoaded();
    _loadUnreadCount();
  }

  Future<void> _loadUnreadCount() async {
    if (!AuthManager.instance.isAuthenticated) return;
    try {
      final count = await context.read<NotificationService>().getUnreadCount();
      if (mounted) setState(() => _unreadNotifs = count);
    } catch (_) {}
  }

  Future<void> _ensureUserLoaded() async {
    if (AuthManager.instance.currentUser != null) return;
    if (!AuthManager.instance.isAuthenticated) return;
    try {
      final user = await context.read<UserService>().getMe();
      AuthManager.instance.setUser(user);
    } catch (_) {}
  }

  void _openCreate() {
    AuthManager.instance.checkAuth(
      context, 
      action: 'start a celebration',
      onAuthenticated: () {
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const PlanFlowScreen()),
        );
      },
    );
  }

  Future<void> _push(BuildContext context, Widget page) {
    return Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: _scaffoldKey,
      drawer: _AppSidebar(
        user: AuthManager.instance.currentUser,
        onNavigate: (i) {
          if (i == 1 || i == 3) {
             AuthManager.instance.checkAuth(
              context, 
              action: i == 1 ? 'view your plans' : 'access your account',
              onAuthenticated: () => setState(() {
                _index = i;
                _isScrolled = false;
              }),
            );
          } else {
            setState(() => _index = i);
          }
          Navigator.pop(context);
        },
      ),
      body: Stack(
        children: [
          Positioned.fill(
            child: NotificationListener<ScrollNotification>(
              onNotification: (scroll) {
                if (_index == 0 && scroll.metrics.axis == Axis.vertical) {
                  final scrolled = scroll.metrics.pixels > 20;
                  if (scrolled != _isScrolled) {
                    setState(() => _isScrolled = scrolled);
                  }
                }
                return false;
              },
              child: IndexedStack(index: _index, children: _pages),
            ),
          ),
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: ListenableBuilder(
              listenable: AuthManager.instance,
              builder: (ctx, _) => _StickyHeader(
                isTransparent: _index == 0,
                isScrolled: _isScrolled,
                onOpenDrawer: () => _scaffoldKey.currentState?.openDrawer(),
                onOpenNotifications: () => _push(context, const NotificationsScreen()).then((_) => _loadUnreadCount()),
                onOpenProfile: () => setState(() => _index = 3),
                user: AuthManager.instance.currentUser,
                unreadCount: _unreadNotifs,
              ),
            ),
          ),
        ],
      ),
      bottomNavigationBar: _BottomBar(
        index: _index,
        onTap: (i) {
          if (i == 1 || i == 3) {
            AuthManager.instance.checkAuth(
              context, 
              action: i == 1 ? 'view your plans' : 'access your account',
              onAuthenticated: () => setState(() {
                _index = i;
                _isScrolled = false;
              }),
            );
          } else {
            setState(() {
              _index = i;
              _isScrolled = false;
            });
          }
        },
        onCreate: _openCreate,
      ),
    );
  }
}

class _StickyHeader extends StatelessWidget {
  final bool isTransparent;
  final bool isScrolled;
  final VoidCallback onOpenDrawer;
  final VoidCallback onOpenNotifications;
  final VoidCallback onOpenProfile;
  final User? user;
  final int unreadCount;

  const _StickyHeader({
    required this.isTransparent,
    required this.isScrolled,
    required this.onOpenDrawer,
    required this.onOpenNotifications,
    required this.onOpenProfile,
    this.user,
    this.unreadCount = 0,
  });

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final bool useBlur = isTransparent && isScrolled;
    final bool isDark = themeController.isDark;
    
    // In transparent mode at the top, we want white text if the theme is dark 
    // OR if we have a strong enough dark gradient. 
    // But if it's light mode and we are at the top, 
    // we should use darker text for better contrast on light imagery.
    final Color foregroundColor = isTransparent 
        ? (isDark ? Colors.white : ty.ink.withOpacity(0.9)) 
        : ty.ink;
        
    final Color buttonBgColor = isTransparent 
        ? (isDark ? Colors.white.withOpacity(0.15) : Colors.black.withOpacity(0.05)) 
        : ty.surface;
        
    final Color borderColor = isTransparent 
        ? (isDark ? Colors.white.withOpacity(0.2) : Colors.black.withOpacity(0.1)) 
        : ty.line;

    Widget header = Container(
      padding: EdgeInsets.fromLTRB(18, MediaQuery.of(context).padding.top + 8, 18, 12),
      decoration: BoxDecoration(
        color: useBlur 
            ? ty.paper.withOpacity(0.75) 
            : (isTransparent ? Colors.transparent : ty.paper),
        border: (isTransparent && !isScrolled)
            ? null 
            : Border(bottom: BorderSide(color: ty.line2.withOpacity(isScrolled ? 0.1 : 0.05))),
      ),
      child: Row(
        children: [
          _circleButton(
            context,
            Icons.menu_rounded,
            onOpenDrawer,
            foregroundColor: foregroundColor,
            backgroundColor: buttonBgColor,
            borderColor: borderColor,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.location_on_rounded, 
                      size: 10, 
                      color: isTransparent 
                          ? (isDark ? Colors.white.withOpacity(0.8) : ty.saffronDeep) 
                          : ty.saffronDeep),
                    const SizedBox(width: 4),
                    Text('INDIA',
                        style: TyType.eyebrow(10, color: isTransparent
                            ? (isDark ? Colors.white.withOpacity(0.8) : ty.saffronDeep)
                            : ty.saffronDeep)),
                  ],
                ),
                const SizedBox(height: 1),
                Text(
                  'Namaste, ${user?.firstName ?? user?.displayName.split(' ').first ?? 'there'}',
                  style: TyType.display(22, color: foregroundColor),
                ),
              ],
            ),
          ),
          _circleButton(
            context,
            themeController.isDark ? Icons.wb_sunny_outlined : Icons.nightlight_round,
            themeController.toggle,
            foregroundColor: foregroundColor,
            backgroundColor: buttonBgColor,
            borderColor: borderColor,
          ),
          const SizedBox(width: 10),
          _circleButton(
            context,
            Icons.account_balance_wallet_outlined,
            () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const WalletScreen()),
            ),
            foregroundColor: foregroundColor,
            backgroundColor: buttonBgColor,
            borderColor: borderColor,
          ),
          const SizedBox(width: 10),
          Stack(
            children: [
              _circleButton(
                context, 
                Icons.notifications_none_rounded, 
                onOpenNotifications,
                foregroundColor: foregroundColor,
                backgroundColor: buttonBgColor,
                borderColor: borderColor,
              ),
              if (unreadCount > 0)
                Positioned(
                  top: 9,
                  right: 10,
                  child: Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: ty.rose,
                      shape: BoxShape.circle,
                      border: Border.all(color: isTransparent ? Colors.transparent : ty.paper, width: 2),
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );

    if (useBlur) {
      return ClipRect(
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
          child: header,
        ),
      );
    }

    return header;
  }

  Widget _circleButton(
    BuildContext context, 
    IconData icon, 
    VoidCallback onTap, {
    required Color foregroundColor,
    required Color backgroundColor,
    required Color borderColor,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 42,
        height: 42,
        decoration: BoxDecoration(
          color: backgroundColor,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: borderColor),
        ),
        child: Icon(icon, size: 21, color: foregroundColor),
      ),
    );
  }
}

class _AppSidebar extends StatelessWidget {
  final ValueChanged<int> onNavigate;
  final User? user;
  const _AppSidebar({required this.onNavigate, this.user});

  Future<void> _push(BuildContext context, Widget page) {
    return Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Drawer(
      backgroundColor: ty.paper,
      width: MediaQuery.of(context).size.width * 0.82,
      child: Column(
        children: [
          _buildHeader(context),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(vertical: 12),
              children: [
                _drawerItem(context, Icons.home_outlined, 'Home', 0),
                _drawerItem(context, Icons.event_note_outlined, 'My Plans', 1),
                _drawerItem(context, Icons.storefront_outlined, 'Packages', 2),
                _drawerItem(context, Icons.person_outline_rounded, 'Account', 3),
                const Divider(height: 32, indent: 20, endIndent: 20, color: Colors.black12),
                _drawerItem(context, Icons.card_membership_rounded, 'Membership', -1,
                    onTap: () => _push(context, const MembershipPlanScreen())),
                _drawerItem(context, Icons.place_outlined, 'Manage Address', -1,
                    onTap: () => _push(context, const ManageAddressScreen())),
                _drawerItem(context, Icons.help_outline_rounded, 'Help & Support', -1,
                    onTap: () => _push(context, const HelpScreen())),
                _drawerItem(context, Icons.description_outlined, 'Privacy Policy', -1,
                    onTap: () => _push(context, const PrivacyPolicyScreen())),
              ],
            ),
          ),
          _buildFooter(context),
        ],
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    final ty = context.ty;
    final name = user?.displayName ?? 'Welcome';
    final sub = user?.email ?? user?.phone ?? '';
    final initial = name.isNotEmpty ? name[0].toUpperCase() : 'T';

    return Container(
      padding: EdgeInsets.fromLTRB(20, MediaQuery.of(context).padding.top + 20, 20, 24),
      decoration: BoxDecoration(
        color: ty.surface,
        border: Border(bottom: BorderSide(color: ty.line2)),
      ),
      child: Row(
        children: [
          Container(
            width: 54,
            height: 54,
            alignment: Alignment.center,
            decoration: BoxDecoration(color: ty.saffron, shape: BoxShape.circle),
            child: Text(initial,
                style: TextStyle(
                    color: ty.onPrimary, fontWeight: FontWeight.w800, fontSize: 22)),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: TyType.sans(18, color: ty.ink, weight: FontWeight.w700)),
                const SizedBox(height: 2),
                if (sub.isNotEmpty) Text(sub, style: TyType.sans(12.5, color: ty.ink3)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _drawerItem(BuildContext context, IconData icon, String label, int targetIndex, {VoidCallback? onTap}) {
    final ty = context.ty;
    return ListTile(
      leading: Icon(icon, color: ty.ink2, size: 22),
      title: Text(label, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w600)),
      contentPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 2),
      onTap: onTap ?? (targetIndex != -1 ? () => onNavigate(targetIndex) : () {}),
    );
  }

  Widget _buildFooter(BuildContext context) {
    final ty = context.ty;
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
      decoration: BoxDecoration(
        border: Border(top: BorderSide(color: ty.line2)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              Icon(themeController.isDark ? Icons.wb_sunny_outlined : Icons.nightlight_round,
                  color: ty.ink3, size: 18),
              const SizedBox(width: 12),
              Text(themeController.isDark ? 'Light Mode' : 'Dark Mode',
                  style: TyType.sans(13.5, color: ty.ink2, weight: FontWeight.w600)),
            ],
          ),
          Switch.adaptive(
            value: themeController.isDark,
            activeTrackColor: ty.saffron,
            onChanged: (_) => themeController.toggle(),
          ),
        ],
      ),
    );
  }
}

class _BottomBar extends StatelessWidget {
  final int index;
  final ValueChanged<int> onTap;
  final VoidCallback onCreate;
  const _BottomBar({
    required this.index,
    required this.onTap,
    required this.onCreate,
  });

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Container(
      decoration: BoxDecoration(
        color: ty.paper.withOpacity(0.96),
        border: Border(top: BorderSide(color: ty.line2)),
      ),
      padding: EdgeInsets.only(
        top: 8,
        bottom: MediaQuery.of(context).padding.bottom + 8,
      ),
      child: Row(
        children: [
          _navItem(context, 0, Icons.home_outlined, Icons.home_rounded, 'Home'),
          _navItem(context, 1, Icons.event_note_outlined, Icons.event_note_rounded, 'Plans'),
          Expanded(child: _centerButton(context)),
          _navItem(context, 2, Icons.storefront_outlined, Icons.storefront_rounded, 'Packages'),
          _navItem(context, 3, Icons.person_outline_rounded, Icons.person_rounded, 'Account'),
        ],
      ),
    );
  }

  Widget _navItem(BuildContext context, int i, IconData icon, IconData active, String label) {
    final ty = context.ty;
    final selected = index == i;
    final color = selected ? ty.saffron : ty.ink3;
    return Expanded(
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () => onTap(i),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(selected ? active : icon, color: color, size: 24),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 10.5,
                fontWeight: selected ? FontWeight.w700 : FontWeight.w600,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _centerButton(BuildContext context) {
    final ty = context.ty;
    return GestureDetector(
      onTap: onCreate,
      child: Transform.translate(
        offset: const Offset(0, -12),
        child: Container(
          width: 56,
          height: 56,
          decoration: BoxDecoration(
            color: ty.saffron,
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: ty.saffron.withOpacity(0.55),
                blurRadius: 22,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Icon(Icons.add_rounded, color: ty.onPrimary, size: 30),
        ),
      ),
    );
  }
}
