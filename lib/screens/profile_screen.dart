import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../theme/theme_controller.dart';
import '../theme/responsive.dart';
import '../widgets/common.dart';
import '../widgets/ty_button.dart';

/// Profile — identity, households, payments and settings.
class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  static const _menu = [
    [Icons.group_outlined, 'Households & family', '3 groups'],
    [Icons.account_balance_wallet_outlined, 'Payment methods', '2 cards'],
    [Icons.notifications_none_rounded, 'Notifications', ''],
    [Icons.shield_outlined, 'Privacy & security', ''],
    [Icons.help_outline_rounded, 'Help & support', ''],
  ];

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    return ListView(
      padding: EdgeInsets.fromLTRB(resp.w(18), resp.h(12), resp.w(18), resp.h(28)),
      children: [
        Row(
          children: [
            Expanded(child: Text('You', style: TyType.display(resp.sp(26), color: ty.ink))),
            ChromeIconButton(
              icon: themeController.isDark ? Icons.wb_sunny_outlined : Icons.nightlight_round,
              onTap: themeController.toggle,
            ),
          ],
        ),
        SizedBox(height: resp.h(24)),
        // identity
        Column(
          children: [
            Container(
              width: resp.w(84),
              height: resp.w(84),
              alignment: Alignment.center,
              decoration: BoxDecoration(color: ty.saffron, shape: BoxShape.circle),
              child: Text('A',
                  style: TextStyle(
                      color: ty.onPrimary, fontWeight: FontWeight.w800, fontSize: resp.sp(34))),
            ),
            SizedBox(height: resp.h(12)),
            Text('Aarav Sharma', style: TyType.display(resp.sp(25), color: ty.ink)),
            SizedBox(height: resp.h(2)),
            Text('aarav.sharma@gmail.com · Jaipur',
                style: TyType.sans(resp.sp(13), color: ty.ink2)),
            SizedBox(height: resp.h(10)),
            Container(
              padding: EdgeInsets.symmetric(horizontal: resp.w(12), vertical: resp.h(6)),
              decoration: BoxDecoration(
                color: ty.saffronSoft,
                borderRadius: BorderRadius.circular(999),
              ),
              child: Text('✦ Member since 2024',
                  style: TyType.sans(resp.sp(12.5), color: ty.saffronDeep, weight: FontWeight.w700)),
            ),
          ],
        ),
        SizedBox(height: resp.h(24)),
        // stats
        Row(
          children: [
            _stat(context, '7', 'Celebrations'),
            SizedBox(width: resp.w(10)),
            _stat(context, '684', 'Photos'),
            SizedBox(width: resp.w(10)),
            _stat(context, '12', 'Saved partners'),
          ],
        ),
        SizedBox(height: resp.h(24)),
        // menu
        Container(
          decoration: BoxDecoration(
            color: ty.surface,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: ty.line),
          ),
          child: Column(
            children: [
              for (int i = 0; i < _menu.length; i++)
                _menuRow(context, _menu[i], last: i == _menu.length - 1),
            ],
          ),
        ),
        SizedBox(height: resp.h(18)),
        TyButton('Sign out',
            kind: TyButtonKind.ghost,
            full: true,
            leadingIcon: Icons.logout_rounded,
            onTap: () {}),
      ],
    );
  }

  Widget _stat(BuildContext context, String n, String l) {
    final ty = context.ty;
    final resp = context.resp;
    return Expanded(
      child: Container(
        padding: EdgeInsets.symmetric(vertical: resp.h(15), horizontal: resp.w(6)),
        decoration: BoxDecoration(
          color: ty.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: ty.line),
        ),
        child: Column(
          children: [
            Text(n, style: TyType.display(resp.sp(26), color: ty.ink)),
            SizedBox(height: resp.h(5)),
            Text(l, style: TyType.sans(resp.sp(11), color: ty.ink2), textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }

  Widget _menuRow(BuildContext context, List item, {bool last = false}) {
    final ty = context.ty;
    final resp = context.resp;
    return Container(
      padding: EdgeInsets.symmetric(horizontal: resp.w(16), vertical: resp.h(15)),
      decoration: BoxDecoration(
        border: last ? null : Border(bottom: BorderSide(color: ty.line2)),
      ),
      child: Row(
        children: [
          Container(
            width: resp.w(38),
            height: resp.w(38),
            decoration: BoxDecoration(
              color: ty.surface2,
              borderRadius: BorderRadius.circular(11),
            ),
            child: Icon(item[0] as IconData, color: ty.saffron, size: resp.w(19)),
          ),
          SizedBox(width: resp.w(13)),
          Expanded(
            child: Text(item[1] as String,
                style: TyType.sans(resp.sp(14.5), color: ty.ink, weight: FontWeight.w600)),
          ),
          if ((item[2] as String).isNotEmpty)
            Text(item[2] as String, style: TyType.sans(resp.sp(12.5), color: ty.ink3)),
          SizedBox(width: resp.w(6)),
          Icon(Icons.chevron_right_rounded, color: ty.ink3, size: resp.w(18)),
        ],
      ),
    );
  }
}
