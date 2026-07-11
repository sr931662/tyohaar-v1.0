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

const _kCancellationReasons = <String, String>{
  'change_of_plans': 'Change of plans',
  'found_better_option': 'Found a better option',
  'weather': 'Weather concerns',
  'customer_request': 'No longer needed',
  'other': 'Other',
};

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
          const SnackBar(content: Text('Could not submit cancellation. Please try again.')),
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    if (_result != null) {
      return Scaffold(
        backgroundColor: ty.paper,
        appBar: tyAppBar(context, title: 'Cancellation Requested'),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(20, 24, 20, 28),
          children: [
            Icon(Icons.check_circle_rounded, color: ty.leaf, size: 56),
            const SizedBox(height: 16),
            Text('Your cancellation request has been submitted',
                style: TyType.display(20, color: ty.ink)),
            const SizedBox(height: 8),
            Text(
              'Our team will review it shortly. Here\'s what to expect based on our cancellation policy:',
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
                  _row(context, 'Cancellation fee',
                      _result!.cancellationFee != null ? '₹${_result!.cancellationFee!.toStringAsFixed(0)}' : '—'),
                  const SizedBox(height: 10),
                  _row(context, 'Refund amount',
                      _result!.refundAmount != null ? '₹${_result!.refundAmount!.toStringAsFixed(0)}' : '—'),
                ],
              ),
            ),
            const SizedBox(height: 24),
            TyButton('Done', full: true, onTap: () => Navigator.of(context).pop(true)),
          ],
        ),
      );
    }

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'Cancel Booking'),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          Text(widget.booking.packageName ?? 'Booking', style: TyType.display(20, color: ty.ink)),
          const SizedBox(height: 4),
          Text('Booking #${widget.booking.bookingNumber}', style: TyType.sans(13, color: ty.ink3)),
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
                        const TextSpan(text: 'A cancellation fee may apply depending on how close this is to your event date. '),
                        TextSpan(
                          text: 'Read our Cancellation & Refund Policy.',
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
          Text('Why are you cancelling?', style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
          const SizedBox(height: 10),
          ..._kCancellationReasons.entries.map((e) => RadioListTile<String>(
                value: e.key,
                groupValue: _reason,
                onChanged: (v) => setState(() => _reason = v!),
                title: Text(e.value, style: TyType.sans(14, color: ty.ink)),
                contentPadding: EdgeInsets.zero,
                activeColor: ty.saffron,
              )),
          const SizedBox(height: 8),
          TextField(
            controller: _detailCtrl,
            maxLines: 3,
            decoration: InputDecoration(
              hintText: 'Additional details (optional)',
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
            _isSubmitting ? 'Submitting…' : 'Request Cancellation',
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
