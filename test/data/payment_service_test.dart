import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/data/api_client.dart';
import 'package:tyohaar/data/services/payment_service.dart';

class _ScriptedAdapter implements HttpClientAdapter {
  final ResponseBody Function(RequestOptions options) respond;
  RequestOptions? lastRequest;

  _ScriptedAdapter(this.respond);

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    lastRequest = options;
    return respond(options);
  }
}

ResponseBody _json(int status, String body) => ResponseBody.fromString(
      body,
      status,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );

void main() {
  late PaymentService service;
  late _ScriptedAdapter adapter;

  setUp(() {
    service = PaymentService();
    ApiClient().clearCache();
  });

  group('PaymentGatewayConfig.fromJson', () {
    test('parses a fully-configured gateway response', () {
      final config = PaymentGatewayConfig.fromJson({
        'gateway': 'razorpay',
        'key_id': 'rzp_live_abc123',
        'is_configured': true,
      });
      expect(config.gateway, 'razorpay');
      expect(config.keyId, 'rzp_live_abc123');
      expect(config.isConfigured, isTrue);
    });

    test('defaults gracefully on missing fields', () {
      final config = PaymentGatewayConfig.fromJson({});
      expect(config.gateway, 'razorpay');
      expect(config.keyId, '');
      expect(config.isConfigured, isFalse);
    });
  });

  group('PaymentOrder.fromJson', () {
    test('prefers the server-authoritative paise amount', () {
      final order = PaymentOrder.fromJson({
        'payment_id': 'p1',
        'gateway_order_id': 'order_1',
        'currency': 'INR',
        'amount': 100.0,
        'amount_paise': 10050,
      });
      expect(order.amountPaise, 10050);
    });

    test('falls back to client-side rounding when amount_paise is absent', () {
      final order = PaymentOrder.fromJson({
        'payment_id': 'p1',
        'gateway_order_id': 'order_1',
        'amount': 249.5,
      });
      expect(order.amountPaise, 24950);
      expect(order.currency, 'INR');
    });
  });

  group('PaymentService.getGatewayConfig', () {
    test('fetches and parses the runtime gateway config', () async {
      adapter = _ScriptedAdapter((opts) => _json(200, '{"data":{"gateway":"razorpay","key_id":"rzp_live_x","is_configured":true}}'));
      ApiClient().dio.httpClientAdapter = adapter;

      final config = await service.getGatewayConfig();
      expect(config.keyId, 'rzp_live_x');
      expect(adapter.lastRequest?.path, 'payments/config');
      expect(adapter.lastRequest?.method, 'GET');
    });
  });

  group('PaymentService.initiatePayment', () {
    test('posts the subtotal and fixed gateway fields', () async {
      adapter = _ScriptedAdapter((opts) => _json(
            200,
            '{"data":{"payment_id":"pay_1","gateway_order_id":"order_1","currency":"INR","amount_paise":50000}}',
          ));
      ApiClient().dio.httpClientAdapter = adapter;

      final order = await service.initiatePayment(bookingId: 'b1', subtotal: 500.0);

      expect(order.paymentId, 'pay_1');
      expect(order.orderId, 'order_1');
      expect(order.amountPaise, 50000);
      expect(adapter.lastRequest?.path, 'payments/bookings/b1');
      expect(adapter.lastRequest?.method, 'POST');
      final body = adapter.lastRequest?.data as Map;
      expect(body['subtotal'], 500.0);
      expect(body['payment_method'], 'razorpay');
    });
  });

  group('PaymentService.verifyPayment', () {
    test('sends the gateway payment id and signature as query params', () async {
      adapter = _ScriptedAdapter((opts) => _json(200, '{"data":{}}'));
      ApiClient().dio.httpClientAdapter = adapter;

      await service.verifyPayment(
        paymentId: 'pay_1',
        razorpayPaymentId: 'rzp_pay_1',
        signature: 'sig_1',
      );

      expect(adapter.lastRequest?.path, 'payments/pay_1/verify');
      expect(adapter.lastRequest?.queryParameters['gateway_payment_id'], 'rzp_pay_1');
      expect(adapter.lastRequest?.queryParameters['gateway_signature'], 'sig_1');
    });
  });
}
