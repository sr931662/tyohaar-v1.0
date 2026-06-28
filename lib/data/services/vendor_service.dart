import '../api_client.dart';

class VendorProfile {
  final String id;
  final String businessName;
  final String? businessCategory;
  final double? rating;
  final int? totalReviews;
  final String status;

  VendorProfile({
    required this.id,
    required this.businessName,
    this.businessCategory,
    this.rating,
    this.totalReviews,
    required this.status,
  });

  factory VendorProfile.fromJson(Map<String, dynamic> json) {
    return VendorProfile(
      id: json['id'] as String,
      businessName: json['business_name'] as String? ?? 'My Business',
      businessCategory: json['category'] as String?,
      rating: (json['average_rating'] as num?)?.toDouble(),
      totalReviews: json['total_reviews'] as int?,
      status: json['status'] as String? ?? 'active',
    );
  }
}

class VendorStats {
  final int activeBookings;
  final int completedBookings;
  final double monthlyEarnings;
  final double earningsChangePercent;
  final int pendingRequests;

  VendorStats({
    required this.activeBookings,
    required this.completedBookings,
    required this.monthlyEarnings,
    required this.earningsChangePercent,
    required this.pendingRequests,
  });

  factory VendorStats.fromJson(Map<String, dynamic> json) {
    return VendorStats(
      activeBookings: json['active_bookings'] as int? ?? 0,
      completedBookings: json['completed_bookings'] as int? ?? 0,
      monthlyEarnings: (json['monthly_earnings'] as num?)?.toDouble() ?? 0.0,
      earningsChangePercent: (json['earnings_change_percent'] as num?)?.toDouble() ?? 0.0,
      pendingRequests: json['pending_requests'] as int? ?? 0,
    );
  }
}

class VendorBooking {
  final String id;
  final String bookingNumber;
  final String status;
  final String occasionName;
  final DateTime scheduledDate;
  final String? clientName;
  final String? location;
  final double totalAmount;
  final DateTime? quoteExpiresAt;

  VendorBooking({
    required this.id,
    required this.bookingNumber,
    required this.status,
    required this.occasionName,
    required this.scheduledDate,
    this.clientName,
    this.location,
    required this.totalAmount,
    this.quoteExpiresAt,
  });

  factory VendorBooking.fromJson(Map<String, dynamic> json) {
    return VendorBooking(
      id: json['id'] as String,
      bookingNumber: json['booking_number'] as String? ?? '',
      status: json['booking_status'] as String? ?? 'pending',
      occasionName: json['celebration']?['occasion']?['name'] as String? ??
          json['occasion']?['name'] as String? ??
          'Celebration',
      scheduledDate: DateTime.parse(json['scheduled_date'] as String),
      clientName: json['customer']?['full_name'] as String?,
      location: json['venue_address'] as String?,
      totalAmount: (json['total_amount'] as num?)?.toDouble() ?? 0.0,
      quoteExpiresAt: json['quote_expires_at'] != null
          ? DateTime.tryParse(json['quote_expires_at'] as String)
          : null,
    );
  }
}

class VendorService {
  final ApiClient _api = ApiClient();

  Future<VendorProfile> getMyVendorProfile() async {
    final response = await _api.dio.get('vendors/me');
    return VendorProfile.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  Future<VendorStats> getMyStats() async {
    final response = await _api.dio.get('vendors/me/stats');
    return VendorStats.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  Future<List<VendorBooking>> listMyBookings({int limit = 10, String? status}) async {
    final response = await _api.dio.get(
      'vendors/me/bookings',
      queryParameters: {
        'limit': limit,
        if (status != null) 'status': status,
      },
    );
    final data = response.data['data'];
    final List list = (data is Map ? data['items'] : data) as List? ?? [];
    return list
        .map((b) => VendorBooking.fromJson(b as Map<String, dynamic>))
        .toList();
  }
}
