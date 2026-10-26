import '../api_client.dart';

/// One balloon colour from the admin-managed palette.
class BalloonColorOption {
  final String name;
  final String hex; // "#RRGGBB"
  const BalloonColorOption(this.name, this.hex);

  factory BalloonColorOption.fromJson(Map<String, dynamic> j) =>
      BalloonColorOption(j['name'] as String, (j['hex_code'] as String).toUpperCase());
}

/// What the customer is offered if the palette can't be fetched (offline, or
/// the first request fails). Mirrors the migration's seed. The server still
/// validates every booking against the live palette, so a stale fallback can
/// at worst be refused — never silently accepted.
const List<BalloonColorOption> fallbackBalloonPalette = [
  BalloonColorOption('Red', '#E63946'),
  BalloonColorOption('Gold', '#D4AF37'),
  BalloonColorOption('Rose Gold', '#E8B4B8'),
  BalloonColorOption('Pink', '#F48FB1'),
  BalloonColorOption('Sky Blue', '#87CEEB'),
  BalloonColorOption('Navy Blue', '#1E3A5F'),
  BalloonColorOption('White', '#FFFFFF'),
  BalloonColorOption('Black', '#1C1C1C'),
  BalloonColorOption('Silver', '#C0C0C0'),
  BalloonColorOption('Purple', '#8E44AD'),
  BalloonColorOption('Green', '#2ECC71'),
  BalloonColorOption('Orange', '#F39C12'),
  BalloonColorOption('Yellow', '#F1C40F'),
];

class ColorService {
  final ApiClient _api = ApiClient();

  /// The active palette, in the order the admin arranged it.
  Future<List<BalloonColorOption>> balloonColors() async {
    final response = await _api.dio.get('balloon-colors');
    final list = (response.data['data'] ?? []) as List;
    return list.map((e) => BalloonColorOption.fromJson(e as Map<String, dynamic>)).toList();
  }

  /// Active finish names (matte / pastel / chrome …) in the admin's order.
  Future<List<String>> balloonFinishes() async {
    final response = await _api.dio.get('balloon-finishes');
    return ((response.data['data'] ?? []) as List).map((e) => (e as Map<String, dynamic>)['name'] as String).toList();
  }
}
