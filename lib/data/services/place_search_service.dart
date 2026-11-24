import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart' show visibleForTesting;
import 'package:geocoding/geocoding.dart';
import 'package:geolocator/geolocator.dart';

/// A place the customer can pick as the venue: an area, street, society or
/// landmark. Carries just enough structure to fill the address form.
class PlaceSuggestion {
  /// Headline, e.g. "Sector 93B" or "Assotech Business Cresterra".
  final String title;

  /// The rest of the line, e.g. "Noida, Uttar Pradesh".
  final String subtitle;
  final String? street;
  final String? area;
  final String? city;
  final String? state;
  final String? postalCode;
  final double? latitude;
  final double? longitude;

  const PlaceSuggestion({
    required this.title,
    required this.subtitle,
    this.street,
    this.area,
    this.city,
    this.state,
    this.postalCode,
    this.latitude,
    this.longitude,
  });

  /// What goes in the "Area" tile: the place plus its locality, deduplicated.
  String get areaLine {
    final parts = <String>[];
    void add(String? v) {
      final t = v?.trim();
      if (t != null && t.isNotEmpty && !parts.any((p) => p.toLowerCase() == t.toLowerCase())) parts.add(t);
    }

    add(title);
    add(area);
    return parts.join(', ');
  }
}

enum CurrentPlaceStatus { found, permissionDenied, permissionDeniedForever, serviceOff, failed }

class CurrentPlaceResult {
  final CurrentPlaceStatus status;
  final PlaceSuggestion? place;
  const CurrentPlaceResult(this.status, [this.place]);
}

/// Place search + "use my current location", kept behind one small class so
/// the provider can be swapped (e.g. for Google Places once a key exists)
/// without touching any screen.
///
/// Search uses Photon (OpenStreetMap data, no API key, built for type-ahead).
/// Reverse lookups of the device position use the platform geocoder.
class PlaceSearchService {
  PlaceSearchService._();
  static final PlaceSearchService instance = PlaceSearchService._();

  static const _photon = 'https://photon.komoot.io/api/';
  // Rough bounding box of India (minLon,minLat,maxLon,maxLat) — keeps results
  // to places Tyohaar could actually serve.
  static const _indiaBox = '68.1,6.7,97.4,35.7';

  Dio _dio = Dio(BaseOptions(
    connectTimeout: const Duration(seconds: 6),
    receiveTimeout: const Duration(seconds: 8),
    headers: const {'Accept': 'application/json'},
  ));

  /// Swaps the HTTP client and clears cached results. For tests.
  @visibleForTesting
  void debugReset({Dio? dio}) {
    if (dio != null) _dio = dio;
    _cache.clear();
    _inFlight?.cancel();
    _inFlight = null;
  }

  CancelToken? _inFlight;
  final Map<String, List<PlaceSuggestion>> _cache = {};

  /// Suggestions for [query], biased towards [city] (and [nearLat]/[nearLon]
  /// when known). Cancels any earlier in-flight search, so a slow response to
  /// "sec" can never overwrite the results for "sector 93".
  Future<List<PlaceSuggestion>> search(
    String query, {
    String? city,
    double? nearLat,
    double? nearLon,
  }) async {
    final q = query.trim();
    if (q.length < 2) return const [];

    final cityPart = (city ?? '').trim();
    final full = cityPart.isEmpty || q.toLowerCase().contains(cityPart.toLowerCase()) ? q : '$q, $cityPart';
    final key = '${full.toLowerCase()}|${nearLat?.toStringAsFixed(2)}|${nearLon?.toStringAsFixed(2)}';
    final cached = _cache[key];
    if (cached != null) return cached;

    _inFlight?.cancel();
    final token = _inFlight = CancelToken();
    final res = await _dio.get<Map<String, dynamic>>(
      _photon,
      queryParameters: {
        'q': full,
        'limit': 10,
        'lang': 'en',
        'bbox': _indiaBox,
        if (nearLat != null && nearLon != null) ...{'lat': nearLat, 'lon': nearLon},
      },
      cancelToken: token,
    );

    final features = (res.data?['features'] as List?) ?? const [];
    final seen = <String>{};
    final out = <PlaceSuggestion>[];
    for (final f in features) {
      final s = _fromFeature(f as Map<String, dynamic>);
      if (s == null) continue;
      // Photon can return the same place several times (node + relation).
      if (!seen.add('${s.title}|${s.subtitle}'.toLowerCase())) continue;
      out.add(s);
    }
    if (_cache.length > 60) _cache.clear();
    return _cache[key] = out;
  }

  PlaceSuggestion? _fromFeature(Map<String, dynamic> f) {
    final p = (f['properties'] as Map?)?.cast<String, dynamic>();
    if (p == null) return null;
    if ((p['countrycode'] as String?)?.toUpperCase() != 'IN') return null;

    String? s(String k) {
      final v = (p[k] as String?)?.trim();
      return (v == null || v.isEmpty) ? null : v;
    }

    final name = s('name');
    final street = s('street');
    final house = s('housenumber');
    final locality = s('locality') ?? s('district');
    final city = s('city') ?? s('county') ?? s('district');
    final state = s('state');

    final title = name ?? (street != null ? [if (house != null) house, street].join(' ') : locality);
    if (title == null) return null;

    final coords = ((f['geometry'] as Map?)?['coordinates'] as List?);
    final lon = coords != null && coords.length >= 2 ? (coords[0] as num).toDouble() : null;
    final lat = coords != null && coords.length >= 2 ? (coords[1] as num).toDouble() : null;

    final subtitleParts = <String>[];
    for (final v in [if (name != null) street, locality != title ? locality : null, city, state]) {
      final t = v?.trim();
      if (t != null && t.isNotEmpty && t != title && !subtitleParts.contains(t)) subtitleParts.add(t);
    }

    return PlaceSuggestion(
      title: title,
      subtitle: subtitleParts.join(', '),
      street: street,
      area: locality != title ? locality : null,
      city: city,
      state: state,
      postalCode: s('postcode'),
      latitude: lat,
      longitude: lon,
    );
  }

  /// Resolves where the device is right now into a [PlaceSuggestion]. Asks for
  /// permission only if it has not been decided yet.
  Future<CurrentPlaceResult> currentPlace() async {
    if (!await Geolocator.isLocationServiceEnabled()) {
      return const CurrentPlaceResult(CurrentPlaceStatus.serviceOff);
    }
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.deniedForever) {
      return const CurrentPlaceResult(CurrentPlaceStatus.permissionDeniedForever);
    }
    if (permission == LocationPermission.denied) {
      return const CurrentPlaceResult(CurrentPlaceStatus.permissionDenied);
    }
    try {
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 12),
        ),
      );
      final place = await reverse(position.latitude, position.longitude);
      return place == null
          ? const CurrentPlaceResult(CurrentPlaceStatus.failed)
          : CurrentPlaceResult(CurrentPlaceStatus.found, place);
    } catch (_) {
      return const CurrentPlaceResult(CurrentPlaceStatus.failed);
    }
  }

  /// Like [currentPlace] but never prompts and never waits for a fresh fix:
  /// used to preview the current address before the customer has said yes.
  Future<PlaceSuggestion?> peekCurrentPlace() async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) return null;
      final permission = await Geolocator.checkPermission();
      if (permission != LocationPermission.whileInUse && permission != LocationPermission.always) return null;
      final last = await Geolocator.getLastKnownPosition();
      if (last == null) return null;
      return await reverse(last.latitude, last.longitude);
    } catch (_) {
      return null;
    }
  }

  Future<PlaceSuggestion?> reverse(double lat, double lon) async {
    final marks = await placemarkFromCoordinates(lat, lon);
    if (marks.isEmpty) return null;
    final m = marks.first;

    String? clean(String? v) {
      final t = v?.trim();
      return (t == null || t.isEmpty) ? null : t;
    }

    final area = clean(m.subLocality);
    final city = clean(m.locality) ?? clean(m.subAdministrativeArea);
    final street = clean(m.thoroughfare) ?? clean(m.street);
    final name = clean(m.name);
    // "name" is frequently just the house number or a plus code — only use it
    // as the headline when it looks like a real place name.
    final looksLikeName = name != null && !RegExp(r'^[\d\s/-]+$').hasMatch(name) && !name.contains('+');
    final title = (looksLikeName ? name : null) ?? area ?? street ?? city;
    if (title == null) return null;

    final sub = <String>[];
    for (final v in [if (looksLikeName) area, city, clean(m.administrativeArea)]) {
      if (v != null && v != title && !sub.contains(v)) sub.add(v);
    }
    return PlaceSuggestion(
      title: title,
      subtitle: sub.join(', '),
      street: street,
      area: area != title ? area : null,
      city: city,
      state: clean(m.administrativeArea),
      postalCode: clean(m.postalCode),
      latitude: lat,
      longitude: lon,
    );
  }
}
