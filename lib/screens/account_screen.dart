import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/app_state.dart';
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

/// Account screen for managing profile, bookings, addresses and app settings.
class AccountScreen extends StatelessWidget {
  const AccountScreen({super.key});

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
        // Switch to Vendor
        _vendorBanner(context),
        const SizedBox(height: 24),
        // identity
        Row(
          children: [
            Container(
              width: 64,
              height: 64,
              alignment: Alignment.center,
              decoration: BoxDecoration(color: ty.saffron, shape: BoxShape.circle),
              child: Text('A',
                  style: TextStyle(
                      color: ty.onPrimary, fontWeight: FontWeight.w800, fontSize: 26)),
            ),
            const SizedBox(width: 16),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Aarav Sharma', style: TyType.display(22, color: ty.ink)),
                const SizedBox(height: 2),
                Text('+91 98765 43210', style: TyType.sans(14, color: ty.ink2)),
              ],
            ),
          ],
        ),
        const SizedBox(height: 24),
        // quick actions
        Row(
          children: [
            _quickAction(context, Icons.calendar_today_outlined, 'My Bookings', () => _push(context, const MyBookingsScreen())),
            const SizedBox(width: 12),
            _quickAction(context, Icons.card_giftcard_rounded, 'Refer & Earn', () => _push(context, const ReferEarnScreen())),
            const SizedBox(width: 12),
            _quickAction(context, Icons.help_outline_rounded, 'Help', () => _push(context, const HelpScreen())),
          ],
        ),
        const SizedBox(height: 24),
        // menu
        _sectionHeader('Personal'),
        _menuGroup(context, [
          _menuItem(context, Icons.person_outline_rounded, 'My Profile', onTap: () => _push(context, const MyProfileScreen())),
          _menuItem(context, Icons.card_membership_rounded, 'My Membership Plan', onTap: () => _push(context, const MembershipPlanScreen())),
          _menuItem(context, Icons.place_outlined, 'Manage Address', onTap: () => _push(context, const ManageAddressScreen())),
        ]),
        const SizedBox(height: 16),
        _sectionHeader('Support & Legal'),
        _menuGroup(context, [
          _menuItem(context, Icons.info_outline_rounded, 'About App', onTap: () => _push(context, const AboutAppScreen())),
          _menuItem(context, Icons.privacy_tip_outlined, 'Privacy Policy', onTap: () => _push(context, const PrivacyPolicyScreen())),
          _menuItem(context, Icons.description_outlined, 'Terms & Conditions', onTap: () => _push(context, const TermsConditionsScreen())),
          _menuItem(context, Icons.report_problem_outlined, 'Report Issue', onTap: () => _push(context, const RaiseTicketScreen())),
          _menuItem(context, Icons.confirmation_number_outlined, 'Raise Ticket', onTap: () => _push(context, const RaiseTicketScreen())),
        ]),
        const SizedBox(height: 16),
        _menuGroup(context, [
          _menuItem(context, Icons.delete_outline_rounded, 'Delete Account', color: ty.rose, onTap: () {}),
        ]),
        const SizedBox(height: 24),
        TyButton('Sign out',
            kind: TyButtonKind.ghost,
            full: true,
            leadingIcon: Icons.logout_rounded,
            onTap: () {}),
      ],
    );
  }

  Widget _vendorBanner(BuildContext context) {
    final ty = context.ty;
    return GestureDetector(
      onTap: () => AppState.instance.setPOV(UserPOV.vendor),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: ty.ink,
          borderRadius: BorderRadius.circular(24),
          boxShadow: [
            BoxShadow(color: ty.ink.withOpacity(0.1), blurRadius: 10, offset: const Offset(0, 4)),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.1),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.business_center_rounded, color: Colors.white, size: 24),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Business Account', style: TyType.sans(16, color: Colors.white, weight: FontWeight.w700)),
                  Text('Switch to Vendor POV', style: TyType.sans(12, color: Colors.white.withOpacity(0.6))),
                ],
              ),
            ),
            Icon(Icons.swap_horiz_rounded, color: Colors.white.withOpacity(0.5)),
          ],
        ),
      ),
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

  Widget _menuItem(BuildContext context, IconData icon, String label, {Color? color, VoidCallback? onTap}) {
    final ty = context.ty;
    return ListTile(
      leading: Icon(icon, color: color ?? ty.saffron, size: 22),
      title: Text(label, style: TyType.sans(14.5, color: color ?? ty.ink, weight: FontWeight.w600)),
      trailing: Icon(Icons.chevron_right_rounded, color: ty.ink3, size: 18),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16),
      onTap: onTap,
    );
  }
}
