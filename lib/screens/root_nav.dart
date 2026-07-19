import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../theme/theme_controller.dart';
import '../theme/responsive.dart';
import '../data/auth_manager.dart';
import '../data/models.dart';
import '../data/services/user_service.dart';
import '../data/services/notification_service.dart';
import '../data/services/push_service.dart';
import 'home_screen.dart';
import 'plans_screen.dart';
import 'explore_screen.dart';
import 'account_screen.dart';
import 'plan_flow/plan_flow_screen.dart';

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
  final ScrollController _homeScrollController = ScrollController();

  late final _pages = [
    HomeScreen(scrollController: _homeScrollController),
    const PlansScreen(),
    const ExploreScreen(),
    const AccountScreen(),
  ];

  @override
  void initState() {
    super.initState();
    _ensureUserLoaded();
    _loadUnreadCount();
    PushService.instance.initialize();
  }

  @override
  void dispose() {
    _homeScrollController.dispose();
    super.dispose();
  }

  // Only the Home tab (index 0) tracks scroll-driven header contrast.
  // IndexedStack keeps HomeScreen's ListView (and its real scroll offset)
  // alive across tab switches, so when the user returns to Home we must
  // re-derive _isScrolled from the controller's actual offset instead of
  // blindly resetting to false — otherwise a header that should still be
  // opaque (because Home is scrolled) renders transparent with nothing
  // behind it for contrast.
  void _setIndex(int i) {
    setState(() {
      _index = i;
      _isScrolled = i == 0 &&
          _homeScrollController.hasClients &&
          _homeScrollController.offset > 20;
    });
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
      // Content flows under the floating dock so the gaps around it show
      // the page behind; each tab's scroll view adds bottom clearance
      // (MediaQuery.padding.bottom includes the navbar height) so nothing
      // ends up permanently hidden behind the bar.
      extendBody: true,
      drawer: _AppSidebar(
        user: AuthManager.instance.currentUser,
        onNavigate: (i) {
          if (i == 1 || i == 3) {
             AuthManager.instance.checkAuth(
              context,
              action: i == 1 ? 'view your plans' : 'access your account',
              onAuthenticated: () => _setIndex(i),
            );
          } else {
            _setIndex(i);
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
                onOpenProfile: () => _setIndex(3),
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
          if (_index == i) {
            // TODO: Scroll to top or refresh
            return;
          }
          if (i == 1 || i == 3) {
            AuthManager.instance.checkAuth(
              context,
              action: i == 1 ? 'view your plans' : 'access your account',
              onAuthenticated: () => _setIndex(i),
            );
          } else {
            _setIndex(i);
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
    final resp = context.resp;
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
      padding: EdgeInsets.fromLTRB(resp.w(18), MediaQuery.of(context).padding.top + resp.h(8), resp.w(18), resp.h(12)),
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
          SizedBox(width: resp.w(12)),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.location_on_rounded, 
                      size: resp.sp(10), 
                      color: isTransparent 
                          ? (isDark ? Colors.white.withOpacity(0.8) : ty.saffronDeep) 
                          : ty.saffronDeep),
                    SizedBox(width: resp.w(4)),
                    Text('INDIA',
                        style: TyType.eyebrow(resp.sp(10), color: isTransparent
                            ? (isDark ? Colors.white.withOpacity(0.8) : ty.saffronDeep)
                            : ty.saffronDeep)),
                  ],
                ),
                SizedBox(height: resp.h(1)),
                Text(
                  'Namaste, ${user?.firstName ?? user?.displayName.split(' ').first ?? 'there'}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TyType.display(resp.sp(22), color: foregroundColor),
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
          SizedBox(width: resp.w(10)),
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
                  top: resp.h(9),
                  right: resp.w(10),
                  child: Container(
                    width: resp.w(8),
                    height: resp.w(8),
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
    final resp = context.resp;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: resp.w(42),
        height: resp.w(42),
        decoration: BoxDecoration(
          color: backgroundColor,
          borderRadius: BorderRadius.circular(resp.w(14)),
          border: Border.all(color: borderColor),
        ),
        child: Icon(icon, size: resp.sp(21), color: foregroundColor),
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
    final resp = context.resp;
    return Padding(
      padding: EdgeInsets.fromLTRB(
        resp.w(14),
        0,
        resp.w(14),
        MediaQuery.of(context).padding.bottom + resp.h(10),
      ),
      child: Container(
            height: resp.h(72),
            decoration: BoxDecoration(
              color: ty.surface,
              borderRadius: BorderRadius.circular(resp.w(28)),
              border: Border.all(color: ty.line2),
              boxShadow: [
                BoxShadow(
                  color: ty.isDark ? Colors.black.withOpacity(0.35) : ty.ink.withOpacity(0.08),
                  blurRadius: resp.w(20),
                  offset: Offset(0, resp.h(8)),
                ),
              ],
            ),
            child: Row(
              children: [
                _DockItem(
                  selected: index == 0,
                  icon: Icons.home_outlined,
                  activeIcon: Icons.home_rounded,
                  label: 'Home',
                  onTap: () => onTap(0),
                ),
                _DockItem(
                  selected: index == 1,
                  icon: Icons.event_note_outlined,
                  activeIcon: Icons.event_note_rounded,
                  label: 'Plans',
                  onTap: () => onTap(1),
                ),
                SizedBox(
                  width: resp.w(72),
                  child: Center(child: _CenterButton(onTap: onCreate)),
                ),
                _DockItem(
                  selected: index == 2,
                  icon: Icons.storefront_outlined,
                  activeIcon: Icons.storefront_rounded,
                  label: 'Packages',
                  onTap: () => onTap(2),
                ),
                _DockItem(
                  selected: index == 3,
                  icon: Icons.person_outline_rounded,
                  activeIcon: Icons.person_rounded,
                  label: 'Account',
                  onTap: () => onTap(3),
                ),
              ],
            ),
      ),
    );
  }
}

/// A single dock destination: icon over an always-visible label, with a
/// "diya glow" halo, gentle icon lift, and a marigold dot when active.
/// Fixed column layout — nothing expands horizontally, so long labels
/// simply ellipsize instead of wrapping.
class _DockItem extends StatelessWidget {
  final bool selected;
  final IconData icon;
  final IconData activeIcon;
  final String label;
  final VoidCallback onTap;

  const _DockItem({
    required this.selected,
    required this.icon,
    required this.activeIcon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    final activeColor = ty.isDark ? ty.saffron : ty.saffronDeep;
    final color = selected ? activeColor : ty.ink3;

    return Expanded(
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () {
          if (!selected) HapticFeedback.selectionClick();
          onTap();
        },
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            SizedBox(
              height: resp.h(30),
              child: Stack(
                alignment: Alignment.center,
                children: [
                  // Diya glow halo behind the active icon.
                  AnimatedScale(
                    scale: selected ? 1.0 : 0.4,
                    duration: const Duration(milliseconds: 350),
                    curve: Curves.easeOutCubic,
                    child: AnimatedOpacity(
                      opacity: selected ? 1.0 : 0.0,
                      duration: const Duration(milliseconds: 350),
                      child: Container(
                        width: resp.w(40),
                        height: resp.w(40),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: RadialGradient(
                            colors: [
                              ty.saffron.withOpacity(0.28),
                              ty.saffron.withOpacity(0.0),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                  AnimatedSlide(
                    offset: selected ? Offset(0, resp.h(-3) / resp.h(30)) : Offset.zero,
                    duration: const Duration(milliseconds: 300),
                    curve: Curves.easeOutCubic,
                    child: Icon(
                      selected ? activeIcon : icon,
                      size: resp.sp(22),
                      color: color,
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: EdgeInsets.symmetric(horizontal: resp.w(2)),
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: resp.sp(9.5),
                  fontWeight: selected ? FontWeight.w700 : FontWeight.w600,
                  color: color,
                  letterSpacing: 0.2,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// The raised "Start a celebration" button — a warm gradient disc with a
/// slow breathing glow so it keeps drawing the eye without being loud.
class _CenterButton extends StatefulWidget {
  final VoidCallback onTap;
  const _CenterButton({required this.onTap});

  @override
  State<_CenterButton> createState() => _CenterButtonState();
}

class _CenterButtonState extends State<_CenterButton> with SingleTickerProviderStateMixin {
  late final AnimationController _pulse = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 2000),
  )..repeat(reverse: true);
  bool _pressed = false;

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    return GestureDetector(
      onTapDown: (_) => setState(() => _pressed = true),
      onTapCancel: () => setState(() => _pressed = false),
      onTapUp: (_) => setState(() => _pressed = false),
      onTap: () {
        HapticFeedback.mediumImpact();
        widget.onTap();
      },
      child: AnimatedBuilder(
        animation: _pulse,
        builder: (context, child) {
          final glow = 0.35 + (_pulse.value * 0.25);
          return Container(
            width: resp.w(60),
            height: resp.w(60),
            alignment: Alignment.center,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: ty.saffron.withOpacity(glow),
                  blurRadius: resp.w(24 + _pulse.value * 8),
                  spreadRadius: resp.w(1 + _pulse.value * 2),
                ),
              ],
            ),
            child: child,
          );
        },
        child: AnimatedScale(
          scale: _pressed ? 0.92 : 1.0,
          duration: const Duration(milliseconds: 120),
          curve: Curves.easeOut,
          child: Container(
            width: resp.w(50),
            height: resp.w(50),
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [ty.saffron, ty.gold],
              ),
            ),
            child: Icon(Icons.add_rounded, color: ty.onPrimary, size: resp.sp(26)),
          ),
        ),
      ),
    );
  }
}
