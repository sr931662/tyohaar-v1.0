import 'package:flutter/material.dart';
import '../l10n/generated/app_localizations.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/ty_button.dart';
import 'root_nav.dart';

class BookingConfirmationScreen extends StatelessWidget {
  final String bookingId;
  final String packageName;
  final String date;

  const BookingConfirmationScreen({
    super.key,
    required this.bookingId,
    required this.packageName,
    required this.date,
  });

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;

    // Simulate mobile status bar notification
    Future.delayed(const Duration(seconds: 1), () {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Row(
              children: [
                const Icon(Icons.notifications_active, color: Colors.white, size: 20),
                const SizedBox(width: 12),
                Expanded(child: Text(l10n.bookingConfirmationNotificationMessage(packageName, date))),
              ],
            ),
            behavior: SnackBarBehavior.floating,
            backgroundColor: ty.saffron,
          ),
        );
      }
    });

    return Scaffold(
      backgroundColor: ty.paper,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Spacer(),
              Container(
                width: 100,
                height: 100,
                decoration: BoxDecoration(
                  color: ty.leaf.withValues(alpha: 0.1),
                  shape: BoxShape.circle,
                ),
                child: Icon(Icons.check_circle_rounded, color: ty.leaf, size: 64),
              ),
              const SizedBox(height: 32),
              Text(l10n.bookingConfirmationHeading, style: TyType.display(32, color: ty.ink), textAlign: TextAlign.center),
              const SizedBox(height: 12),
              Text(
                l10n.bookingConfirmationBodyMessage(packageName),
                style: TyType.sans(15, color: ty.ink2, height: 1.5),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 48),
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: ty.surface,
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: ty.line),
                ),
                child: Column(
                  children: [
                    _row(context, l10n.bookingConfirmationBookingIdLabel, '#${bookingId.substring(0, 8).toUpperCase()}'),
                    const Divider(height: 32),
                    _row(context, l10n.bookingConfirmationDeliveryDateLabel, date),
                    const Divider(height: 32),
                    _row(context, l10n.bookingConfirmationPackageLabel, packageName),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              TyButton(l10n.bookingConfirmationDownloadInvoiceButtonLabel, kind: TyButtonKind.ghost, full: true, leadingIcon: Icons.description_outlined, onTap: () {
                // TODO: Implement invoice download
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l10n.bookingConfirmationDownloadingInvoiceMessage)));
              }),
              const Spacer(),
              TyButton(l10n.bookingConfirmationGoToEventHubButtonLabel, full: true, onTap: () {
                Navigator.of(context).pushAndRemoveUntil(
                  MaterialPageRoute(builder: (_) => const RootNav()),
                  (route) => false,
                );
              }),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }

  Widget _row(BuildContext context, String label, String value) {
    final ty = context.ty;
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: TyType.sans(13, color: ty.ink3, weight: FontWeight.w600)),
        Text(value, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
      ],
    );
  }
}
