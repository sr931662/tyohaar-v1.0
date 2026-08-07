import 'services/common_service.dart';

String slugifyCity(String cityName) =>
    cityName.trim().toLowerCase().replaceAll(RegExp(r'\s+'), '-');

/// Admin-managed list of cities Tyohaar actively operates in (vendors
/// onboarded, bookings possible) — sourced from the same `/common/cities`
/// table the admin portal's "States & Cities" settings tab manages, filtered
/// to `is_serviceable`. Feeds every manual city picker in the app (Explore,
/// the nav sidebar) so they never drift from what the backend considers
/// live, and nothing is hardcoded client-side.
///
/// `CommonService.listCities` already HTTP-caches the request for an hour;
/// this is just an in-memory mirror so repeat picker opens within a session
/// don't even need that.
class ServiceableCities {
  static final ServiceableCities instance = ServiceableCities._internal();
  ServiceableCities._internal();

  final CommonService _service = CommonService();
  List<CityOption>? _cities;
  Future<List<CityOption>>? _inFlight;

  Future<List<CityOption>> load() {
    final cached = _cities;
    if (cached != null) return Future.value(cached);
    return _inFlight ??= _service.listCities(isServiceable: true).then((cities) {
      _cities = cities;
      _inFlight = null;
      return cities;
    }).catchError((Object e) {
      _inFlight = null;
      throw e;
    });
  }
}
