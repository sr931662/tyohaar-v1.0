import '../api_client.dart';

class ReferralCode {
  final String code;
  final String referralUrl;

  ReferralCode({required this.code, required this.referralUrl});

  factory ReferralCode.fromJson(Map<String, dynamic> json) {
    return ReferralCode(
      code: json['referral_code'] as String? ?? json['code'] as String? ?? '',
      referralUrl: json['referral_url'] as String? ?? '',
    );
  }
}

class ReferralStats {
  final int totalReferrals;
  final int successfulReferrals;
  final double totalEarned;
  final double pendingRewards;

  ReferralStats({
    required this.totalReferrals,
    required this.successfulReferrals,
    required this.totalEarned,
    required this.pendingRewards,
  });

  factory ReferralStats.fromJson(Map<String, dynamic> json) {
    // ReferralStatsResponse fields: signed_up_count, converted_count, rewarded_count, total_earned
    return ReferralStats(
      totalReferrals: json['signed_up_count'] as int? ?? 0,
      successfulReferrals: json['converted_count'] as int? ?? 0,
      totalEarned: (json['total_earned'] ?? 0).toDouble(),
      pendingRewards: 0, // not in ReferralStatsResponse
    );
  }
}

class ReferralItem {
  final String id;
  final String refereeName;
  final String status;
  final DateTime createdAt;

  ReferralItem({
    required this.id,
    required this.refereeName,
    required this.status,
    required this.createdAt,
  });

  factory ReferralItem.fromJson(Map<String, dynamic> json) {
    return ReferralItem(
      id: json['id'] as String,
      refereeName: json['referee']?['full_name'] as String? ?? 'Unknown',
      status: json['reward_status'] as String? ?? 'pending',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

class ReferralService {
  final ApiClient _api = ApiClient();

  Future<ReferralCode> getReferralCode() async {
    final response = await _api.dio.get('referrals/code');
    return ReferralCode.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  Future<void> applyReferralCode(String code) async {
    await _api.dio.post('referrals/apply', data: {'referral_code': code});
  }

  Future<ReferralStats> getReferralStats() async {
    final response = await _api.dio.get('referrals/stats');
    return ReferralStats.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  Future<List<ReferralItem>> listReferrals() async {
    final response = await _api.dio.get('referrals/');
    final List list = (response.data['data'] ?? []) as List;
    return list.map((item) => ReferralItem.fromJson(item as Map<String, dynamic>)).toList();
  }
}
