import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_core_platform_interface/test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/test/test_flutter_secure_storage_platform.dart';
import 'package:flutter_secure_storage_platform_interface/flutter_secure_storage_platform_interface.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tyohaar/app.dart';
import 'package:tyohaar/data/auth_manager.dart';

/// Boots the app's signed-out entry screen (onboarding/auth) at each of the
/// device widths called out as must-support in the responsiveness pass —
/// 320dp (smallest common Android), 360dp/412dp (common Android), 390dp
/// (iPhone 13/14, the app's own design baseline in lib/theme/responsive.dart)
/// — plus a couple of wider references, and asserts no exception (including
/// the "A RenderFlex overflowed" / BoxConstraints assertion errors this pass
/// was fixing) was thrown while laying out at that width.
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

  const widths = <double>[320, 360, 390, 412, 480, 600];

  for (final width in widths) {
    testWidgets('boots without overflow at ${width.toInt()}dp width', (tester) async {
      final dpi = tester.view.devicePixelRatio;
      tester.view.physicalSize = Size(width * dpi, 844 * dpi);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(const TyohaarApp());
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(tester.takeException(), isNull, reason: 'Overflow/render error at ${width.toInt()}dp width');
      expect(find.byType(Scaffold), findsWidgets);
    });
  }
}
