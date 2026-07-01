import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:cached_network_image/cached_network_image.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/app_state.dart';
import '../data/auth_manager.dart';
import '../data/models.dart';
import '../data/services/user_service.dart';
import '../data/services/auth_service.dart';
import '../widgets/common.dart';
import '../widgets/ty_button.dart';

import 'my_bookings_screen.dart';
import 'refer_earn_screen.dart';
import 'help_screen.dart';
import 'my_profile_screen.dart';
import 'membership_plan_screen.dart';
import 'manage_address_screen.dart';
import 'about_app_screen.dart';
import 'privacy_policy_screen.dart';
import 'terms_conditions_screen.dart';
import 'raise_ticket_screen.dart';
import 'onboarding_screen.dart';

class AccountScreen extends StatefulWidget {
  const AccountScreen({super.key});

  @override
  State<AccountScreen> createState() => _AccountScreenState();
}

class _AccountScreenState extends State<AccountScreen> {
  User? _user;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadUser();
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
    final topPadding = MediaQuery.of(context).padding.top + 70;

    return ListView(
      padding: EdgeInsets.fromLTRB(18, topPadding, 18, 28),
      children: [
        Text('Account', style: TyType.display(26, color: ty.ink)),
        const SizedBox(height: 24),
        _buildIdentity(ty),
        const SizedBox(height: 24),
        _buildQuickActions(context),
        const SizedBox(height: 24),
        _sectionHeader('Personal'),
        _menuGroup(context, [
          _menuItem(context, Icons.person_outline_rounded, 'My Profile',
              onTap: () => _push(context, const MyProfileScreen())),
          _menuItem(context, Icons.card_membership_rounded, 'My Membership Plan',
              onTap: () => _push(context, const MembershipPlanScreen())),
          _menuItem(context, Icons.place_outlined, 'Manage Addresses',
              onTap: () => _push(context, const ManageAddressScreen())),
        ]),
        const SizedBox(height: 16),
        _sectionHeader('Support & Legal'),
        _menuGroup(context, [
          _menuItem(context, Icons.info_outline_rounded, 'About App',
              onTap: () => _push(context, const AboutAppScreen())),
          _menuItem(context, Icons.privacy_tip_outlined, 'Privacy Policy',
              onTap: () => _push(context, const PrivacyPolicyScreen())),
          _menuItem(context, Icons.description_outlined, 'Terms & Conditions',
              onTap: () => _push(context, const TermsConditionsScreen())),
          _menuItem(context, Icons.confirmation_number_outlined, 'Raise Ticket',
              onTap: () => _push(context, const RaiseTicketScreen())),
        ]),
        const SizedBox(height: 16),
        _menuGroup(context, [
          _menuItem(context, Icons.delete_outline_rounded, 'Delete Account',
              color: ty.rose, onTap: () {}),
        ]),
        const SizedBox(height: 24),
        TyButton(
          'Sign out',
          kind: TyButtonKind.ghost,
          full: true,
          leadingIcon: Icons.logout_rounded,
          onTap: _handleLogout,
        ),
      ],
    );
  }

  Widget _buildIdentity(TyColors ty) {
    if (_loading) {
      return Row(
        children: [
          Container(
            width: 64, height: 64,
            decoration: BoxDecoration(color: ty.line, shape: BoxShape.circle),
          ),
          const SizedBox(width: 16),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(width: 120, height: 18, decoration: BoxDecoration(
                  color: ty.line, borderRadius: BorderRadius.circular(4))),
              const SizedBox(height: 6),
              Container(width: 80, height: 14, decoration: BoxDecoration(
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
          width: 64,
          height: 64,
          clipBehavior: Clip.antiAlias,
          decoration: BoxDecoration(color: ty.saffron, shape: BoxShape.circle),
          child: photoUrl != null && photoUrl.isNotEmpty
              ? CachedNetworkImage(
                  imageUrl: photoUrl,
                  fit: BoxFit.cover,
                  errorWidget: (_, __, ___) => Center(
                    child: Text(initial,
                        style: TextStyle(
                            color: ty.onPrimary,
                            fontWeight: FontWeight.w800,
                            fontSize: 26)),
                  ),
                )
              : Center(
                  child: Text(initial,
                      style: TextStyle(
                          color: ty.onPrimary,
                          fontWeight: FontWeight.w800,
                          fontSize: 26)),
                ),
        ),
        const SizedBox(width: 16),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(name, style: TyType.display(22, color: ty.ink)),
            const SizedBox(height: 2),
            if (sub.isNotEmpty) Text(sub, style: TyType.sans(14, color: ty.ink2)),
          ],
        ),
      ],
    );
  }

  Widget _buildQuickActions(BuildContext context) {
    return Row(
      children: [
        _quickAction(context, Icons.calendar_today_outlined, 'My Bookings',
            () => _push(context, const MyBookingsScreen())),
        const SizedBox(width: 12),
        _quickAction(context, Icons.card_giftcard_rounded, 'Refer & Earn',
            () => _push(context, const ReferEarnScreen())),
        const SizedBox(width: 12),
        _quickAction(context, Icons.help_outline_rounded, 'Help',
            () => _push(context, const HelpScreen())),
      ],
    );
  }

  Widget _quickAction(BuildContext context, IconData icon, String label, VoidCallback onTap) {
    final ty = context.ty;
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 16),
          decoration: BoxDecoration(
            color: ty.surface,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: ty.line),
          ),
          child: Column(
            children: [
              Icon(icon, color: ty.saffron, size: 24),
              const SizedBox(height: 8),
              Text(label, style: TyType.sans(12, color: ty.ink, weight: FontWeight.w600)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _sectionHeader(String label) {
    return Padding(
      padding: const EdgeInsets.only(left: 4, bottom: 8),
      child: Text(label.toUpperCase(), style: TyType.eyebrow(11, color: Colors.grey)),
    );
  }

  Widget _menuGroup(BuildContext context, List<Widget> children) {
    final ty = context.ty;
    return Container(
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: ty.line),
      ),
      child: Column(children: children),
    );
  }

  Widget _menuItem(BuildContext context, IconData icon, String label,
      {Color? color, VoidCallback? onTap}) {
    final ty = context.ty;
    return ListTile(
      leading: Icon(icon, color: color ?? ty.saffron, size: 22),
      title: Text(label,
          style: TyType.sans(14.5, color: color ?? ty.ink, weight: FontWeight.w600)),
      trailing: Icon(Icons.chevron_right_rounded, color: ty.ink3, size: 18),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16),
      onTap: onTap,
    );
  }
}
