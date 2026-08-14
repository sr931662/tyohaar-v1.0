import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:url_launcher/url_launcher.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../theme/responsive.dart';
import '../data/auth_manager.dart';
import '../data/models.dart';
import '../data/services/user_service.dart';
import '../data/services/auth_service.dart';
import '../widgets/ty_button.dart';
import '../widgets/tutorial/tutorial_overlay.dart';
import '../l10n/generated/app_localizations.dart';

import 'my_bookings_screen.dart';
import 'refer_earn_screen.dart';
import 'help_screen.dart';
import 'my_profile_screen.dart';
import 'membership_plan_screen.dart';
import 'manage_address_screen.dart';
import 'about_app_screen.dart';
import 'privacy_policy_screen.dart';
import 'cancellation_policy_screen.dart';
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
      final l10n = AppLocalizations.of(context)!;
      TutorialOverlay.show(context, screenKey: 'account', steps: [
        TutorialStep(
          targetKey: _quickActionsKey,
          title: l10n.accountTutorialTitle,
          description: l10n.accountTutorialDescription,
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
    final l10n = AppLocalizations.of(context)!;
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.accountSignOutConfirmTitle),
        content: Text(l10n.accountSignOutConfirmMessage),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(l10n.commonCancel)),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(l10n.accountSignOutLabel, style: const TextStyle(color: Colors.red)),
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

  // Google Play requires the deletion request path to be reachable from inside
  // the app as well as from the store listing. There is no authenticated
  // delete endpoint yet, so both routes land on the same web form.
  Future<void> _handleDeleteAccount() async {
    final l10n = AppLocalizations.of(context)!;
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.accountDeleteAccountConfirmTitle),
        content: Text(l10n.accountDeleteAccountConfirmMessage),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(l10n.commonCancel)),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(l10n.accountDeleteAccountContinueLabel,
                style: const TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
    if (confirm != true || !mounted) return;

    final opened = await launchUrl(
      Uri.parse('https://www.tyohaar.co/delete-account'),
      mode: LaunchMode.externalApplication,
    );
    if (!opened && mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(l10n.accountDeleteAccountOpenFailed)));
    }
  }

  void _push(BuildContext context, Widget page) {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    final l10n = AppLocalizations.of(context)!;
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
        padding: EdgeInsets.fromLTRB(resp.w(18), topPadding, resp.w(18),
            resp.h(28) + MediaQuery.of(context).padding.bottom),
        children: [
          Text(l10n.accountHeading, style: TyType.display(resp.sp(26), color: ty.ink)),
          SizedBox(height: resp.h(24)),
          _buildIdentity(context, ty, resp),
          SizedBox(height: resp.h(24)),
          _buildQuickActions(context),
          SizedBox(height: resp.h(24)),
          _sectionHeader(resp, l10n.accountSectionPersonalLabel),
          _menuGroup(context, resp, [
            _menuItem(context, resp, Icons.person_outline_rounded, l10n.accountMyProfileLabel,
                onTap: () => _push(context, const MyProfileScreen())),
            _menuItem(context, resp, Icons.card_membership_rounded, l10n.accountMyMembershipPlanLabel,
                onTap: () => _push(context, const MembershipPlanScreen())),
            _menuItem(context, resp, Icons.place_outlined, l10n.accountManageAddressesLabel,
                onTap: () => _push(context, const ManageAddressScreen())),
          ]),
          SizedBox(height: resp.h(16)),
          _sectionHeader(resp, l10n.accountSectionSupportLegalLabel),
          _menuGroup(context, resp, [
            _menuItem(context, resp, Icons.info_outline_rounded, l10n.aboutAppTitle,
                onTap: () => _push(context, const AboutAppScreen())),
            _menuItem(context, resp, Icons.privacy_tip_outlined, l10n.privacyPolicyTitle,
                onTap: () => _push(context, const PrivacyPolicyScreen())),
            _menuItem(context, resp, Icons.assignment_return_outlined, l10n.cancellationPolicyTitle,
                onTap: () => _push(context, const CancellationPolicyScreen())),
            _menuItem(context, resp, Icons.description_outlined, l10n.termsConditionsTitle,
                onTap: () => _push(context, const TermsConditionsScreen())),
            _menuItem(context, resp, Icons.confirmation_number_outlined, l10n.accountMyTicketsLabel,
                onTap: () => _push(context, const MyTicketsScreen())),
          ]),
          SizedBox(height: resp.h(16)),
          _menuGroup(context, resp, [
            _menuItem(context, resp, Icons.delete_outline_rounded, l10n.accountDeleteAccountLabel,
                color: ty.rose, onTap: _handleDeleteAccount),
          ]),
          SizedBox(height: resp.h(24)),
          TyButton(
            l10n.accountSignOutLabel,
            kind: TyButtonKind.ghost,
            full: true,
            leadingIcon: Icons.logout_rounded,
            onTap: _handleLogout,
          ),
        ],
      ),
    );
  }

  Widget _buildIdentity(BuildContext context, TyColors ty, TyResponsive resp) {
    final l10n = AppLocalizations.of(context)!;
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
    final name = user?.displayName ?? l10n.accountWelcomeFallback;
    final sub = user?.phone ?? user?.email ?? '';
    final photoUrl = user?.profilePhotoUrl;
    final initial = name.isNotEmpty ? name[0].toUpperCase() : l10n.accountAvatarInitialFallback;

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
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(name, style: TyType.display(resp.sp(22), color: ty.ink), maxLines: 1, overflow: TextOverflow.ellipsis),
              SizedBox(height: resp.h(2)),
              if (sub.isNotEmpty)
                Text(sub, style: TyType.sans(resp.sp(14), color: ty.ink2), maxLines: 1, overflow: TextOverflow.ellipsis),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildQuickActions(BuildContext context) {
    final resp = context.resp;
    final l10n = AppLocalizations.of(context)!;
    return Row(
      key: _quickActionsKey,
      children: [
        _quickAction(context, Icons.calendar_today_outlined, l10n.accountMyBookingsLabel,
            () => _push(context, const MyBookingsScreen())),
        SizedBox(width: resp.w(12)),
        _quickAction(context, Icons.card_giftcard_rounded, l10n.accountReferEarnLabel,
            () => _push(context, const ReferEarnScreen())),
        SizedBox(width: resp.w(12)),
        _quickAction(context, Icons.help_outline_rounded, l10n.accountHelpLabel,
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
