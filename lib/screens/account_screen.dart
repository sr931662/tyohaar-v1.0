import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:cached_network_image/cached_network_image.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../theme/responsive.dart';
import '../data/auth_manager.dart';
import '../data/models.dart';
import '../data/services/user_service.dart';
import '../data/services/auth_service.dart';
import '../widgets/ty_button.dart';
import '../widgets/tutorial/tutorial_overlay.dart';

import 'my_bookings_screen.dart';
import 'refer_earn_screen.dart';
import 'help_screen.dart';
import 'my_profile_screen.dart';
import 'membership_plan_screen.dart';
import 'manage_address_screen.dart';
import 'about_app_screen.dart';
import 'privacy_policy_screen.dart';
import 'terms_conditions_screen.dart';
import 'my_tickets_screen.dart';
import 'onboarding_screen.dart';

class AccountScreen extends StatefulWidget {
  const AccountScreen({super.key});

  @override
  State<AccountScreen> createState() => _AccountScreenState();
}

class _AccountScreenState extends State<AccountScreen> {
  User? _user;
  bool _loading = true;
  final GlobalKey _quickActionsKey = GlobalKey();

  @override
  void initState() {
    super.initState();
    _loadUser();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      TutorialOverlay.show(context, screenKey: 'account', steps: [
        TutorialStep(
          targetKey: _quickActionsKey,
          title: 'Everything about you, in one place',
          description: 'Jump to your bookings, referrals, or help from here — and manage your profile and membership below.',
        ),
      ]);
    });
  }

  Future<void> _loadUser() async {
    // Use cached user from AuthManager if available
    final cached = AuthManager.instance.currentUser;
    if (cached != null) {
      setState(() { _user = cached; _loading = false; });
      return;
    }
    try {
      final user = await context.read<UserService>().getMe();
      AuthManager.instance.setUser(user);
      if (mounted) setState(() { _user = user; _loading = false; });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _handleLogout() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Sign out?'),
        content: const Text('You will need to sign in again to access your account.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Sign out', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
    if (confirm != true || !mounted) return;

    await context.read<AuthService>().logout();
    await AuthManager.instance.logout();

    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const OnboardingScreen()),
      (_) => false,
    );
  }

  void _push(BuildContext context, Widget page) {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    final topPadding = MediaQuery.of(context).padding.top + resp.h(85);

    // Re-fetch user if AuthManager changed (auto-refresh when user updates)
    final user = context.watch<AuthManager>().currentUser;
    if (user != null && user != _user) {
      _user = user;
    }

    return RefreshIndicator(
      onRefresh: _loadUser,
      displacement: topPadding,
      color: ty.saffron,
      child: ListView(
        padding: EdgeInsets.fromLTRB(resp.w(18), topPadding, resp.w(18), resp.h(28)),
        children: [
          Text('Account', style: TyType.display(resp.sp(26), color: ty.ink)),
          SizedBox(height: resp.h(24)),
          _buildIdentity(ty, resp),
          SizedBox(height: resp.h(24)),
          _buildQuickActions(context),
          SizedBox(height: resp.h(24)),
          _sectionHeader(resp, 'Personal'),
          _menuGroup(context, resp, [
            _menuItem(context, resp, Icons.person_outline_rounded, 'My Profile',
                onTap: () => _push(context, const MyProfileScreen())),
            _menuItem(context, resp, Icons.card_membership_rounded, 'My Membership Plan',
                onTap: () => _push(context, const MembershipPlanScreen())),
            _menuItem(context, resp, Icons.place_outlined, 'Manage Addresses',
                onTap: () => _push(context, const ManageAddressScreen())),
          ]),
          SizedBox(height: resp.h(16)),
          _sectionHeader(resp, 'Support & Legal'),
          _menuGroup(context, resp, [
            _menuItem(context, resp, Icons.info_outline_rounded, 'About App',
                onTap: () => _push(context, const AboutAppScreen())),
            _menuItem(context, resp, Icons.privacy_tip_outlined, 'Privacy Policy',
                onTap: () => _push(context, const PrivacyPolicyScreen())),
            _menuItem(context, resp, Icons.description_outlined, 'Terms & Conditions',
                onTap: () => _push(context, const TermsConditionsScreen())),
            _menuItem(context, resp, Icons.confirmation_number_outlined, 'My Tickets',
                onTap: () => _push(context, const MyTicketsScreen())),
          ]),
          SizedBox(height: resp.h(16)),
          _menuGroup(context, resp, [
            _menuItem(context, resp, Icons.delete_outline_rounded, 'Delete Account',
                color: ty.rose, onTap: () {}),
          ]),
          SizedBox(height: resp.h(24)),
          TyButton(
            'Sign out',
            kind: TyButtonKind.ghost,
            full: true,
            leadingIcon: Icons.logout_rounded,
            onTap: _handleLogout,
          ),
        ],
      ),
    );
  }

  Widget _buildIdentity(TyColors ty, TyResponsive resp) {
    if (_loading && _user == null) {
      return Row(
        children: [
          Container(
            width: resp.w(80), height: resp.w(80),
            decoration: BoxDecoration(color: ty.line, shape: BoxShape.circle),
          ),
          SizedBox(width: resp.w(16)),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(width: resp.w(120), height: resp.h(18), decoration: BoxDecoration(
                  color: ty.line, borderRadius: BorderRadius.circular(4))),
              SizedBox(height: resp.h(6)),
              Container(width: resp.w(80), height: resp.h(14), decoration: BoxDecoration(
                  color: ty.line, borderRadius: BorderRadius.circular(4))),
            ],
          ),
        ],
      );
    }

    final user = _user;
    final name = user?.displayName ?? 'Welcome';
    final sub = user?.phone ?? user?.email ?? '';
    final photoUrl = user?.profilePhotoUrl;
    final initial = name.isNotEmpty ? name[0].toUpperCase() : 'T';

    return Row(
      children: [
        Container(
          width: resp.w(80),
          height: resp.w(80),
          clipBehavior: Clip.antiAlias,
          decoration: BoxDecoration(color: ty.saffron, shape: BoxShape.circle),
          child: photoUrl != null && photoUrl.isNotEmpty
              ? CachedNetworkImage(
                  imageUrl: photoUrl,
                  fit: BoxFit.cover,
                  placeholder: (_, __) => Center(
                    child: Text(initial,
                        style: TextStyle(
                            color: ty.onPrimary,
                            fontWeight: FontWeight.w800,
                            fontSize: resp.sp(30))),
                  ),
                  errorWidget: (_, __, ___) => Center(
                    child: Text(initial,
                        style: TextStyle(
                            color: ty.onPrimary,
                            fontWeight: FontWeight.w800,
                            fontSize: resp.sp(30))),
                  ),
                )
              : Center(
                  child: Text(initial,
                      style: TextStyle(
                          color: ty.onPrimary,
                          fontWeight: FontWeight.w800,
                          fontSize: resp.sp(30))),
                ),
        ),
        SizedBox(width: resp.w(16)),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(name, style: TyType.display(resp.sp(22), color: ty.ink)),
            SizedBox(height: resp.h(2)),
            if (sub.isNotEmpty) Text(sub, style: TyType.sans(resp.sp(14), color: ty.ink2)),
          ],
        ),
      ],
    );
  }

  Widget _buildQuickActions(BuildContext context) {
    final resp = context.resp;
    return Row(
      key: _quickActionsKey,
      children: [
        _quickAction(context, Icons.calendar_today_outlined, 'My Bookings',
            () => _push(context, const MyBookingsScreen())),
        SizedBox(width: resp.w(12)),
        _quickAction(context, Icons.card_giftcard_rounded, 'Refer & Earn',
            () => _push(context, const ReferEarnScreen())),
        SizedBox(width: resp.w(12)),
        _quickAction(context, Icons.help_outline_rounded, 'Help',
            () => _push(context, const HelpScreen())),
      ],
    );
  }

  Widget _quickAction(BuildContext context, IconData icon, String label, VoidCallback onTap) {
    final ty = context.ty;
    final resp = context.resp;
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: EdgeInsets.symmetric(vertical: resp.h(16)),
          decoration: BoxDecoration(
            color: ty.surface,
            borderRadius: BorderRadius.circular(resp.w(16)),
            border: Border.all(color: ty.line),
          ),
          child: Column(
            children: [
              Icon(icon, color: ty.saffron, size: resp.sp(24)),
              SizedBox(height: resp.h(8)),
              Text(label, style: TyType.sans(resp.sp(12), color: ty.ink, weight: FontWeight.w600)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _sectionHeader(TyResponsive resp, String label) {
    return Padding(
      padding: EdgeInsets.only(left: resp.w(4), bottom: resp.h(8)),
      child: Text(label.toUpperCase(), style: TyType.eyebrow(resp.sp(11), color: Colors.grey)),
    );
  }

  Widget _menuGroup(BuildContext context, TyResponsive resp, List<Widget> children) {
    final ty = context.ty;
    return Container(
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(resp.w(20)),
        border: Border.all(color: ty.line),
      ),
      child: Column(children: children),
    );
  }

  Widget _menuItem(BuildContext context, TyResponsive resp, IconData icon, String label,
      {Color? color, VoidCallback? onTap}) {
    final ty = context.ty;
    return ListTile(
      leading: Icon(icon, color: color ?? ty.saffron, size: resp.sp(22)),
      title: Text(label,
          style: TyType.sans(resp.sp(14.5), color: color ?? ty.ink, weight: FontWeight.w600)),
      trailing: Icon(Icons.chevron_right_rounded, color: ty.ink3, size: resp.sp(18)),
      contentPadding: EdgeInsets.symmetric(horizontal: resp.w(16)),
      onTap: onTap,
    );
  }
}
