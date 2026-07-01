import '../api_client.dart';

class VendorProfile {
  final String id;
  final String businessName;
  final String? businessCategory;
  final double? rating;
  final int? totalReviews;
  final String status;
  final Map<String, dynamic>? workingHours;

  VendorProfile({
    required this.id,
    required this.businessName,
    this.businessCategory,
    this.rating,
    this.totalReviews,
    required this.status,
    this.workingHours,
  });

  factory VendorProfile.fromJson(Map<String, dynamic> json) {
    return VendorProfile(
      id: json['id'] as String,
      businessName: json['business_name'] as String? ?? 'My Business',
      businessCategory: json['category'] as String?,
      rating: (json['average_rating'] as num?)?.toDouble(),
      totalReviews: json['total_reviews'] as int?,
      status: json['status'] as String? ?? 'active',
      workingHours: json['working_hours'] as Map<String, dynamic>?,
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

class VendorPublicDetail {
  final String id;
  final String businessName;
  final String? businessCategory;
  final String? bio;
  final double? rating;
  final int? totalReviews;
  final String? location;
  final bool? isVerified;
  final int? yearsInBusiness;
  final String tint;
  final String? heroImageUrl;
  final List<String> galleryUrls;

  VendorPublicDetail({
    required this.id,
    required this.businessName,
    this.businessCategory,
    this.bio,
    this.rating,
    this.totalReviews,
    this.location,
    this.isVerified,
    this.yearsInBusiness,
    this.tint = 'saffron',
    this.heroImageUrl,
    this.galleryUrls = const [],
  });

  factory VendorPublicDetail.fromJson(Map<String, dynamic> json) {
    final profile = json['vendor_profile'] as Map<String, dynamic>? ?? json;
    final gallery = (json['gallery'] as List?)?.map((g) => g['image_url'] as String? ?? '').where((u) => u.isNotEmpty).toList() ?? <String>[];
    return VendorPublicDetail(
      id: json['id'] as String,
      businessName: profile['business_name'] as String? ?? 'Vendor',
      businessCategory: profile['category'] as String?,
      bio: profile['bio'] as String?,
      rating: (json['average_rating'] as num?)?.toDouble(),
      totalReviews: json['total_reviews'] as int?,
      location: profile['city'] as String? ?? profile['location'] as String?,
      isVerified: json['is_verified'] as bool? ?? false,
      yearsInBusiness: profile['years_in_business'] as int?,
      tint: 'saffron',
      heroImageUrl: (gallery.isNotEmpty) ? gallery.first : null,
      galleryUrls: gallery,
    );
  }
}

class VendorReview {
  final String id;
  final String reviewerName;
  final double rating;
  final String? comment;
  final DateTime createdAt;

  VendorReview({
    required this.id,
    required this.reviewerName,
    required this.rating,
    this.comment,
    required this.createdAt,
  });

  factory VendorReview.fromJson(Map<String, dynamic> json) {
    return VendorReview(
      id: json['id'] as String,
      reviewerName: json['user']?['full_name'] as String? ?? 'Customer',
      rating: (json['rating'] as num?)?.toDouble() ?? 5.0,
      comment: json['comment'] as String?,
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
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

  Future<VendorPublicDetail> getVendorById(String vendorId) async {
    final response = await _api.dio.get('vendors/$vendorId');
    return VendorPublicDetail.fromJson(response.data['data'] as Map<String, dynamic>);
  }

  Future<List<Map<String, dynamic>>> getVendorPackages(String vendorId) async {
    final response = await _api.dio.get('vendors/$vendorId/packages');
    final List list = response.data['data'] ?? [];
    return List<Map<String, dynamic>>.from(list);
  }

  Future<List<VendorReview>> getVendorReviews(String vendorId, {int limit = 5}) async {
    final response = await _api.dio.get('vendors/$vendorId/reviews', queryParameters: {'limit': limit});
    final List list = response.data['data'] ?? [];
    return list.map((r) => VendorReview.fromJson(r as Map<String, dynamic>)).toList();
  }

  Future<void> updateVendorProfile(String vendorId, Map<String, dynamic> data) async {
    await _api.dio.put('users/$vendorId/profile', data: data);
  }
}
