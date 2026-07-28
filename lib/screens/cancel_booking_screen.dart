import 'package:flutter/material.dart';
import 'package:flutter/gestures.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/auth_manager.dart';
import '../data/models.dart';
import '../data/services/booking_service.dart';
import '../widgets/common.dart';
import '../widgets/ty_button.dart';
import 'cancellation_policy_screen.dart';
import '../l10n/generated/app_localizations.dart';

Map<String, String> _cancellationReasons(BuildContext context) {
  final l10n = AppLocalizations.of(context)!;
  return <String, String>{
    'change_of_plans': l10n.cancelBookingReasonChangeOfPlans,
    'found_better_option': l10n.cancelBookingReasonFoundBetterOption,
    'weather': l10n.cancelBookingReasonWeatherConcerns,
    'customer_request': l10n.cancelBookingReasonNoLongerNeeded,
    'other': l10n.cancelBookingReasonOther,
  };
}

class CancelBookingScreen extends StatefulWidget {
  final Booking booking;
  const CancelBookingScreen({super.key, required this.booking});

  @override
  State<CancelBookingScreen> createState() => _CancelBookingScreenState();
}

class _CancelBookingScreenState extends State<CancelBookingScreen> {
  final BookingService _bookingService = BookingService();
  final TextEditingController _detailCtrl = TextEditingController();
  String _reason = 'change_of_plans';
  bool _isSubmitting = false;
  BookingCancellation? _result;

  @override
  void dispose() {
    _detailCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final customerId = AuthManager.instance.currentUser?.id;
    if (customerId == null) return;
    setState(() => _isSubmitting = true);
    try {
      final result = await _bookingService.requestCancellation(
        bookingId: widget.booking.id,
        customerId: customerId,
        reason: _reason,
        reasonDetail: _detailCtrl.text.trim().isNotEmpty ? _detailCtrl.text.trim() : null,
      );
      if (mounted) setState(() => _result = result);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AppLocalizations.of(context)!.cancelBookingSubmitError)),
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;

    if (_result != null) {
      return Scaffold(
        backgroundColor: ty.paper,
        appBar: tyAppBar(context, title: l10n.cancelBookingRequestedTitle),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(20, 24, 20, 28),
          children: [
            Icon(Icons.check_circle_rounded, color: ty.leaf, size: 56),
            const SizedBox(height: 16),
            Text(l10n.cancelBookingSubmittedHeading,
                style: TyType.display(20, color: ty.ink)),
            const SizedBox(height: 8),
            Text(
              l10n.cancelBookingReviewMessage,
              style: TyType.sans(14, color: ty.ink2, height: 1.5),
            ),
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: ty.surface,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: ty.line),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _row(context, l10n.cancelBookingFeeLabel,
                      _result!.cancellationFee != null ? '₹${_result!.cancellationFee!.toStringAsFixed(0)}' : '—'),
                  const SizedBox(height: 10),
                  _row(context, l10n.cancelBookingRefundAmountLabel,
                      _result!.refundAmount != null ? '₹${_result!.refundAmount!.toStringAsFixed(0)}' : '—'),
                ],
              ),
            ),
            const SizedBox(height: 24),
            TyButton(l10n.cancelBookingDoneButtonLabel, full: true, onTap: () => Navigator.of(context).pop(true)),
          ],
        ),
      );
    }

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: l10n.cancelBookingTitle),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          Text(widget.booking.packageName ?? l10n.cancelBookingPackageFallback, style: TyType.display(20, color: ty.ink)),
          const SizedBox(height: 4),
          Text(l10n.cancelBookingNumberLabel(widget.booking.bookingNumber), style: TyType.sans(13, color: ty.ink3)),
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: ty.saffronSoft,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.info_outline_rounded, color: ty.saffronDeep, size: 18),
                const SizedBox(width: 10),
                Expanded(
                  child: RichText(
                    text: TextSpan(
                      style: TyType.sans(13, color: ty.ink2, height: 1.5),
                      children: [
                        TextSpan(text: l10n.cancelBookingFeeNoticeText),
                        TextSpan(
                          text: l10n.cancelBookingReadPolicyLinkLabel,
                          style: TyType.sans(13, color: ty.saffronDeep, weight: FontWeight.w700),
                          recognizer: TapGestureRecognizer()
                            ..onTap = () => Navigator.of(context).push(
                                MaterialPageRoute(builder: (_) => const CancellationPolicyScreen())),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          Text(l10n.cancelBookingReasonQuestionLabel, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
          const SizedBox(height: 10),
          RadioGroup<String>(
            groupValue: _reason,
            onChanged: (v) => setState(() => _reason = v!),
            child: Column(
              children: _cancellationReasons(context).entries
                  .map((e) => RadioListTile<String>(
                        value: e.key,
                        title: Text(e.value, style: TyType.sans(14, color: ty.ink)),
                        contentPadding: EdgeInsets.zero,
                        activeColor: ty.saffron,
                      ))
                  .toList(),
            ),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _detailCtrl,
            maxLines: 3,
            decoration: InputDecoration(
              hintText: l10n.cancelBookingDetailsHint,
              hintStyle: TyType.sans(13, color: ty.ink3),
              filled: true,
              fillColor: ty.surface,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: BorderSide(color: ty.line),
              ),
            ),
          ),
          const SizedBox(height: 24),
          TyButton(
            _isSubmitting ? l10n.cancelBookingSubmittingLabel : l10n.cancelBookingRequestButtonLabel,
            full: true,
            enabled: !_isSubmitting,
            onTap: _submit,
          ),
        ],
      ),
    );
  }

  Widget _row(BuildContext context, String label, String value) {
    final ty = context.ty;
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: TyType.sans(14, color: ty.ink2)),
        Text(value, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
      ],
    );
  }
}
