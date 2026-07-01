import '../api_client.dart';

// Replace with real key at deployment: use --dart-define=RAZORPAY_KEY_ID=rzp_live_xxxx
const String kRazorpayKeyId = String.fromEnvironment(
  'RAZORPAY_KEY_ID',
  defaultValue: 'rzp_test_PLACEHOLDER_KEY',
);

class PaymentOrder {
  final String orderId;
  final String currency;
  final int amountPaise;
  final String? bookingId;

  PaymentOrder({
    required this.orderId,
    required this.currency,
    required this.amountPaise,
    this.bookingId,
  });

  factory PaymentOrder.fromJson(Map<String, dynamic> json) {
    return PaymentOrder(
      orderId: json['gateway_order_id'] as String? ?? json['order_id'] as String,
      currency: json['currency'] as String? ?? 'INR',
      amountPaise: ((json['amount'] as num?) ?? 0).toInt(),
      bookingId: json['booking_id'] as String?,
    );
  }
}

class PaymentService {
  final ApiClient _api = ApiClient();

  Future<PaymentOrder> initiatePayment({
    required String bookingId,
    required double amount,
  }) async {
    final response = await _api.dio.post('payments/initiate', data: {
      'booking_id': bookingId,
      'amount': amount,
      'currency': 'INR',
      'payment_method': 'razorpay',
    });
    return PaymentOrder.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  Future<void> verifyPayment({
    required String paymentId,
    required String orderId,
    required String signature,
  }) async {
    await _api.dio.post('payments/verify', data: {
      'razorpay_payment_id': paymentId,
      'razorpay_order_id': orderId,
      'razorpay_signature': signature,
    });
  }
}
