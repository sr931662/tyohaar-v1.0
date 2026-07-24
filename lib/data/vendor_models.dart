/// Vendor-domain models — mirrors server/app/schemas/vendors/*, packages/*,
/// bookings/* response shapes exactly as consumed by the web vendor portal
/// (client/src/vendor/api/index.js is the source-of-truth contract).
library;

import 'models.dart' show asDouble, asUrl;

class VendorBusinessProfile {
  final String id;
  final String userId;
  final String businessName;
  final String vendorType;
  final String? legalName;
  final String? registrationNumber;
  final String? gstNumber;
  final String? panNumber;
  final int? yearsOfExperience;
  final int? establishedYear;
  final double? serviceRadiusKm;
  final String status;
  final String verificationStatus;
  final double averageRating;
  final int reviewCount;
  final int completionCount;
  final int cancellationCount;
  final double acceptanceRatePct;
  final VendorExtendedProfile? profile;
  final DateTime createdAt;

  VendorBusinessProfile({
    required this.id,
    required this.userId,
    required this.businessName,
    required this.vendorType,
    this.legalName,
    this.registrationNumber,
    this.gstNumber,
    this.panNumber,
    this.yearsOfExperience,
    this.establishedYear,
    this.serviceRadiusKm,
    required this.status,
    required this.verificationStatus,
    this.averageRating = 0,
    this.reviewCount = 0,
    this.completionCount = 0,
    this.cancellationCount = 0,
    this.acceptanceRatePct = 0,
    this.profile,
    required this.createdAt,
  });

  factory VendorBusinessProfile.fromJson(Map<String, dynamic> json) {
    return VendorBusinessProfile(
      id: json['id'] as String,
      userId: json['user_id'] as String? ?? '',
      businessName: json['business_name'] as String? ?? '',
      vendorType: json['vendor_type'] as String? ?? 'other',
      legalName: json['legal_name'] as String?,
      registrationNumber: json['registration_number'] as String?,
      gstNumber: json['gst_number'] as String?,
      panNumber: json['pan_number'] as String?,
      yearsOfExperience: json['years_of_experience'] as int?,
      establishedYear: json['established_year'] as int?,
      serviceRadiusKm: json['service_radius_km'] != null ? asDouble(json['service_radius_km']) : null,
      status: json['status'] as String? ?? 'pending',
      verificationStatus: json['verification_status'] as String? ?? 'pending',
      averageRating: asDouble(json['average_rating']),
      reviewCount: json['review_count'] as int? ?? 0,
      completionCount: json['completion_count'] as int? ?? 0,
      cancellationCount: json['cancellation_count'] as int? ?? 0,
      acceptanceRatePct: asDouble(json['acceptance_rate_pct']),
      profile: json['profile'] != null
          ? VendorExtendedProfile.fromJson(json['profile'] as Map<String, dynamic>)
          : null,
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

class VendorExtendedProfile {
  final String? tagline;
  final String? about;
  final List<String> specialties;
  final List<String> operatingCities;
  final List<String> operatingPincodes;
  final String? websiteUrl;
  final Map<String, String> socialLinks;
  final String? logoUrl;

  VendorExtendedProfile({
    this.tagline,
    this.about,
    this.specialties = const [],
    this.operatingCities = const [],
    this.operatingPincodes = const [],
    this.websiteUrl,
    this.socialLinks = const {},
    this.logoUrl,
  });

  factory VendorExtendedProfile.fromJson(Map<String, dynamic> json) {
    return VendorExtendedProfile(
      tagline: json['tagline'] as String?,
      about: json['about'] as String?,
      specialties: (json['specialties'] as List? ?? []).map((e) => e.toString()).toList(),
      operatingCities: (json['operating_cities'] as List? ?? []).map((e) => e.toString()).toList(),
      operatingPincodes: (json['operating_pincodes'] as List? ?? []).map((e) => e.toString()).toList(),
      websiteUrl: asUrl(json['website_url']),
      socialLinks: (json['social_links'] as Map? ?? {}).map((k, v) => MapEntry(k.toString(), v.toString())),
      logoUrl: asUrl(json['logo_url']),
    );
  }
}

class VendorGalleryItem {
  final String id;
  final String mediaUrl;
  final String? caption;
  final bool isFeatured;

  VendorGalleryItem({required this.id, required this.mediaUrl, this.caption, this.isFeatured = false});

  factory VendorGalleryItem.fromJson(Map<String, dynamic> json) {
    return VendorGalleryItem(
      id: json['id'] as String,
      mediaUrl: json['media_url'] as String? ?? json['file_url'] as String? ?? '',
      caption: json['caption'] as String?,
      isFeatured: json['is_featured'] as bool? ?? false,
    );
  }
}

class VendorDocument {
  final String id;
  final String documentType;
  final String documentUrl;
  final String verificationStatus;
  final bool isActive;

  VendorDocument({
    required this.id,
    required this.documentType,
    required this.documentUrl,
    required this.verificationStatus,
    this.isActive = true,
  });

  factory VendorDocument.fromJson(Map<String, dynamic> json) {
    return VendorDocument(
      id: json['id'] as String,
      documentType: json['document_type'] as String? ?? 'other',
      documentUrl: json['document_url'] as String? ?? '',
      verificationStatus: json['verification_status'] as String? ?? 'unverified',
      isActive: json['is_active'] as bool? ?? true,
    );
  }
}

class VendorBankAccount {
  final String id;
  final String accountHolderName;
  final String maskedAccountNumber;
  final String ifscCode;
  final String bankName;
  final String? branchName;
  final bool isPrimary;
  final bool isVerified;

  VendorBankAccount({
    required this.id,
    required this.accountHolderName,
    required this.maskedAccountNumber,
    required this.ifscCode,
    required this.bankName,
    this.branchName,
    this.isPrimary = false,
    this.isVerified = false,
  });

  factory VendorBankAccount.fromJson(Map<String, dynamic> json) {
    return VendorBankAccount(
      id: json['id'] as String,
      accountHolderName: json['account_holder_name'] as String? ?? '',
      maskedAccountNumber: json['masked_account_number'] as String? ?? json['account_number'] as String? ?? '',
      ifscCode: json['ifsc_code'] as String? ?? '',
      bankName: json['bank_name'] as String? ?? '',
      branchName: json['branch_name'] as String?,
      isPrimary: json['is_primary'] as bool? ?? false,
      isVerified: json['is_verified'] as bool? ?? false,
    );
  }
}

class VendorAvailabilityDay {
  final String? id;
  final int dayOfWeek; // 0=Mon..6=Sun (matches backend convention used here)
  final bool isWorking;
  final String? openTime;
  final String? closeTime;
  final String? breakStart;
  final String? breakEnd;
  final int? maxBookingsPerDay;

  VendorAvailabilityDay({
    this.id,
    required this.dayOfWeek,
    this.isWorking = true,
    this.openTime,
    this.closeTime,
    this.breakStart,
    this.breakEnd,
    this.maxBookingsPerDay,
  });

  factory VendorAvailabilityDay.fromJson(Map<String, dynamic> json) {
    return VendorAvailabilityDay(
      id: json['id'] as String?,
      dayOfWeek: json['day_of_week'] as int? ?? 0,
      isWorking: json['is_working'] as bool? ?? true,
      openTime: json['open_time'] as String?,
      closeTime: json['close_time'] as String?,
      breakStart: json['break_start'] as String?,
      breakEnd: json['break_end'] as String?,
      maxBookingsPerDay: json['max_bookings_per_day'] as int?,
    );
  }

  Map<String, dynamic> toJson() => {
        'day_of_week': dayOfWeek,
        'is_working': isWorking,
        if (openTime != null) 'open_time': openTime,
        if (closeTime != null) 'close_time': closeTime,
        if (breakStart != null) 'break_start': breakStart,
        if (breakEnd != null) 'break_end': breakEnd,
        if (maxBookingsPerDay != null) 'max_bookings_per_day': maxBookingsPerDay,
      };
}

/// Public-facing vendor listing shown on the customer app's vendor detail
/// page (lib/screens/vendor_detail_screen.dart) — distinct from the vendor
/// portal's own VendorBusinessProfile above.
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
    final profile = json['vendor_profile'] as Map<String, dynamic>? ?? json['profile'] as Map<String, dynamic>? ?? json;
    final gallery = (json['gallery'] as List?)?.map((g) => g['image_url'] as String? ?? g['media_url'] as String? ?? '').where((u) => u.isNotEmpty).toList() ?? <String>[];
    return VendorPublicDetail(
      id: json['id'] as String,
      businessName: json['business_name'] as String? ?? 'Vendor',
      businessCategory: json['vendor_type'] as String?,
      bio: profile['about'] as String?,
      rating: json['average_rating'] != null ? asDouble(json['average_rating']) : null,
      totalReviews: json['review_count'] as int?,
      location: (profile['operating_cities'] as List?)?.cast<String>().firstOrNull,
      isVerified: json['verification_status'] == 'verified',
      yearsInBusiness: json['years_of_experience'] as int?,
      tint: 'saffron',
      heroImageUrl: (gallery.isNotEmpty) ? gallery.first : null,
      galleryUrls: gallery,
    );
  }
}

/// Review shape for the public vendor detail page (simpler than the vendor
/// portal's own VendorReview below — no title/booking id needed there).
class PublicVendorReview {
  final String id;
  final String reviewerName;
  final double rating;
  final String? comment;
  final DateTime createdAt;

  PublicVendorReview({
    required this.id,
    required this.reviewerName,
    required this.rating,
    this.comment,
    required this.createdAt,
  });

  factory PublicVendorReview.fromJson(Map<String, dynamic> json) {
    return PublicVendorReview(
      id: json['id'] as String,
      reviewerName: json['reviewer_name'] as String? ?? 'Customer',
      rating: asDouble(json['rating']),
      comment: json['body'] as String? ?? json['comment'] as String?,
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

class VendorReview {
  final String id;
  final String? reviewerName;
  final int rating;
  final String? title;
  final String? body;
  final String? bookingId;
  final DateTime createdAt;

  VendorReview({
    required this.id,
    this.reviewerName,
    required this.rating,
    this.title,
    this.body,
    this.bookingId,
    required this.createdAt,
  });

  factory VendorReview.fromJson(Map<String, dynamic> json) {
    return VendorReview(
      id: json['id'] as String,
      reviewerName: json['reviewer_name'] as String?,
      rating: json['rating'] as int? ?? 5,
      title: json['title'] as String?,
      body: json['body'] as String?,
      bookingId: json['booking_id'] as String?,
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

// ---------------------------------------------------------------------------
// Packages (vendor-owned)
// ---------------------------------------------------------------------------

class VendorPackage {
  final String id;
  final String name;
  final String? shortDescription;
  final String? description;
  final double basePrice;
  final List<String> occasionIds;
  final int? minGuests;
  final int? maxGuests;
  final double? durationHours;
  final String? coverImageUrl;
  final String? citySlug;
  final bool isCustomizable;
  final List<String> themeIds;
  final String status; // draft/pending_review/active/inactive/archived

  VendorPackage({
    required this.id,
    required this.name,
    this.shortDescription,
    this.description,
    required this.basePrice,
    this.occasionIds = const [],
    this.minGuests,
    this.maxGuests,
    this.durationHours,
    this.coverImageUrl,
    this.citySlug,
    this.isCustomizable = false,
    this.themeIds = const [],
    required this.status,
  });

  factory VendorPackage.fromJson(Map<String, dynamic> json) {
    return VendorPackage(
      id: json['id'] as String,
      name: json['name'] as String? ?? '',
      shortDescription: json['short_description'] as String?,
      description: json['description'] as String?,
      basePrice: asDouble(json['base_price']),
      occasionIds: (json['occasion_ids'] as List? ?? []).map((e) => e.toString()).toList(),
      minGuests: json['min_guests'] as int?,
      maxGuests: json['max_guests'] as int?,
      durationHours: json['duration_hours'] != null ? asDouble(json['duration_hours']) : null,
      coverImageUrl: asUrl(json['cover_image_url']),
      citySlug: json['city_slug'] as String?,
      isCustomizable: json['is_customizable'] as bool? ?? false,
      themeIds: (json['theme_ids'] as List? ?? []).map((e) => e.toString()).toList(),
      status: json['status'] as String? ?? 'draft',
    );
  }
}

class VendorPackageItem {
  final String id;
  final String name;
  final String? description;
  final double basePrice;
  final int quantity;
  final String? unit;
  final bool isMandatory;
  final bool isOptional;
  final bool isCommon;
  final int? maxQuantity;
  final String? coverImageUrl;
  final List<String> imageUrls;

  VendorPackageItem({
    required this.id,
    required this.name,
    this.description,
    required this.basePrice,
    this.quantity = 1,
    this.unit,
    this.isMandatory = true,
    this.isOptional = false,
    this.isCommon = false,
    this.maxQuantity,
    this.coverImageUrl,
    this.imageUrls = const [],
  });

  factory VendorPackageItem.fromJson(Map<String, dynamic> json) {
    return VendorPackageItem(
      id: json['id'] as String,
      name: json['name'] as String? ?? '',
      description: json['description'] as String?,
      basePrice: asDouble(json['base_price']),
      quantity: json['quantity'] as int? ?? 1,
      unit: json['unit'] as String?,
      isMandatory: json['is_mandatory'] as bool? ?? true,
      isOptional: json['is_optional'] as bool? ?? false,
      isCommon: json['is_common'] as bool? ?? false,
      maxQuantity: json['max_quantity'] as int?,
      coverImageUrl: asUrl(json['cover_image_url']),
      imageUrls: ((json['images'] as List?) ?? [])
          .map((i) => asUrl(i is Map ? i['image_url'] : i))
          .whereType<String>()
          .toList(),
    );
  }
}

class VendorCommonItem {
  final String id;
  final String name;
  final String? description;
  final double basePrice;
  final int quantity;
  final String? unit;
  final int? maxQuantity;

  VendorCommonItem({
    required this.id,
    required this.name,
    this.description,
    required this.basePrice,
    this.quantity = 1,
    this.unit,
    this.maxQuantity,
  });

  factory VendorCommonItem.fromJson(Map<String, dynamic> json) {
    return VendorCommonItem(
      id: json['id'] as String,
      name: json['name'] as String? ?? '',
      description: json['description'] as String?,
      basePrice: asDouble(json['base_price']),
      quantity: json['quantity'] as int? ?? 1,
      unit: json['unit'] as String?,
      maxQuantity: json['max_quantity'] as int?,
    );
  }
}

// ---------------------------------------------------------------------------
// Earnings
// ---------------------------------------------------------------------------

class VendorEarnings {
  final double totalCollected;
  final double pending;
  final int bookingsPaid;
  final List<VendorPaymentRecord> history;

  VendorEarnings({
    required this.totalCollected,
    required this.pending,
    required this.bookingsPaid,
    this.history = const [],
  });

  factory VendorEarnings.fromJson(Map<String, dynamic> json) {
    return VendorEarnings(
      totalCollected: asDouble(json['total_collected']),
      pending: asDouble(json['pending']),
      bookingsPaid: json['bookings_paid'] as int? ?? 0,
      history: ((json['history'] as List?) ?? [])
          .map((e) => VendorPaymentRecord.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class VendorPaymentRecord {
  final String id;
  final String? paymentNumber;
  final String? method;
  final double amount;
  final String status;
  final DateTime? capturedAt;
  final DateTime createdAt;

  VendorPaymentRecord({
    required this.id,
    this.paymentNumber,
    this.method,
    required this.amount,
    required this.status,
    this.capturedAt,
    required this.createdAt,
  });

  factory VendorPaymentRecord.fromJson(Map<String, dynamic> json) {
    return VendorPaymentRecord(
      id: json['id'] as String,
      paymentNumber: json['payment_number'] as String?,
      method: json['payment_method'] as String? ?? json['method'] as String?,
      amount: asDouble(json['amount']),
      status: json['status'] as String? ?? json['payment_status'] as String? ?? 'pending',
      capturedAt: json['captured_at'] != null ? DateTime.tryParse(json['captured_at'] as String) : null,
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
    );
  }
}
