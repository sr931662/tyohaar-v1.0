import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:tyohaar/data/models.dart';
import 'package:tyohaar/data/services/auth_service.dart';
import 'package:tyohaar/data/sign_in_identifier.dart';
import 'package:tyohaar/l10n/generated/app_localizations.dart';
import 'package:tyohaar/screens/auth/code_sign_in_panel.dart';
import 'package:tyohaar/theme/theme.dart';

class _FakeAuth extends AuthService {
  final List<String> sent = [];
  final List<String> verified = [];
  Object? sendError;
  Object? verifyError;

  @override
  Future<void> requestSignInCode(SignInIdentifier id) async {
    if (sendError != null) throw sendError!;
    sent.add(id.value);
  }

  @override
  Future<CodeSignInResult> verifySignInCode(SignInIdentifier id, String code) async {
    if (verifyError != null) throw verifyError!;
    verified.add('${id.value}:$code');
    return CodeSignInResult(
      AuthCredentials(accessToken: 'a', refreshToken: 'r', user: User(id: 'u', role: 'customer', status: 'active')),
      true,
    );
  }
}

DioException _serverError(String message) => DioException(
      requestOptions: RequestOptions(path: '/'),
      response: Response(
        requestOptions: RequestOptions(path: '/'),
        statusCode: 401,
        data: {'error': {'code': 'X', 'message': message}},
      ),
    );

void main() {
  late _FakeAuth auth;
  final signedIn = <CodeSignInResult>[];

  Widget host({bool phone = true, bool email = true}) => Provider<AuthService>.value(
        value: auth,
        child: MaterialApp(
          theme: buildTyTheme(Brightness.light),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: Scaffold(
            body: SingleChildScrollView(
              child: CodeSignInPanel(
                phoneEnabled: phone,
                emailEnabled: email,
                onSignedIn: (r) async => signedIn.add(r),
              ),
            ),
          ),
        ),
      );

  setUp(() {
    auth = _FakeAuth();
    signedIn.clear();
  });

  testWidgets('mobile number -> code -> signed in, with no extra tap after 6 digits', (tester) async {
    await tester.pumpWidget(host());
    await tester.enterText(find.byType(TextField), '98765 43210');
    await tester.tap(find.text('Send code'));
    await tester.pumpAndSettle();

    expect(auth.sent, ['+919876543210']);
    expect(find.textContaining('+91 98765 43210'), findsOneWidget);
    expect(find.textContaining('notification'), findsOneWidget); // push hint

    await tester.enterText(find.byType(TextField), '482913');
    await tester.pumpAndSettle();
    expect(auth.verified, ['+919876543210:482913']);
    expect(signedIn.single.isNewUser, isTrue);
  });

  testWidgets('email works the same way', (tester) async {
    await tester.pumpWidget(host());
    await tester.enterText(find.byType(TextField), 'Asha@Example.com');
    await tester.tap(find.text('Send code'));
    await tester.pumpAndSettle();
    expect(auth.sent, ['asha@example.com']);
  });

  testWidgets('a mobile number is refused clearly when SMS is not available', (tester) async {
    await tester.pumpWidget(host(phone: false));
    await tester.enterText(find.byType(TextField), '9876543210');
    await tester.tap(find.text('Send code'));
    await tester.pumpAndSettle();
    expect(auth.sent, isEmpty);
    expect(find.textContaining("isn't available yet"), findsOneWidget);
  });

  testWidgets('nonsense input is caught before calling the server', (tester) async {
    await tester.pumpWidget(host());
    await tester.enterText(find.byType(TextField), '12345');
    await tester.tap(find.text('Send code'));
    await tester.pumpAndSettle();
    expect(auth.sent, isEmpty);
    expect(find.textContaining('valid 10-digit'), findsOneWidget);
  });

  testWidgets("the server's own message is shown, not a generic one", (tester) async {
    auth.verifyError = _serverError('Incorrect OTP. Please try again.');
    await tester.pumpWidget(host());
    await tester.enterText(find.byType(TextField), '9876543210');
    await tester.tap(find.text('Send code'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), '000000');
    await tester.pumpAndSettle();
    expect(find.text('Incorrect OTP. Please try again.'), findsOneWidget);
    expect(signedIn, isEmpty);
  });

  testWidgets('resend waits for the cooldown, and Change goes back', (tester) async {
    await tester.pumpWidget(host());
    await tester.enterText(find.byType(TextField), '9876543210');
    await tester.tap(find.text('Send code'));
    await tester.pump();
    expect(find.textContaining('Resend code in'), findsOneWidget);
    await tester.pump(const Duration(seconds: 31));
    await tester.tap(find.text('Resend code'));
    await tester.pump();
    expect(auth.sent.length, 2);
    await tester.tap(find.text('Change'));
    await tester.pumpAndSettle();
    expect(find.text('Send code'), findsOneWidget);
  });
}
