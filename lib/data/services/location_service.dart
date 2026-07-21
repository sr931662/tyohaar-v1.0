import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:geocoding/geocoding.dart';
import 'package:geolocator/geolocator.dart';

/// Outcome of a city-resolution attempt, distinguishing "permission
/// permanently denied" (which needs an Open Settings affordance) from a
/// plain "couldn't resolve right now" (which is just worth retrying).
enum LocationResultStatus { success, deniedForever, unavailable }

class LocationResult {
  final LocationResultStatus status;
  final String? city;

  const LocationResult(this.status, [this.city]);
}

class LocationService {
  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );
  static const _lastCityKey = 'ty_last_known_city';

  /// Best-effort last resolved city, cached locally so the header doesn't
  /// flash a placeholder on every cold start while GPS re-resolves.
  Future<String?> getCachedCity() async {
    try {
      return await _storage.read(key: _lastCityKey);
    } catch (_) {
      return null;
    }
  }

  Future<void> _cacheCity(String city) async {
    try {
      await _storage.write(key: _lastCityKey, value: city);
    } catch (_) {
      // Non-fatal — worst case the header re-resolves from GPS next time.
    }
  }

  Future<LocationResult> resolveCurrentCity() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) return const LocationResult(LocationResultStatus.unavailable);

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    if (permission == LocationPermission.deniedForever) {
      return const LocationResult(LocationResultStatus.deniedForever);
    }
    if (permission == LocationPermission.denied) {
      return const LocationResult(LocationResultStatus.unavailable);
    }

    try {
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.medium),
      );

      final placemarks = await placemarkFromCoordinates(
        position.latitude,
        position.longitude,
      );
      if (placemarks.isEmpty) return const LocationResult(LocationResultStatus.unavailable);

      final place = placemarks.first;
      final city = _firstNonEmpty([
        place.locality,
        place.subAdministrativeArea,
        place.administrativeArea,
      ]);
      if (city == null) return const LocationResult(LocationResultStatus.unavailable);

      await _cacheCity(city);
      return LocationResult(LocationResultStatus.success, city);
    } catch (_) {
      return const LocationResult(LocationResultStatus.unavailable);
    }
  }

  /// Backwards-compatible convenience wrapper — resolves just the city
  /// string, or null on any non-success outcome.
  Future<String?> getCurrentCity() async {
    final result = await resolveCurrentCity();
    return result.status == LocationResultStatus.success ? result.city : null;
  }

  String? _firstNonEmpty(List<String?> values) {
    for (final value in values) {
      final trimmed = value?.trim();
      if (trimmed != null && trimmed.isNotEmpty) return trimmed;
    }
    return null;
  }
}
