import '../api_client.dart';

class MembershipPlan {
  final String id;
  final String name;
  final String description;
  final double price;
  final String billingCycle;
  final List<String> features;
  final bool isActive;

  MembershipPlan({
    required this.id,
    required this.name,
    required this.description,
    required this.price,
    required this.billingCycle,
    required this.features,
    required this.isActive,
  });

  factory MembershipPlan.fromJson(Map<String, dynamic> json) {
    return MembershipPlan(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String? ?? '',
      price: (json['price'] ?? 0).toDouble(),
      billingCycle: json['billing_cycle'] as String? ?? 'monthly',
      features: (json['features'] as List?)?.cast<String>() ?? [],
      isActive: json['is_active'] as bool? ?? true,
    );
  }
}

class ActiveMembership {
  final String id;
  final String planId;
  final String planName;
  final String status;
  final DateTime? expiresAt;

  ActiveMembership({
    required this.id,
    required this.planId,
    required this.planName,
    required this.status,
    this.expiresAt,
  });

  factory ActiveMembership.fromJson(Map<String, dynamic> json) {
    return ActiveMembership(
      id: json['id'] as String,
      planId: json['plan_id'] as String? ?? '',
      planName: json['plan']?['name'] as String? ?? 'Standard',
      status: json['membership_status'] as String? ?? 'active',
      expiresAt: json['expires_at'] != null
          ? DateTime.tryParse(json['expires_at'] as String)
          : null,
    );
  }
}

class MembershipService {
  final ApiClient _api = ApiClient();

  Future<List<MembershipPlan>> listPlans() async {
    final response = await _api.dio.get('memberships/plans');
    final List list = (response.data['data'] ?? []) as List;
    return list.map((item) => MembershipPlan.fromJson(item as Map<String, dynamic>)).toList();
  }

  Future<ActiveMembership?> getActiveMembership() async {
    try {
      final response = await _api.dio.get('memberships/active');
      final data = response.data['data'];
      if (data == null) return null;
      return ActiveMembership.fromJson(data as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }

  Future<void> subscribe(String planId) async {
    await _api.dio.post('memberships/subscribe', data: {'plan_id': planId});
  }

  Future<void> cancelMembership(String membershipId) async {
    await _api.dio.post('memberships/$membershipId/cancel');
  }

  Future<void> renewMembership(String membershipId) async {
    await _api.dio.post('memberships/$membershipId/renew');
  }
}
