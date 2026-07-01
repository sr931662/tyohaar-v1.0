import 'package:flutter/material.dart';
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

  factory TyStateScreen.error({
    String? title,
    String? message,
    String? actionLabel,
    VoidCallback? onAction,
  }) {
    return TyStateScreen(
      type: TyStateType.error,
      title: title ?? 'Something went wrong',
      message: message ?? 'We encountered an unexpected error. Please try again.',
      actionLabel: actionLabel ?? 'Try Again',
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

  factory TyStateScreen.notFound({
    String? title,
    String? message,
    VoidCallback? onAction,
  }) {
    return TyStateScreen(
      type: TyStateType.notFound,
      title: title ?? "Something's missing",
      message: message ?? "The page or item you're looking for doesn't exist or has been moved.",
      actionLabel: 'Go Back',
      onAction: onAction,
      icon: Icons.search_off_rounded,
    );
  }

  factory TyStateScreen.offline({VoidCallback? onRetry}) {
    return TyStateScreen(
      type: TyStateType.offline,
      title: 'No connection',
      message: 'Please check your internet settings and try again.',
      actionLabel: 'Retry',
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
