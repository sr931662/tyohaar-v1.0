import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';

/// A row with a serif section title and an optional trailing action.
class SectionHeader extends StatelessWidget {
  final String title;
  final String? action;
  final VoidCallback? onAction;
  const SectionHeader(this.title, {super.key, this.action, this.onAction});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.baseline,
        textBaseline: TextBaseline.alphabetic,
        children: [
          Expanded(
            child: Text(title, style: TyType.display(21, color: ty.ink)),
          ),
          if (action != null)
            GestureDetector(
              onTap: onAction,
              child: Text(
                action!,
                style: TyType.sans(13, color: ty.saffron, weight: FontWeight.w700),
              ),
            ),
        ],
      ),
    );
  }
}

/// A pill tag used over imagery.
class TyPill extends StatelessWidget {
  final String label;
  final Color? background;
  final Color? foreground;
  const TyPill(this.label, {super.key, this.background, this.foreground});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
      decoration: BoxDecoration(
        color: background ?? Colors.white.withOpacity(0.9),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w700,
          color: foreground ?? const Color(0xFF2A2018),
        ),
      ),
    );
  }
}

/// Maps the data layer's icon keywords to Material icons.
IconData tyIcon(String name) {
  switch (name) {
    case 'chat':
      return Icons.chat_bubble_outline_rounded;
    case 'check':
      return Icons.check_circle_outline_rounded;
    case 'users':
      return Icons.group_outlined;
    case 'wallet':
      return Icons.account_balance_wallet_outlined;
    case 'spark':
      return Icons.auto_awesome;
    case 'gift':
      return Icons.card_giftcard_rounded;
    default:
      return Icons.notifications_none_rounded;
  }
}

/// A simple back-button app bar that matches the brand chrome.
AppBar tyAppBar(
  BuildContext context, {
  String? title,
  List<Widget>? actions,
}) {
  final ty = context.ty;
  return AppBar(
    backgroundColor: ty.paper,
    surfaceTintColor: Colors.transparent,
    elevation: 0,
    scrolledUnderElevation: 0,
    centerTitle: true,
    leading: Navigator.of(context).canPop()
        ? Padding(
            padding: const EdgeInsets.only(left: 14),
            child: _ChromeButton(
              icon: Icons.chevron_left_rounded,
              onTap: () => Navigator.of(context).maybePop(),
            ),
          )
        : null,
    leadingWidth: 70,
    title: title == null
        ? null
        : Text(title,
            style: TextStyle(
                color: ty.ink, fontWeight: FontWeight.w700, fontSize: 16)),
    actions: actions,
  );
}

class _ChromeButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;
  const _ChromeButton({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 42,
        height: 42,
        decoration: BoxDecoration(
          color: ty.surface,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: ty.line),
        ),
        child: Icon(icon, size: 24, color: ty.ink),
      ),
    );
  }
}

/// Exposed chrome button for use in screen actions.
class ChromeIconButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback? onTap;
  const ChromeIconButton({super.key, required this.icon, this.onTap});

  @override
  Widget build(BuildContext context) => _ChromeButton(icon: icon, onTap: onTap ?? () {});
}
