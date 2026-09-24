import 'package:google_sign_in/google_sign_in.dart';

import '../../utils/log.dart';

/// Why a Google sign-in attempt didn't yield an ID token. The UI maps these to
/// localized copy — `cancelled` deliberately has none, since dismissing the
/// account sheet isn't an error worth reporting back to the user.
enum GoogleSignInFailureKind {
  cancelled,
  notConfigured,
  unsupported,
  noIdToken,
  failed,
}

class GoogleSignInFailure implements Exception {
  final GoogleSignInFailureKind kind;
  final String? detail;

  GoogleSignInFailure(this.kind, [this.detail]);

  bool get isCancelled => kind == GoogleSignInFailureKind.cancelled;

  @override
  String toString() => 'GoogleSignInFailure($kind${detail == null ? '' : ': $detail'})';
}

/// Wraps google_sign_in 7.x so the rest of the app only ever handles an ID
/// token string, which it posts to `auth/google` for the server to verify.
///
/// The plugin contract is that `initialize()` runs exactly once per process,
/// so it is memoised here rather than called at each button press.
class GoogleAuthService {
  Future<void>? _initialization;

  Future<void> _ensureInitialized(String serverClientId) {
    // A failed initialize must not be cached, or a transient failure would
    // permanently disable the button for the rest of the session.
    return _initialization ??= GoogleSignIn.instance
        .initialize(serverClientId: serverClientId)
        .catchError((Object e) {
      _initialization = null;
      throw GoogleSignInFailure(GoogleSignInFailureKind.failed, '$e');
    });
  }

  /// Runs the interactive Google flow and returns the ID token to send to the
  /// backend. [serverClientId] is the *web* OAuth client ID, served by
  /// `GET auth/config` — it becomes the token's `aud`, which is what the
  /// server checks against its own GOOGLE_CLIENT_ID.
  Future<String> obtainIdToken(String serverClientId) async {
    if (serverClientId.isEmpty) {
      throw GoogleSignInFailure(GoogleSignInFailureKind.notConfigured);
    }

    await _ensureInitialized(serverClientId);

    // False on platforms where Google mandates its own rendered button (web).
    // The mobile targets this app ships all support it.
    if (!GoogleSignIn.instance.supportsAuthenticate()) {
      throw GoogleSignInFailure(GoogleSignInFailureKind.unsupported);
    }

    final GoogleSignInAccount account;
    try {
      account = await GoogleSignIn.instance.authenticate();
    } on GoogleSignInException catch (e, st) {
      if (e.code != GoogleSignInExceptionCode.canceled) {
        // The UI only ever shows a generic "couldn't sign in" line, so the
        // platform's own reason was lost — and in a release build nothing
        // reached the device log either. Report it: the common production
        // cause is the app's signing certificate not matching any Android
        // OAuth client (Play re-signs an App Bundle with its own key), and
        // that is only distinguishable from a consent-screen or network
        // problem by this description.
        logError(
          'google_sign_in.authenticate [${e.code}] serverClientId=$serverClientId',
          e,
          st,
        );
      }
      throw GoogleSignInFailure(
        e.code == GoogleSignInExceptionCode.canceled
            ? GoogleSignInFailureKind.cancelled
            : GoogleSignInFailureKind.failed,
        e.description,
      );
    }

    final idToken = account.authentication.idToken;
    if (idToken == null || idToken.isEmpty) {
      // Signed in, but no ID token minted — the signature that reaches this
      // point is almost always an Android OAuth client mismatch for the
      // project that owns serverClientId.
      logError(
        'google_sign_in.noIdToken serverClientId=$serverClientId',
        StateError('Google returned an account but no ID token'),
      );
      throw GoogleSignInFailure(GoogleSignInFailureKind.noIdToken);
    }
    return idToken;
  }

  /// Clears the cached Google session so the next sign-in shows the account
  /// picker again instead of silently reusing the last account.
  Future<void> signOut() async {
    try {
      await GoogleSignIn.instance.signOut();
    } catch (_) {
      // Best-effort: never let this block the app's own logout.
    }
  }
}
