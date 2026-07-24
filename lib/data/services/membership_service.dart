import 'package:dio/dio.dart';

import '../api_client.dart';
import '../models.dart' show asDouble;

/// listPlans() is a largely-static pricing/tier catalog — opt it into
/// ApiClient's in-memory cache like package_service.dart/common_service.dart
/// already do. getActiveMembership() reflects live subscription state and
/// deliberately stays uncached.
Options _cacheable({Duration ttl = const Duration(minutes: 10)}) =>
    Options(extra: {'cache': true, 'cacheTtl': ttl});

class MembershipPlan {
  final String id;
  final String tier;
  final String name;
  final String slug;
  final String? tagline;
  final String description;
  final double monthlyPrice;
  final double yearlyPrice;
  final int? validityDays;
  final double cashbackPercentage;
  final double discountPercentage;
  final double rewardMultiplier;
  final double walletBonus;
  final int freeInvitationsCount;
  final bool priorityBooking;
  final bool hasExclusivePackages;
  final bool cancellationProtection;
  final int customerSupportPriority;
  final String? canUpgradeToTier;
  final String? canDowngradeToTier;
  final bool isActive;
  final int displayOrder;
  final double annualSavings;

  MembershipPlan({
    required this.id,
    required this.tier,
    required this.name,
    required this.slug,
    this.tagline,
    required this.description,
    required this.monthlyPrice,
    required this.yearlyPrice,
    this.validityDays,
    required this.cashbackPercentage,
    required this.discountPercentage,
    required this.rewardMultiplier,
    required this.walletBonus,
    required this.freeInvitationsCount,
    required this.priorityBooking,
    required this.hasExclusivePackages,
    required this.cancellationProtection,
    required this.customerSupportPriority,
    this.canUpgradeToTier,
    this.canDowngradeToTier,
    required this.isActive,
    required this.displayOrder,
    required this.annualSavings,
  });

  factory MembershipPlan.fromJson(Map<String, dynamic> json) {
    return MembershipPlan(
      id: json['id'] as String,
      tier: json['tier'] as String? ?? 'free',
      name: json['name'] as String,
      slug: json['slug'] as String? ?? '',
      tagline: json['tagline'] as String?,
      description: json['description'] as String? ?? '',
      monthlyPrice: asDouble(json['monthly_price']),
      yearlyPrice: asDouble(json['yearly_price']),
      validityDays: json['validity_days'] as int?,
      cashbackPercentage: asDouble(json['cashback_percentage']),
      discountPercentage: asDouble(json['discount_percentage']),
      rewardMultiplier: json['reward_multiplier'] == null ? 1.0 : asDouble(json['reward_multiplier']),
      walletBonus: asDouble(json['wallet_bonus']),
      freeInvitationsCount: (json['free_invitations_count'] ?? 0) as int,
      priorityBooking: json['priority_booking'] as bool? ?? false,
      hasExclusivePackages: json['has_exclusive_packages'] as bool? ?? false,
      cancellationProtection: json['cancellation_protection'] as bool? ?? false,
      customerSupportPriority: (json['customer_support_priority'] ?? 1) as int,
      canUpgradeToTier: json['can_upgrade_to_tier'] as String?,
      canDowngradeToTier: json['can_downgrade_to_tier'] as String?,
      isActive: json['is_active'] as bool? ?? true,
      displayOrder: (json['display_order'] ?? 0) as int,
      annualSavings: asDouble(json['annual_savings']),
    );
  }
}

class ActiveMembership {
  final String id;
  final String planId;
  final String? tier;
  final String billingCycle;
  final String status;
  final bool isLifetime;
  final DateTime? activatedAt;
  final DateTime? expiresAt;
  final DateTime? gracePeriodUntil;
  final bool autoRenew;
  final int renewalCount;
  final String? upgradedFromPlanId;
  final String? cancellationReason;
  final DateTime? cancelledAt;

  ActiveMembership({
    required this.id,
    required this.planId,
    this.tier,
    required this.billingCycle,
    required this.status,
    required this.isLifetime,
    this.activatedAt,
    this.expiresAt,
    this.gracePeriodUntil,
    required this.autoRenew,
    required this.renewalCount,
    this.upgradedFromPlanId,
    this.cancellationReason,
    this.cancelledAt,
  });

  bool get isActive => status == 'active' || status == 'grace_period';
  bool get isInGracePeriod => status == 'grace_period';

  factory ActiveMembership.fromJson(Map<String, dynamic> json) {
    DateTime? parse(String? key) =>
        json[key] != null ? DateTime.tryParse(json[key] as String) : null;
    return ActiveMembership(
      id: json['id'] as String,
      planId: json['plan_id'] as String? ?? '',
      tier: json['tier'] as String?,
      billingCycle: json['billing_cycle'] as String? ?? 'monthly',
      status: json['membership_status'] as String? ?? 'active',
      isLifetime: json['is_lifetime'] as bool? ?? false,
      activatedAt: parse('activated_at'),
      expiresAt: parse('expires_at'),
      gracePeriodUntil: parse('grace_period_until'),
      autoRenew: json['auto_renew'] as bool? ?? true,
      renewalCount: (json['renewal_count'] ?? 0) as int,
      upgradedFromPlanId: json['upgraded_from_plan_id'] as String?,
      cancellationReason: json['cancellation_reason'] as String?,
      cancelledAt: parse('cancelled_at'),
    );
  }
}

class MembershipService {
  final ApiClient _api = ApiClient();

  Future<List<MembershipPlan>> listPlans() async {
    final response = await _api.dio.get('memberships/plans', options: _cacheable());
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

  Future<void> subscribe({
    required String planId,
    required String billingCycle,
    String? paymentId,
  }) async {
    await _api.dio.post('memberships/subscribe', data: {
      'plan_id': planId,
      'billing_cycle': billingCycle,
      if (paymentId != null) 'payment_id': paymentId,
    });
  }

  Future<void> cancelMembership(String membershipId, {String? reason}) async {
    await _api.dio.post('memberships/$membershipId/cancel', data: {
      if (reason != null) 'reason': reason,
    });
  }

  Future<void> renewMembership(String membershipId, {String? paymentId}) async {
    await _api.dio.post('memberships/$membershipId/renew', data: {
      if (paymentId != null) 'payment_id': paymentId,
    });
  }

  Future<void> upgrade(String membershipId, String newPlanId, {String? paymentId, String? reason}) async {
    await _api.dio.post('memberships/$membershipId/upgrade', data: {
      'new_plan_id': newPlanId,
      if (paymentId != null) 'payment_id': paymentId,
      if (reason != null) 'reason': reason,
    });
  }

  Future<void> downgrade(String membershipId, String newPlanId, {String? reason}) async {
    await _api.dio.post('memberships/$membershipId/downgrade', data: {
      'new_plan_id': newPlanId,
      if (reason != null) 'reason': reason,
    });
  }
}
