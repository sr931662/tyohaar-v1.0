import 'package:flutter/material.dart';
import 'package:razorpay_flutter/razorpay_flutter.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/auth_manager.dart';
import '../data/services/payment_service.dart';
import '../widgets/ty_button.dart';
import 'booking_confirmation_screen.dart';
import 'send_invitations_screen.dart';

class PaymentScreen extends StatefulWidget {
  final String bookingId;
  final double amount;
  final String packageName;
  final String scheduledDate;
  final String? celebrationId;
  final List<PlannedGuest> plannedGuests;

  const PaymentScreen({
    super.key,
    required this.bookingId,
    required this.amount,
    required this.packageName,
    this.scheduledDate = 'Upcoming',
    this.celebrationId,
    this.plannedGuests = const [],
  });

  @override
  State<PaymentScreen> createState() => _PaymentScreenState();
}

class _PaymentScreenState extends State<PaymentScreen> {
  final PaymentService _paymentService = PaymentService();
  late Razorpay _razorpay;
  bool _isProcessing = false;
  String? _error;
  String? _paymentId;

  @override
  void initState() {
    super.initState();
    _razorpay = Razorpay();
    _razorpay.on(Razorpay.EVENT_PAYMENT_SUCCESS, _handlePaymentSuccess);
    _razorpay.on(Razorpay.EVENT_PAYMENT_ERROR, _handlePaymentError);
    _razorpay.on(Razorpay.EVENT_EXTERNAL_WALLET, _handleExternalWallet);
  }

  @override
  void dispose() {
    _razorpay.clear();
    super.dispose();
  }

  Future<void> _startPayment() async {
    setState(() { _isProcessing = true; _error = null; });
    try {
      final config = await _paymentService.getGatewayConfig();
      final order = await _paymentService.initiatePayment(
        bookingId: widget.bookingId,
        subtotal: widget.amount,
      );
      _paymentId = order.paymentId;

      final user = AuthManager.instance.currentUser;

      final options = {
        'key': config.keyId.isNotEmpty ? config.keyId : kRazorpayKeyId,
        'amount': order.amountPaise,
        'currency': order.currency,
        'order_id': order.orderId,
        'name': 'Tyohaar',
        'description': widget.packageName,
        'prefill': {
          'contact': user?.phone ?? '',
          'email': user?.email ?? '',
          'name': user?.displayName ?? '',
        },
        'theme': {'color': '#F97316'},
        'retry': {'enabled': true, 'max_count': 3},
      };

      _razorpay.open(options);
    } catch (e) {
      if (mounted) setState(() { _isProcessing = false; _error = 'Could not initiate payment. Please try again.'; });
    }
  }

  void _handlePaymentSuccess(PaymentSuccessResponse response) async {
    setState(() => _isProcessing = true);
    try {
      await _paymentService.verifyPayment(
        paymentId: _paymentId ?? '',
        razorpayPaymentId: response.paymentId ?? '',
        signature: response.signature ?? '',
      );
      if (mounted) {
        final celebrationId = widget.celebrationId;
        if (celebrationId != null && widget.plannedGuests.isNotEmpty) {
          Navigator.of(context).pushAndRemoveUntil(
            MaterialPageRoute(
              builder: (_) => SendInvitationsScreen(
                celebrationId: celebrationId,
                bookingId: widget.bookingId,
                packageName: widget.packageName,
                date: widget.scheduledDate,
                plannedGuests: widget.plannedGuests,
              ),
            ),
            (_) => false,
          );
        } else {
          Navigator.of(context).pushAndRemoveUntil(
            MaterialPageRoute(
              builder: (_) => BookingConfirmationScreen(
                bookingId: widget.bookingId,
                packageName: widget.packageName,
                date: widget.scheduledDate,
              ),
            ),
            (_) => false,
          );
        }
      }
    } catch (_) {
      if (mounted) {
        setState(() { _isProcessing = false; _error = 'Payment received but verification failed. Contact support.'; });
      }
    }
  }

  void _handlePaymentError(PaymentFailureResponse response) {
    if (mounted) {
      setState(() {
        _isProcessing = false;
        _error = response.message ?? 'Payment failed. Please try again.';
      });
    }
  }

  void _handleExternalWallet(ExternalWalletResponse response) {
    if (mounted) setState(() => _isProcessing = false);
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: AppBar(
        backgroundColor: ty.paper,
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.close_rounded, color: ty.ink),
          onPressed: () => Navigator.of(context).maybePop(),
        ),
        title: Text('Payment', style: TyType.sans(17, color: ty.ink, weight: FontWeight.w700)),
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: ty.surface,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: ty.line),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Order Summary', style: TyType.sans(12, color: ty.ink3, weight: FontWeight.w600)),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(child: Text(widget.packageName, style: TyType.sans(16, color: ty.ink, weight: FontWeight.w700))),
                      Text('₹${widget.amount.toInt()}', style: TyType.display(20, color: ty.saffronDeep)),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text('Booking #${widget.bookingId.substring(0, 8).toUpperCase()}',
                      style: TyType.sans(12, color: ty.ink3)),
                ],
              ),
            ),
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: ty.surface2,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Row(
                children: [
                  Icon(Icons.lock_outline_rounded, color: ty.leaf, size: 18),
                  const SizedBox(width: 10),
                  Text('Secured by Razorpay — 256-bit SSL encryption',
                      style: TyType.sans(12.5, color: ty.ink2)),
                ],
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: ty.rose.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: ty.rose.withValues(alpha: 0.2)),
                ),
                child: Row(
                  children: [
                    Icon(Icons.error_outline_rounded, color: ty.rose, size: 18),
                    const SizedBox(width: 10),
                    Expanded(child: Text(_error!, style: TyType.sans(13, color: ty.rose))),
                  ],
                ),
              ),
            ],
            const Spacer(),
            TyButton(
              _isProcessing ? 'Processing...' : 'Pay ₹${widget.amount.toInt()}',
              full: true,
              icon: Icons.payment_rounded,
              enabled: !_isProcessing,
              onTap: _startPayment,
            ),
            const SizedBox(height: 12),
            Center(
              child: Text(
                'By proceeding you agree to Tyohaar\'s Terms & Conditions',
                textAlign: TextAlign.center,
                style: TyType.sans(11, color: ty.ink3),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
