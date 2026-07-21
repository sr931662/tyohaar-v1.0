import '../api_client.dart';

// Replace with real key at deployment: use --dart-define=RAZORPAY_KEY_ID=rzp_live_xxxx
const String kRazorpayKeyId = String.fromEnvironment(
  'RAZORPAY_KEY_ID',
  defaultValue: 'rzp_test_PLACEHOLDER_KEY',
);

class PaymentOrder {
  final String paymentId;
  final String orderId;
  final String currency;
  final int amountPaise;

  PaymentOrder({
    required this.paymentId,
    required this.orderId,
    required this.currency,
    required this.amountPaise,
  });

  factory PaymentOrder.fromJson(Map<String, dynamic> json) {
    final amount = (json['amount'] as num?)?.toDouble() ?? 0;
    final serverAmountPaise = json['amount_paise'] as num?;
    return PaymentOrder(
      paymentId: json['payment_id'] as String,
      orderId: json['gateway_order_id'] as String,
      currency: json['currency'] as String? ?? 'INR',
      // Prefer the backend's authoritative paise amount (same figure used to
      // create the actual Razorpay order); fall back to client-side rounding
      // only if an older backend build doesn't send it yet.
      amountPaise: serverAmountPaise?.round() ?? (amount * 100).round(),
    );
  }
}

/// Public, non-secret gateway config the client needs to open checkout.
class PaymentGatewayConfig {
  final String gateway;
  final String keyId;
  final bool isConfigured;

  PaymentGatewayConfig({
    required this.gateway,
    required this.keyId,
    required this.isConfigured,
  });

  factory PaymentGatewayConfig.fromJson(Map<String, dynamic> json) {
    return PaymentGatewayConfig(
      gateway: json['gateway'] as String? ?? 'razorpay',
      keyId: json['key_id'] as String? ?? '',
      isConfigured: json['is_configured'] as bool? ?? false,
    );
  }
}

/// One discount applied within a DiscountEvaluationResponse.
class AppliedDiscount {
  final String couponId;
  final String title;
  final String? publicOfferTitle;
  final String? code;
  final double discountAmount;

  AppliedDiscount({
    required this.couponId,
    required this.title,
    this.publicOfferTitle,
    this.code,
    required this.discountAmount,
  });

  factory AppliedDiscount.fromJson(Map<String, dynamic> json) {
    return AppliedDiscount(
      couponId: json['coupon_id'] as String,
      title: json['title'] as String? ?? '',
      publicOfferTitle: json['public_offer_title'] as String?,
      code: json['code'] as String?,
      discountAmount: (json['discount_amount'] as num?)?.toDouble() ?? 0,
    );
  }
}

/// Full server-computed discount breakdown — mirrors the backend's
/// DiscountEvaluationResponse. All discount math happens server-side; the
/// app only ever displays this result, never computes discounts itself.
class DiscountPreview {
  final double originalAmount;
  final List<AppliedDiscount> appliedDiscounts;
  final double totalDiscount;
  final double finalAmount;
  final String? couponError;

  DiscountPreview({
    required this.originalAmount,
    required this.appliedDiscounts,
    required this.totalDiscount,
    required this.finalAmount,
    this.couponError,
  });

  factory DiscountPreview.fromJson(Map<String, dynamic> json) {
    return DiscountPreview(
      originalAmount: (json['original_amount'] as num?)?.toDouble() ?? 0,
      appliedDiscounts: (json['applied_discounts'] as List? ?? [])
          .map((e) => AppliedDiscount.fromJson(e as Map<String, dynamic>))
          .toList(),
      totalDiscount: (json['total_discount'] as num?)?.toDouble() ?? 0,
      finalAmount: (json['final_amount'] as num?)?.toDouble() ?? 0,
      couponError: json['coupon_error'] as String?,
    );
  }
}

class PaymentService {
  final ApiClient _api = ApiClient();

  /// Fetches the public gateway config (key_id) at runtime, so the Razorpay
  /// key lives in one place — the backend's .env — instead of a separate
  /// build-time --dart-define flag.
  Future<PaymentGatewayConfig> getGatewayConfig() async {
    final response = await _api.dio.get('payments/config');
    return PaymentGatewayConfig.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  /// Server-side discount evaluation preview — combines any automatic
  /// discounts with an optional coupon code, per the DiscountEngine's
  /// priority/stacking rules. Safe to call repeatedly (read-only).
  Future<DiscountPreview> previewDiscount({
    required double subtotal,
    String? packageId,
    String? occasionId,
    String? couponCode,
  }) async {
    final response = await _api.dio.post('payments/coupons/preview', data: {
      'subtotal': subtotal,
      if (packageId != null) 'package_id': packageId,
      if (occasionId != null) 'occasion_id': occasionId,
      if (couponCode != null && couponCode.isNotEmpty) 'coupon_code': couponCode,
    });
    return DiscountPreview.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  /// Initiates a gateway payment for a booking. `subtotal` is the pre-fee,
  /// pre-tax amount — the backend computes platform fee + GST and returns
  /// the resulting order for the full amount to charge.
  Future<PaymentOrder> initiatePayment({
    required String bookingId,
    required double subtotal,
  }) async {
    final response = await _api.dio.post('payments/bookings/$bookingId', data: {
      'currency': 'INR',
      'subtotal': subtotal,
      'discount_amount': 0,
      'tax_amount': 0,
      'final_amount': subtotal,
      'payment_method': 'razorpay',
      'gateway': 'razorpay',
    });
    return PaymentOrder.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  Future<void> verifyPayment({
    required String paymentId,
    required String razorpayPaymentId,
    required String signature,
  }) async {
    await _api.dio.get('payments/$paymentId/verify', queryParameters: {
      'gateway_payment_id': razorpayPaymentId,
      'gateway_signature': signature,
      'gateway': 'razorpay',
    });
  }
}
