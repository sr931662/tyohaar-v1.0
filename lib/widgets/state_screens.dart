import 'package:flutter/material.dart';
import '../l10n/generated/app_localizations.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import 'ty_button.dart';

enum TyStateType { error, empty, notFound, offline }

class TyStateScreen extends StatelessWidget {
  final TyStateType type;
  final String? title;
  final String? message;
  final String? actionLabel;
  final VoidCallback? onAction;
  final IconData? icon;

  const TyStateScreen({
    super.key,
    required this.type,
    this.title,
    this.message,
    this.actionLabel,
    this.onAction,
    this.icon,
  });

  factory TyStateScreen.error(
    BuildContext context, {
    String? title,
    String? message,
    String? actionLabel,
    VoidCallback? onAction,
  }) {
    final l10n = AppLocalizations.of(context)!;
    return TyStateScreen(
      type: TyStateType.error,
      title: title ?? l10n.commonSomethingWentWrong,
      message: message ?? l10n.commonUnexpectedErrorMessage,
      actionLabel: actionLabel ?? l10n.commonTryAgain,
      onAction: onAction,
      icon: Icons.error_outline_rounded,
    );
  }

  factory TyStateScreen.empty({
    required String title,
    required String message,
    String? actionLabel,
    VoidCallback? onAction,
    IconData? icon,
  }) {
    return TyStateScreen(
      type: TyStateType.empty,
      title: title,
      message: message,
      actionLabel: actionLabel,
      onAction: onAction,
      icon: icon ?? Icons.inbox_rounded,
    );
  }

  factory TyStateScreen.notFound(
    BuildContext context, {
    String? title,
    String? message,
    VoidCallback? onAction,
  }) {
    final l10n = AppLocalizations.of(context)!;
    return TyStateScreen(
      type: TyStateType.notFound,
      title: title ?? l10n.commonSomethingMissing,
      message: message ?? l10n.commonNotFoundMessage,
      actionLabel: l10n.commonGoBack,
      onAction: onAction,
      icon: Icons.search_off_rounded,
    );
  }

  factory TyStateScreen.offline(BuildContext context, {VoidCallback? onRetry}) {
    final l10n = AppLocalizations.of(context)!;
    return TyStateScreen(
      type: TyStateType.offline,
      title: l10n.commonNoConnection,
      message: l10n.commonNoConnectionMessage,
      actionLabel: l10n.commonRetry,
      onAction: onRetry,
      icon: Icons.wifi_off_rounded,
    );
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final color = type == TyStateType.error || type == TyStateType.offline ? ty.rose : ty.saffron;

    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 40),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 100,
              height: 100,
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.1),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, size: 48, color: color),
            ),
            const SizedBox(height: 32),
            Text(
              title!,
              textAlign: TextAlign.center,
              style: TyType.display(24, color: ty.ink),
            ),
            const SizedBox(height: 12),
            Text(
              message!,
              textAlign: TextAlign.center,
              style: TyType.sans(15, color: ty.ink2, height: 1.5),
            ),
            if (onAction != null) ...[
              const SizedBox(height: 32),
              TyButton(
                actionLabel!,
                onTap: onAction,
                padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 14),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
