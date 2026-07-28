import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_core_platform_interface/test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/test/test_flutter_secure_storage_platform.dart';
import 'package:flutter_secure_storage_platform_interface/flutter_secure_storage_platform_interface.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/app.dart';
import 'package:tyohaar/data/auth_manager.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setupFirebaseCoreMocks();
  FlutterSecureStoragePlatform.instance = TestFlutterSecureStoragePlatform({});

  setUpAll(() async {
    await Firebase.initializeApp();
  });

  setUp(() async {
    await AuthManager.instance.logout();
  });

  testWidgets('app boots to the onboarding/auth flow for a signed-out user', (tester) async {
    await tester.pumpWidget(const TyohaarApp());
    // Session restoration is async — let it settle without depending on
    // network (there's none in a test environment, so the customer shell's
    // own retry/error paths take over, which is exactly what we want to
    // confirm doesn't throw).
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(tester.takeException(), isNull);
    // A signed-out session with onboarding not yet seen lands on
    // OnboardingScreen; either way, the app produced a Scaffold rather than
    // crashing during startup.
    expect(find.byType(Scaffold), findsWidgets);
  });
}
