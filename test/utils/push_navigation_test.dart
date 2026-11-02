import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/utils/push_navigation.dart';

void main() {
  testWidgets('links the app cannot show are ignored without throwing', (tester) async {
    await tester.pumpWidget(MaterialApp(navigatorKey: rootNavigatorKey, home: const Scaffold()));
    // Vendor links, unknown links, empty and null: all quietly do nothing.
    openFromPush('/vendor/bookings/abc');
    openFromPush('/somewhere/else');
    openFromPush('');
    openFromPush(null);
    await tester.pump();
    expect(find.byType(Scaffold), findsOneWidget);
    expect(rootNavigatorKey.currentState!.canPop(), isFalse);
  });

  testWidgets('a booking link while signed out does not open account screens', (tester) async {
    await tester.pumpWidget(MaterialApp(navigatorKey: rootNavigatorKey, home: const Scaffold()));
    openFromPush('/bookings/123e4567-e89b-12d3-a456-426614174000');
    await tester.pump();
    expect(rootNavigatorKey.currentState!.canPop(), isFalse);
  });
}
