import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';

import 'auth_manager.dart';

class _CacheEntry {
  final dynamic data;
  final DateTime savedAt;
  _CacheEntry(this.data, this.savedAt);
  Duration get age => DateTime.now().difference(savedAt);
}

/// Opt-in GET response cache, kept in memory and mirrored to disk so it
/// survives app restarts. Services mark a request cacheable with
/// `options.extra['cache'] = true`, plus optional `cacheTtl` (how long a
/// response counts as fresh) and `cacheMaxStale` (how long past that a stale
/// copy may still be shown while a fresh one is fetched; zero disables it).
/// Nothing is cached by default, so user/booking-specific data is unaffected.
/// Only public catalog data (occasions, packages, themes, etc.) opts in.
///
/// Lookup order for a cacheable GET:
///  * fresh entry (age < ttl): served at once, no network.
///  * stale entry (age < ttl + maxStale): served at once, and the response
///    is re-fetched in the background so the next read is fresh. This is
///    what makes cold starts and repeat visits render without a spinner.
///  * nothing usable: normal network request. If that fails with a network
///    error and any cached copy exists, the copy is served (offline mode).
///
/// Identical cacheable GETs that are already in flight share a single
/// network request instead of each opening their own.
class _ResponseCacheInterceptor extends Interceptor {
  _ResponseCacheInterceptor(this._dio);

  final Dio _dio;
  final Map<String, _CacheEntry> _memory = {};
  final Map<String, List<_Waiter>> _inFlight = {};
  Directory? _dir;
  Future<Directory?>? _dirFuture;

  static const _defaultTtl = Duration(minutes: 10);
  static const _defaultMaxStale = Duration(days: 3);
  static const _kRevalidate = 'cacheRevalidate';

  String _keyFor(RequestOptions options) => '${options.method}:${options.uri}';

  bool _isCacheable(RequestOptions o) =>
      o.extra['cache'] == true && o.method.toUpperCase() == 'GET';

  Duration _ttl(RequestOptions o) => o.extra['cacheTtl'] as Duration? ?? _defaultTtl;
  Duration _maxStale(RequestOptions o) =>
      o.extra['cacheMaxStale'] as Duration? ?? _defaultMaxStale;

  Future<Directory?> _cacheDir() {
    if (kIsWeb) return Future.value(null);
    if (_dir != null) return Future.value(_dir);
    return _dirFuture ??= () async {
      try {
        final base = await getApplicationCacheDirectory();
        final dir = Directory('${base.path}/api_cache');
        if (!await dir.exists()) await dir.create(recursive: true);
        return _dir = dir;
      } catch (_) {
        return null;
      }
    }();
  }

  /// Stable across runs (unlike String.hashCode), so it can name files.
  static String _fileName(String key) {
    var h = 0xcbf29ce484222325;
    for (final c in key.codeUnits) {
      h ^= c;
      h = (h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF;
    }
    return '${h.toRadixString(16)}.json';
  }

  Future<_CacheEntry?> _read(String key) async {
    final mem = _memory[key];
    if (mem != null) return mem;
    final dir = await _cacheDir();
    if (dir == null) return null;
    try {
      final file = File('${dir.path}/${_fileName(key)}');
      if (!await file.exists()) return null;
      final decoded = jsonDecode(await file.readAsString()) as Map<String, dynamic>;
      // The key is stored inside the file to rule out hash collisions.
      if (decoded['k'] != key) return null;
      final entry = _CacheEntry(
        decoded['d'],
        DateTime.fromMillisecondsSinceEpoch(decoded['t'] as int),
      );
      _memory[key] = entry;
      return entry;
    } catch (_) {
      return null;
    }
  }

  void _write(String key, dynamic data) {
    final entry = _CacheEntry(data, DateTime.now());
    _memory[key] = entry;
    // Fire-and-forget: a slow or failed disk write must never hold up the
    // response the screen is waiting on.
    () async {
      final dir = await _cacheDir();
      if (dir == null) return;
      try {
        await File('${dir.path}/${_fileName(key)}').writeAsString(jsonEncode({
          'k': key,
          't': entry.savedAt.millisecondsSinceEpoch,
          'd': data,
        }));
      } catch (_) {}
    }();
  }

  Response _responseFrom(RequestOptions options, _CacheEntry entry) => Response(
        requestOptions: options,
        data: entry.data,
        statusCode: 200,
        extra: {'fromCache': true},
      );

  void _revalidateInBackground(RequestOptions options) {
    final key = _keyFor(options);
    if (_inFlight.containsKey(key)) return;
    final opts = options.copyWith(
      extra: {...options.extra, _kRevalidate: true},
    );
    _dio.fetch(opts).catchError((Object _) => Response(requestOptions: opts));
  }

  @override
  Future<void> onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    if (!_isCacheable(options)) return handler.next(options);
    final key = _keyFor(options);

    if (options.extra[_kRevalidate] != true) {
      final entry = await _read(key);
      if (entry != null) {
        final ttl = _ttl(options);
        if (entry.age < ttl) {
          return handler.resolve(_responseFrom(options, entry));
        }
        if (entry.age < ttl + _maxStale(options)) {
          handler.resolve(_responseFrom(options, entry));
          _revalidateInBackground(options);
          return;
        }
      }
    }

    // Join an identical request that is already on the wire.
    final waiters = _inFlight[key];
    if (waiters != null) {
      waiters.add(_Waiter(options, handler));
      return;
    }
    _inFlight[key] = [];
    return handler.next(options);
  }

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    final options = response.requestOptions;
    if (_isCacheable(options)) {
      final key = _keyFor(options);
      if (response.statusCode == 200) _write(key, response.data);
      for (final w in _inFlight.remove(key) ?? const <_Waiter>[]) {
        w.handler.resolve(Response(
          requestOptions: w.options,
          data: response.data,
          statusCode: response.statusCode,
          headers: response.headers,
        ));
      }
    }
    return handler.next(response);
  }

  @override
  Future<void> onError(DioException err, ErrorInterceptorHandler handler) async {
    final options = err.requestOptions;
    if (!_isCacheable(options)) return handler.next(err);
    final key = _keyFor(options);
    final waiters = _inFlight.remove(key) ?? const <_Waiter>[];

    // Offline / server unreachable: any cached copy beats an error screen.
    final isNetworkFailure = err.response == null && err.type != DioExceptionType.cancel;
    final entry = isNetworkFailure ? await _read(key) : null;
    if (entry != null && options.extra[_kRevalidate] != true) {
      for (final w in waiters) {
        w.handler.resolve(_responseFrom(w.options, entry));
      }
      return handler.resolve(_responseFrom(options, entry));
    }
    for (final w in waiters) {
      w.handler.reject(err.copyWith(requestOptions: w.options));
    }
    return handler.next(err);
  }

  Future<void> clear() async {
    _memory.clear();
    final dir = await _cacheDir();
    if (dir == null) return;
    try {
      if (await dir.exists()) {
        await dir.delete(recursive: true);
        await dir.create(recursive: true);
      }
    } catch (_) {}
  }
}

class _Waiter {
  final RequestOptions options;
  final RequestInterceptorHandler handler;
  _Waiter(this.options, this.handler);
}

/// Retries idempotent GET requests on transient network failures
/// (connection/receive/send timeouts, connection errors, and 502/503/504)
/// with exponential backoff. Never retries non-GET requests — retrying a
/// POST/PUT/DELETE blindly risks duplicating a booking/payment/etc. Never
/// retries 4xx responses, since those won't succeed on a second attempt.
class _RetryInterceptor extends Interceptor {
  final Dio _dio;
  static const _maxRetries = 2;
  static const _baseDelay = Duration(milliseconds: 500);

  _RetryInterceptor(this._dio);

  bool _isRetryable(DioException e) {
    if (e.requestOptions.method.toUpperCase() != 'GET') return false;
    final status = e.response?.statusCode;
    if (status != null) return status == 502 || status == 503 || status == 504;
    return e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout ||
        e.type == DioExceptionType.sendTimeout ||
        e.type == DioExceptionType.connectionError;
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    final attempt = (err.requestOptions.extra['retryAttempt'] as int?) ?? 0;
    if (!_isRetryable(err) || attempt >= _maxRetries) {
      return handler.next(err);
    }
    await Future.delayed(_baseDelay * (attempt + 1));
    final opts = err.requestOptions;
    opts.extra['retryAttempt'] = attempt + 1;
    try {
      final response = await _dio.fetch(opts);
      return handler.resolve(response);
    } on DioException catch (e) {
      return handler.next(e);
    }
  }
}

/// Maps a caught network/API error to a short, user-facing message instead
/// of Dio's technical `DioException [type]: ...` text. Screens that
/// currently render `error.toString()` directly to the user should use
/// this instead.
String describeApiError(Object error) {
  if (error is DioException) {
    switch (error.type) {
      case DioExceptionType.connectionError:
        return 'No internet connection. Please check your network and try again.';
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return 'The request timed out. Please try again.';
      case DioExceptionType.badResponse:
        final status = error.response?.statusCode;
        if (status != null && status >= 500) {
          return 'Something went wrong on our end. Please try again shortly.';
        }
        if (status == 404) return 'The requested information could not be found.';
        return 'That request could not be completed. Please try again.';
      case DioExceptionType.cancel:
        return 'Request cancelled.';
      default:
        return 'Something went wrong. Please try again.';
    }
  }
  return 'Something went wrong. Please try again.';
}

class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;

  late final Dio dio;
  late final _ResponseCacheInterceptor _cacheInterceptor;

  /// Clears every cached GET response, in memory and on disk. Only public
  /// catalog endpoints (occasions, packages, themes, categories) opt into
  /// this cache, so it's not user-specific — exposed mainly for
  /// pull-to-refresh flows that want to force a genuinely fresh fetch.
  Future<void> clearCache() => _cacheInterceptor.clear();

  /// Shared by every request that hits a 401 at the same moment, so an
  /// expired token triggers one refresh call instead of one per request.
  Future<bool>? _refreshInFlight;

  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://tyohaar-v1-0-527701068133.asia-south1.run.app/api/v1/',
  );

  ApiClient._internal() {
    dio = Dio(
      BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 30),
        sendTimeout: const Duration(seconds: 15),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    _cacheInterceptor = _ResponseCacheInterceptor(dio);
    dio.interceptors.add(_cacheInterceptor);
    dio.interceptors.add(_RetryInterceptor(dio));

    if (kDebugMode) {
      dio.interceptors.add(LogInterceptor(
        requestHeader: false,
        requestBody: true,
        responseHeader: false,
        responseBody: true,
        error: true,
        logPrint: (obj) => debugPrint('API: $obj'),
      ));
    }

    // Auth interceptor: attach Bearer token and handle 401 refresh/logout
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = AuthManager.instance.accessToken;
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          return handler.next(options);
        },
        onError: (DioException e, handler) async {
          if (e.response?.statusCode == 401) {
            // A 401 with no session to begin with is not an expired session —
            // it is an anonymous caller touching an authed endpoint, which is
            // routine while browsing as a guest (the home screen asks for
            // celebrations, My Bookings is tab-reachable, and so on).
            //
            // Logging out here wiped AuthManager's guest flag and fired
            // notifyListeners(), so the whole app rebuilt out from under the
            // guest and dropped them on an error screen mid-browse. Callers
            // already handle the 401 itself; there is simply nothing to
            // clear, so pass it through untouched.
            if (AuthManager.instance.accessToken == null) {
              return handler.next(e);
            }

            // Avoid infinite loops: check if this is already a retry
            if (e.requestOptions.extra['retry'] == true) {
              await AuthManager.instance.logout();
              return handler.next(e);
            }

            // Attempt token refresh
            final refreshed = await (_refreshInFlight ??=
                _tryRefreshToken().whenComplete(() => _refreshInFlight = null));
            if (refreshed) {
              final opts = e.requestOptions;
              opts.headers['Authorization'] = 'Bearer ${AuthManager.instance.accessToken}';
              opts.extra['retry'] = true; // Mark as retry
              
              try {
                // Use the main dio instance to retry the request
                final retryResp = await dio.fetch(opts);
                return handler.resolve(retryResp);
              } catch (_) {
                // Retry failed even with new token
                await AuthManager.instance.logout();
                return handler.next(e);
              }
            } else {
              // Refresh failed: session is truly dead
              await AuthManager.instance.logout();
            }
          }
          return handler.next(e);
        },
      ),
    );
  }

  /// Calls the refresh-token endpoint and stores the new access token.
  /// Returns true on success, false on failure.
  Future<bool> _tryRefreshToken() async {
    final refreshToken = AuthManager.instance.refreshToken;
    if (refreshToken == null) return false;
    try {
      // Use a separate Dio instance to avoid triggering the auth interceptor again
      final plainDio = Dio(BaseOptions(baseUrl: baseUrl));
      final resp = await plainDio.post(
        'auth/token/refresh',
        data: {'refresh_token': refreshToken},
      );
      final newToken = resp.data?['data']?['access_token'] as String?;
      if (newToken != null) {
        await AuthManager.instance.updateAccessToken(newToken);
        return true;
      }
    } catch (_) {}
    return false;
  }
}
