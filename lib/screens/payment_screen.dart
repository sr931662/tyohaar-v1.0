import 'package:flutter/material.dart';
import 'package:razorpay_flutter/razorpay_flutter.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/auth_manager.dart';
import '../data/services/payment_service.dart';
import '../widgets/ty_button.dart';
import 'booking_confirmation_screen.dart';
import 'send_invitations_screen.dart';
import '../l10n/generated/app_localizations.dart';

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

/// What the screen is doing. The states after checkout matter most: money has
/// already left the customer's account by then, so the UI must never present
/// an unconfirmed capture as a plain failure with a "pay again" button.
enum _PayPhase {
  idle,

  /// Creating the order and opening the gateway sheet.
  starting,

  /// Checkout closed successfully; confirming the capture with our backend.
  confirming,

  /// Verification did not go through. The gateway took the money, so we are
  /// asking the server what it thinks rather than telling the customer it
  /// failed.
  reconciling,

  /// Money taken, capture still unconfirmed. Terminal for this screen —
  /// paying again here would double-charge.
  unconfirmed,
}

class _PaymentScreenState extends State<PaymentScreen> {
  /// Verification is retried before falling back to reconciliation: the
  /// common failure is a momentary network drop right after checkout, and
  /// the endpoint is idempotent, so retrying is both safe and usually enough.
  static const List<Duration> _verifyBackoff = [
    Duration(seconds: 1),
    Duration(seconds: 3),
    Duration(seconds: 6),
  ];

  /// How long to keep asking the server whether the capture webhook landed.
  /// Razorpay normally delivers within seconds; this is the outer bound
  /// before handing the customer a "we're still confirming" message.
  static const List<Duration> _reconcileBackoff = [
    Duration(seconds: 2),
    Duration(seconds: 4),
    Duration(seconds: 6),
    Duration(seconds: 8),
    Duration(seconds: 10),
  ];

  final PaymentService _paymentService = PaymentService();
  late Razorpay _razorpay;
  _PayPhase _phase = _PayPhase.idle;
  String? _error;
  String? _notice;
  String? _paymentId;

  bool get _isBusy => _phase != _PayPhase.idle && _phase != _PayPhase.unconfirmed;

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
    // Guard the whole flow, not just the button: a checkout opened twice
    // creates two gateway orders against one booking.
    if (_isBusy) return;
    setState(() { _phase = _PayPhase.starting; _error = null; _notice = null; });
    try {
      final config = await _paymentService.getGatewayConfig();
      if (!config.isUsable) {
        // No key from the server and none compiled in — opening checkout
        // would just produce a gateway-side error the customer can't act on.
        if (mounted) {
          setState(() {
            _phase = _PayPhase.idle;
            _error = AppLocalizations.of(context)!.paymentUnavailableError;
          });
        }
        return;
      }

      final order = await _paymentService.initiatePayment(
        bookingId: widget.bookingId,
        subtotal: widget.amount,
      );
      _paymentId = order.paymentId;

      final user = AuthManager.instance.currentUser;

      final options = {
        'key': config.effectiveKeyId,
        // Server-derived paise, never re-derived from the rupee decimal —
        // the figure must match the order the backend actually created.
        'amount': order.amountPaise,
        'currency': order.currency,
        'order_id': order.orderId,
        'name': 'Tyohaar',
        'description': widget.packageName,
        'prefill': {
          // Never prefill the `TMP-<hex>` placeholder — Razorpay would reject
          // it as a contact number and block the checkout sheet.
          'contact': user?.displayPhone ?? '',
          'email': user?.email ?? '',
          'name': user?.displayName ?? '',
        },
        // Echoed back on the payment and visible in the Razorpay dashboard —
        // what support reconciles against when a capture needs chasing.
        'notes': {
          'booking_id': widget.bookingId,
          'payment_id': order.paymentId,
        },
        'theme': {'color': '#F97316'},
        // Matches the backend's PAYMENT_EXPIRY_SECONDS window, so the sheet
        // cannot outlive the payment row it belongs to.
        'timeout': 900,
      };

      _razorpay.open(options);
    } catch (_) {
      if (mounted) {
        setState(() {
          _phase = _PayPhase.idle;
          _error = AppLocalizations.of(context)!.paymentInitiateError;
        });
      }
    }
  }

  Future<void> _handlePaymentSuccess(PaymentSuccessResponse response) async {
    final paymentId = _paymentId;
    if (paymentId == null || paymentId.isEmpty) {
      // Should not happen — checkout cannot open without an order — but the
      // money is gone either way, so reconcile rather than report failure.
      await _reconcile(moneyLeftAccount: true);
      return;
    }

    if (mounted) setState(() { _phase = _PayPhase.confirming; _error = null; });

    for (var attempt = 0; attempt <= _verifyBackoff.length; attempt++) {
      try {
        await _paymentService.verifyPayment(
          paymentId: paymentId,
          razorpayPaymentId: response.paymentId ?? '',
          signature: response.signature ?? '',
        );
        _onConfirmed();
        return;
      } catch (_) {
        if (attempt < _verifyBackoff.length) {
          await Future<void>.delayed(_verifyBackoff[attempt]);
          if (!mounted) return;
        }
      }
    }

    // Verification never went through. The capture webhook reaches the
    // backend independently of this app, so ask the server before deciding
    // anything is wrong.
    await _reconcile(moneyLeftAccount: true);
  }

  /// Polls the server's view of the payment. The webhook path completes a
  /// capture without the client's help, so this turns most verification
  /// failures into an ordinary success.
  ///
  /// [moneyLeftAccount] says whether checkout already reported success. It
  /// decides what an inconclusive poll means: after a confirmed capture the
  /// customer has paid and must be told not to pay again, but an external
  /// wallet handoff may simply never have been completed — telling that
  /// customer "payment received" would be a false claim, and would strand a
  /// booking they could still pay for.
  Future<void> _reconcile({required bool moneyLeftAccount}) async {
    final paymentId = _paymentId;
    if (paymentId == null || paymentId.isEmpty) {
      _settleInconclusive(moneyLeftAccount: moneyLeftAccount);
      return;
    }

    if (mounted) setState(() { _phase = _PayPhase.reconciling; _error = null; });

    for (var attempt = 0; attempt <= _reconcileBackoff.length; attempt++) {
      try {
        final status = await _paymentService.getPaymentStatus(paymentId);
        if (status.isCompleted) {
          _onConfirmed();
          return;
        }
        // Anything else terminal (failed/cancelled/expired) is a real
        // failure the customer can retry from.
        if (status.isTerminal) {
          if (mounted) {
            setState(() {
              _phase = _PayPhase.idle;
              _error = AppLocalizations.of(context)!.paymentFailedError;
            });
          }
          return;
        }
      } catch (_) {
        // Network error mid-poll — keep trying within the window.
      }
      if (attempt < _reconcileBackoff.length) {
        await Future<void>.delayed(_reconcileBackoff[attempt]);
        if (!mounted) return;
      }
    }

    _settleInconclusive(moneyLeftAccount: moneyLeftAccount);
  }

  /// The poll ran out without a verdict. What to show depends entirely on
  /// whether the customer has actually been charged.
  void _settleInconclusive({required bool moneyLeftAccount}) {
    if (!mounted) return;
    if (moneyLeftAccount) {
      _onUnconfirmed();
      return;
    }
    // Nothing is known to have been paid — leave the customer able to retry
    // rather than claiming a payment that may never have happened.
    setState(() {
      _phase = _PayPhase.idle;
      _notice = AppLocalizations.of(context)!.paymentStillPendingMessage;
    });
  }

  void _onConfirmed() {
    if (!mounted) return;
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

  void _onUnconfirmed() {
    if (mounted) setState(() { _phase = _PayPhase.unconfirmed; _error = null; });
  }

  void _handlePaymentError(PaymentFailureResponse response) {
    // Close the payment row out server-side. Razorpay sends no webhook for an
    // attempt the customer abandoned, so without this the row stays PENDING
    // and keeps counting toward vendor pending totals.
    final paymentId = _paymentId;
    if (paymentId != null && paymentId.isNotEmpty) {
      _paymentService
          .reportPaymentAbandoned(
            paymentId: paymentId,
            reasonCode: response.code?.toString(),
            reasonDescription: response.message,
          )
          .catchError((_) {});
    }

    if (!mounted) return;
    final l10n = AppLocalizations.of(context)!;
    // Dismissing the sheet is a cancellation, not an error worth alarming
    // anyone with — no money moved.
    final cancelled = response.code == Razorpay.PAYMENT_CANCELLED;
    setState(() {
      _phase = _PayPhase.idle;
      _error = cancelled ? null : (response.message ?? l10n.paymentFailedError);
      _notice = cancelled ? l10n.paymentCancelledMessage : null;
    });
  }

  void _handleExternalWallet(ExternalWalletResponse response) {
    if (!mounted) return;
    // The wallet app takes over from here; the capture arrives by webhook, so
    // poll rather than leaving the customer on a dead screen.
    final message = AppLocalizations.of(context)!
        .paymentExternalWalletMessage(response.walletName ?? 'your wallet');
    setState(() => _notice = message);
    _reconcile(moneyLeftAccount: false);
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    // Between a successful checkout and a confirmed capture there is money in
    // flight. Leaving now would drop the reconciliation poll and strand the
    // booking, so hold the screen until it settles one way or the other.
    final locked = _phase == _PayPhase.confirming || _phase == _PayPhase.reconciling;

    return PopScope(
      canPop: !locked,
      child: Scaffold(
      backgroundColor: ty.paper,
      appBar: AppBar(
        backgroundColor: ty.paper,
        elevation: 0,
        leading: locked
            ? null
            : IconButton(
                icon: Icon(Icons.close_rounded, color: ty.ink),
                onPressed: () => Navigator.of(context).maybePop(),
              ),
        title: Text(AppLocalizations.of(context)!.paymentTitle, style: TyType.sans(17, color: ty.ink, weight: FontWeight.w700)),
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
                  Text(AppLocalizations.of(context)!.paymentOrderSummaryLabel, style: TyType.sans(12, color: ty.ink3, weight: FontWeight.w600)),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(child: Text(widget.packageName, style: TyType.sans(16, color: ty.ink, weight: FontWeight.w700))),
                      Text('₹${widget.amount.toInt()}', style: TyType.display(20, color: ty.saffronDeep)),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(AppLocalizations.of(context)!.paymentBookingNumberLabel(widget.bookingId.substring(0, 8).toUpperCase()),
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
                  Text(AppLocalizations.of(context)!.paymentSecuredByRazorpayLabel,
                      style: TyType.sans(12.5, color: ty.ink2)),
                ],
              ),
            ),
            if (_notice != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: ty.surface2,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: ty.line),
                ),
                child: Row(
                  children: [
                    Icon(Icons.info_outline_rounded, color: ty.ink2, size: 18),
                    const SizedBox(width: 10),
                    Expanded(child: Text(_notice!, style: TyType.sans(13, color: ty.ink2))),
                  ],
                ),
              ),
            ],
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
            if (_phase == _PayPhase.unconfirmed) ...[
              const SizedBox(height: 16),
              _unconfirmedPanel(ty),
            ],
            const Spacer(),
            ..._footer(ty),
          ],
        ),
      ),
      ),
    );
  }

  /// Money taken, capture unconfirmed. Deliberately not styled as an error
  /// and deliberately offering no "pay" button — the one thing the customer
  /// must not do here is pay a second time.
  Widget _unconfirmedPanel(TyColors ty) {
    final l10n = AppLocalizations.of(context)!;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: ty.saffronSoft,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: ty.saffron.withValues(alpha: 0.35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.schedule_rounded, color: ty.saffronDeep, size: 18),
              const SizedBox(width: 10),
              Expanded(
                child: Text(l10n.paymentUnconfirmedTitle,
                    style: TyType.sans(14, color: ty.ink, weight: FontWeight.w700)),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(l10n.paymentUnconfirmedMessage, style: TyType.sans(12.5, color: ty.ink2)),
        ],
      ),
    );
  }

  List<Widget> _footer(TyColors ty) {
    final l10n = AppLocalizations.of(context)!;

    if (_phase == _PayPhase.unconfirmed) {
      return [
        TyButton(
          l10n.paymentCheckAgainButtonLabel,
          full: true,
          icon: Icons.refresh_rounded,
          // Reached only from the unconfirmed state, which is entered only
          // after checkout reported success — the money is known to be gone.
          onTap: () => _reconcile(moneyLeftAccount: true),
        ),
        const SizedBox(height: 12),
      ];
    }

    final confirming =
        _phase == _PayPhase.confirming || _phase == _PayPhase.reconciling;

    return [
      TyButton(
        confirming
            ? l10n.paymentConfirmingLabel
            : _isBusy
                ? l10n.paymentProcessingLabel
                : l10n.paymentPayButtonLabel('${widget.amount.toInt()}'),
        full: true,
        icon: Icons.payment_rounded,
        enabled: !_isBusy,
        onTap: _startPayment,
      ),
      const SizedBox(height: 12),
      Center(
        child: Text(
          // While a capture is being confirmed, leaving the screen is the
          // thing most likely to strand the booking — say so instead of
          // showing the terms line.
          confirming ? l10n.paymentDoNotCloseLabel : l10n.paymentTermsAgreementLabel,
          textAlign: TextAlign.center,
          style: TyType.sans(11, color: ty.ink3),
        ),
      ),
    ];
  }
}
