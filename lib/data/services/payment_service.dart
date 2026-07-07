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
    return PaymentOrder(
      paymentId: json['payment_id'] as String,
      orderId: json['gateway_order_id'] as String,
      currency: json['currency'] as String? ?? 'INR',
      amountPaise: (amount * 100).round(),
    );
  }
}

class WalletTopupOrder {
  final String orderId;
  final String currency;
  final int amountPaise;

  WalletTopupOrder({
    required this.orderId,
    required this.currency,
    required this.amountPaise,
  });

  factory WalletTopupOrder.fromJson(Map<String, dynamic> json) {
    final amount = (json['amount'] as num?)?.toDouble() ?? 0;
    return WalletTopupOrder(
      orderId: json['gateway_order_id'] as String,
      currency: json['currency'] as String? ?? 'INR',
      amountPaise: (amount * 100).round(),
    );
  }
}

class PaymentService {
  final ApiClient _api = ApiClient();

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

  /// Creates a gateway order to top up the customer's wallet. There is no
  /// verify step — the backend credits the wallet asynchronously once the
  /// gateway webhook confirms the capture.
  Future<WalletTopupOrder> initiateWalletTopup({required double amount}) async {
    final response = await _api.dio.post(
      'payments/wallet/topup',
      queryParameters: {'amount': amount},
    );
    return WalletTopupOrder.fromJson(response.data['data'] as Map<String, dynamic>);
  }
}
