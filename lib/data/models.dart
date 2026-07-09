import 'package:flutter/material.dart';

/// Production-ready data models for the Tyohaar app.
/// Mapped to FastAPI backend schemas (server/app/schemas/*/response.py).

// ---------------------------------------------------------------------------
// USER  →  UserResponse
// ---------------------------------------------------------------------------

class User {
  final String id;
  final String? phone;
  final String? email;
  final String? fullName;
  final String? firstName;
  final String? lastName;
  // profile_photo_url lives in UserProfileResponse; backend may nest it as
  // 'profile.profile_photo_url' or include it via a merged endpoint.
  final String? profilePhotoUrl;
  final String role;
  final String status;

  User({
    required this.id,
    this.phone,
    this.email,
    this.fullName,
    this.firstName,
    this.lastName,
    this.profilePhotoUrl,
    required this.role,
    required this.status,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      phone: json['phone'],
      email: json['email'],
      fullName: json['full_name'],
      firstName: json['first_name'],
      lastName: json['last_name'],
      profilePhotoUrl:
          json['profile_photo_url'] as String? ??
          (json['profile'] as Map?)?['profile_photo_url'] as String?,
      role: json['role'] as String? ?? 'customer',
      status: json['account_status'] as String? ?? 'active',
    );
  }

  String get displayName =>
      fullName ??
      (firstName != null ? '$firstName ${lastName ?? ""}'.trim() : (phone ?? id));
}

// ---------------------------------------------------------------------------
// OCCASION  →  OccasionResponse
// ---------------------------------------------------------------------------

class Occasion {
  final String id;
  final String name;
  // name_localized is not in backend; kept for future localisation support.
  final String? nameLocalized;
  // icon is derived from icon_name if present; defaults to auto_awesome.
  final IconData icon;
  // tint is a UI concept — derived client-side from category.
  final String tint;
  final String? description;
  final String category;
  // Backend field: cover_image_url (was incorrectly read as hero_image_url).
  final String? heroImageUrl;
  // Raw icon URL returned by backend (icon_url field).
  final String? iconUrl;

  const Occasion({
    required this.id,
    required this.name,
    this.nameLocalized,
    required this.icon,
    required this.tint,
    this.description,
    required this.category,
    this.heroImageUrl,
    this.iconUrl,
  });

  // Compatibility constructor for positional arguments (kept for existing callsites).
  const Occasion.positional(
    this.id,
    this.name,
    this.nameLocalized,
    this.icon,
    this.tint,
    this.description,
    this.category, {
    this.heroImageUrl,
    this.iconUrl,
  });

  factory Occasion.fromJson(Map<String, dynamic> json) {
    final category = json['category']?.toString() ?? 'other';
    return Occasion(
      id: json['id'],
      name: json['name'],
      nameLocalized: json['name_localized'] as String?,
      // Backend sends icon_url (URL), not icon_name. _parseIcon falls back to
      // auto_awesome when icon_name is absent, which is the correct default.
      icon: _parseIcon(json['icon_name'] as String?),
      iconUrl: json['icon_url'] as String?,
      tint: _getCategoryTint(category),
      description: json['description'] as String?,
      category: category,
      // Was: json['hero_image_url'] — backend sends cover_image_url.
      heroImageUrl: json['cover_image_url'] as String?,
    );
  }

  static IconData _parseIcon(String? name) {
    switch (name) {
      case 'spa':
        return Icons.spa_rounded;
      case 'brush':
        return Icons.brush_rounded;
      case 'favorite':
        return Icons.favorite_rounded;
      case 'cake':
        return Icons.cake_rounded;
      case 'celebration':
        return Icons.celebration_rounded;
      default:
        return Icons.auto_awesome_rounded;
    }
  }

  static String _getCategoryTint(String? category) {
    if (category == 'life_event') return 'rose';
    if (category == 'major_festival') return 'gold';
    return 'saffron';
  }
}

// ---------------------------------------------------------------------------
// PACKAGE CATEGORY  →  PackageCategoryResponse
// ---------------------------------------------------------------------------

class PackageCategory {
  final String id;
  final String name;
  final String slug;
  final String? iconUrl;
  final String? coverImageUrl;
  final int displayOrder;

  const PackageCategory({
    required this.id,
    required this.name,
    required this.slug,
    this.iconUrl,
    this.coverImageUrl,
    this.displayOrder = 0,
  });

  factory PackageCategory.fromJson(Map<String, dynamic> json) {
    return PackageCategory(
      id: json['id'] as String,
      name: json['name'] as String,
      slug: json['slug'] as String,
      iconUrl: json['icon_url'] as String?,
      coverImageUrl: json['cover_image_url'] as String?,
      displayOrder: json['display_order'] as int? ?? 0,
    );
  }
}

// ---------------------------------------------------------------------------
// PACKAGE  →  PackageResponse / PackageDetailResponse
// ---------------------------------------------------------------------------

class Package {
  final String id;
  final String name;
  // base_price from backend.
  final double price;
  // Count returned by the list endpoint (inclusions_count field).
  final int inclusionsCount;
  // Full item names — populated only on detail endpoint (PackageDetailResponse.items).
  final List<String> inclusions;
  final String? slug;
  final String? description;
  // Backend field: short_description.
  final String? shortDescription;
  final String? coverImageUrl;
  // tint is a UI concept — derived client-side; backend has no tint field.
  final String tint;
  // UUID of the linked PackageCategory.
  final String? categoryId;
  final String? status;
  final bool isFeatured;
  final bool isCustomizable;
  final int? minGuests;
  final int? maxGuests;
  final double? durationHours;
  final double? averageRating;
  final int reviewCount;
  final int bookingCount;
  final String? vendorId;
  final String currency;
  final int displayOrder;
  // City slug where this package is offered (e.g. 'noida', 'mumbai').
  final String? citySlug;

  const Package({
    required this.id,
    required this.name,
    required this.price,
    this.inclusionsCount = 0,
    this.inclusions = const [],
    this.slug,
    this.description,
    this.shortDescription,
    this.coverImageUrl,
    required this.tint,
    this.categoryId,
    this.status,
    this.isFeatured = false,
    this.isCustomizable = false,
    this.minGuests,
    this.maxGuests,
    this.durationHours,
    this.averageRating,
    this.reviewCount = 0,
    this.bookingCount = 0,
    this.vendorId,
    this.currency = 'INR',
    this.displayOrder = 0,
    this.citySlug,
  });

  factory Package.fromJson(Map<String, dynamic> json) {
    final categoryId = json['category_id'] as String?;
    return Package(
      id: json['id'],
      name: json['name'],
      price: json['base_price'] != null
          ? double.tryParse(json['base_price'].toString()) ?? 0.0
          : 0.0,
      inclusionsCount: json['inclusions_count'] as int? ?? 0,
      inclusions: (json['items'] as List?)
              ?.map((item) => item['name'] as String)
              .toList() ??
          [],
      slug: json['slug'] as String?,
      description: json['description'] as String?,
      shortDescription: json['short_description'] as String?,
      coverImageUrl: json['cover_image_url'] as String?,
      // tint is derived — backend has no tint field.
      tint: _deriveTint(categoryId),
      categoryId: categoryId,
      status: json['status'] as String?,
      isFeatured: json['is_featured'] as bool? ?? false,
      isCustomizable: json['is_customizable'] as bool? ?? false,
      minGuests: json['min_guests'] as int?,
      maxGuests: json['max_guests'] as int?,
      durationHours: json['duration_hours'] != null
          ? double.tryParse(json['duration_hours'].toString())
          : null,
      averageRating: json['average_rating'] != null
          ? double.tryParse(json['average_rating'].toString())
          : null,
      reviewCount: json['review_count'] as int? ?? 0,
      bookingCount: json['booking_count'] as int? ?? 0,
      vendorId: json['vendor_id'] as String?,
      currency: json['currency'] as String? ?? 'INR',
      displayOrder: json['display_order'] as int? ?? 0,
      citySlug: json['city_slug'] as String?,
    );
  }

  // Backend sends category_id (UUID) — tint must be derived on the client.
  static String _deriveTint(String? categoryId) => 'saffron';
}

// ---------------------------------------------------------------------------
// PACKAGE ITEM  →  PackageItemResponse
// ---------------------------------------------------------------------------

class PackageItem {
  final String id;
  final String name;
  final String? description;
  // Backend field: unit (e.g. 'hours', 'pieces'). Was incorrectly read as item_type.
  final String? unit;
  // Backend field: base_price. Was incorrectly read as unit_price.
  final double unitPrice;
  final int quantity;
  // Derived as !is_mandatory. Backend sends is_mandatory, not is_optional.
  final bool isOptional;
  final bool isMandatory;
  final int displayOrder;

  const PackageItem({
    required this.id,
    required this.name,
    this.description,
    this.unit,
    required this.unitPrice,
    required this.quantity,
    required this.isOptional,
    required this.isMandatory,
    this.displayOrder = 0,
  });

  factory PackageItem.fromJson(Map<String, dynamic> json) {
    final isMandatory = json['is_mandatory'] as bool? ?? true;
    return PackageItem(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String?,
      // Was: json['item_type'] — backend has no item_type field; unit is closest.
      unit: json['unit'] as String?,
      // Was: json['unit_price'] — backend sends base_price.
      unitPrice: (json['base_price'] ?? 0).toDouble(),
      quantity: json['quantity'] as int? ?? 1,
      isMandatory: isMandatory,
      // Was: json['is_optional'] — backend sends is_mandatory (inverted).
      isOptional: !isMandatory,
      displayOrder: json['display_order'] as int? ?? 0,
    );
  }
}

// ---------------------------------------------------------------------------
// BOOKING  →  BookingResponse / BookingDetailResponse
// ---------------------------------------------------------------------------

class Booking {
  final String id;
  final String bookingNumber;
  final String status;
  final String paymentStatus;
  final double totalAmount;
  final double amountPaid;
  final double amountDue;
  final DateTime scheduledDate;
  // Backend sends package_id (UUID) — nested package object is NOT included in
  // BookingResponse. packageName/packageCoverUrl are only available if the
  // endpoint nests a 'package' object (non-standard extension).
  final String? packageId;
  final String? packageName;
  final String? packageCoverUrl;
  final String currency;
  final String? specialInstructions;
  final String? cancellationReason;
  final DateTime? confirmedAt;
  final DateTime? completedAt;
  final DateTime createdAt;

  Booking({
    required this.id,
    required this.bookingNumber,
    required this.status,
    required this.paymentStatus,
    required this.totalAmount,
    required this.amountPaid,
    required this.amountDue,
    required this.scheduledDate,
    this.packageId,
    this.packageName,
    this.packageCoverUrl,
    required this.currency,
    this.specialInstructions,
    this.cancellationReason,
    this.confirmedAt,
    this.completedAt,
    required this.createdAt,
  });

  factory Booking.fromJson(Map<String, dynamic> json) {
    return Booking(
      id: json['id'],
      bookingNumber: json['booking_number'],
      status: json['booking_status'],
      paymentStatus: json['payment_status'] as String? ?? 'pending',
      totalAmount: (json['total_amount'] ?? 0).toDouble(),
      amountPaid: (json['amount_paid'] ?? 0).toDouble(),
      amountDue: (json['amount_due'] ?? 0).toDouble(),
      scheduledDate: DateTime.parse(json['scheduled_date']),
      packageId: json['package_id'] as String?,
      // Backend does not nest the package object in BookingResponse.
      // These will be null unless the endpoint is extended to include them.
      packageName: (json['package'] as Map?)?['name'] as String?,
      packageCoverUrl:
          (json['package'] as Map?)?['cover_image_url'] as String?,
      currency: json['currency'] as String? ?? 'INR',
      specialInstructions: json['special_instructions'] as String?,
      cancellationReason: json['cancellation_reason'] as String?,
      confirmedAt: json['confirmed_at'] != null
          ? DateTime.tryParse(json['confirmed_at'] as String)
          : null,
      completedAt: json['completed_at'] != null
          ? DateTime.tryParse(json['completed_at'] as String)
          : null,
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

// ---------------------------------------------------------------------------
// WALLET  →  WalletResponse
// ---------------------------------------------------------------------------

class Wallet {
  final double availableBalance;
  final double pendingBalance;
  final double promotionalBalance;
  // Computed field returned by backend: available_balance + promotional_balance.
  final double totalSpendable;
  final int rewardPoints;
  final String currency;
  final String walletStatus;

  Wallet({
    required this.availableBalance,
    required this.pendingBalance,
    required this.promotionalBalance,
    required this.totalSpendable,
    required this.rewardPoints,
    required this.currency,
    required this.walletStatus,
  });

  factory Wallet.fromJson(Map<String, dynamic> json) {
    final available = (json['available_balance'] ?? 0).toDouble();
    final promotional = (json['promotional_balance'] ?? 0).toDouble();
    return Wallet(
      availableBalance: available,
      pendingBalance: (json['pending_balance'] ?? 0).toDouble(),
      promotionalBalance: promotional,
      totalSpendable: json['total_spendable'] != null
          ? (json['total_spendable'] as num).toDouble()
          : available + promotional,
      rewardPoints: json['reward_points'] as int? ?? 0,
      currency: json['currency'] as String? ?? 'INR',
      walletStatus: json['wallet_status'] as String? ?? 'active',
    );
  }
}

// ---------------------------------------------------------------------------
// WALLET TRANSACTION  →  WalletTransactionResponse
// ---------------------------------------------------------------------------

class WalletTransaction {
  final String id;
  final String type;
  final double amount;
  final double balanceBefore;
  final double balanceAfter;
  final String? description;
  final DateTime createdAt;

  WalletTransaction({
    required this.id,
    required this.type,
    required this.amount,
    required this.balanceBefore,
    required this.balanceAfter,
    this.description,
    required this.createdAt,
  });

  factory WalletTransaction.fromJson(Map<String, dynamic> json) {
    return WalletTransaction(
      id: json['id'],
      type: json['transaction_type'],
      amount: (json['amount'] ?? 0).toDouble(),
      balanceBefore: (json['balance_before'] ?? 0).toDouble(),
      balanceAfter: (json['balance_after'] ?? 0).toDouble(),
      description: json['description'] as String?,
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

// ---------------------------------------------------------------------------
// GUEST  →  CelebrationGuestResponse
// ---------------------------------------------------------------------------

class Guest {
  final String id;
  final String name;
  final String? phone;
  final String? email;
  String rsvpStatus;
  // Computed display status from the backend: mirrors rsvpStatus once the
  // guest has responded; otherwise 'pending' (never opened) or 'ignored'
  // (opened the RSVP link but didn't respond yet).
  final String displayStatus;
  final String? groupTag;
  final String? notes;
  final String? rsvpToken;
  final DateTime? invitationOpenedAt;
  // count is a UI-only field used in plan flow to specify party size.
  // Backend has no group_size; each guest record is one person.
  int count;

  Guest({
    required this.id,
    required this.name,
    this.phone,
    this.email,
    required this.rsvpStatus,
    this.displayStatus = 'pending',
    this.groupTag,
    this.notes,
    this.rsvpToken,
    this.invitationOpenedAt,
    this.count = 1,
  });

  factory Guest.fromJson(Map<String, dynamic> json) {
    return Guest(
      id: json['id'],
      name: json['name'],
      phone: json['phone'] as String?,
      email: json['email'] as String?,
      rsvpStatus: json['rsvp_status'] as String? ?? 'pending',
      displayStatus: json['display_status'] as String? ?? json['rsvp_status'] as String? ?? 'pending',
      groupTag: json['group_tag'] as String?,
      notes: json['notes'] as String?,
      rsvpToken: json['rsvp_token'] as String?,
      invitationOpenedAt: json['invitation_opened_at'] != null
          ? DateTime.tryParse(json['invitation_opened_at'] as String)
          : null,
    );
  }
}

// ---------------------------------------------------------------------------
// BUDGET EXPENSE  →  BudgetExpenseResponse
// ---------------------------------------------------------------------------

class BudgetExpense {
  final String id;
  final String category;
  final String title;
  // Backend has a single 'amount' field per expense entry.
  // The old estimated_amount / actual_amount fields do not exist in the backend.
  final double amount;
  // expense_type distinguishes planning-stage (estimated) vs realised expenses.
  final String expenseType;
  final bool isPaid;
  final String? vendorName;
  final String? receiptUrl;
  // tint is a UI concept — derived client-side from category.
  final String tint;

  BudgetExpense({
    required this.id,
    required this.category,
    required this.title,
    required this.amount,
    required this.expenseType,
    required this.isPaid,
    this.vendorName,
    this.receiptUrl,
    required this.tint,
  });

  factory BudgetExpense.fromJson(Map<String, dynamic> json) {
    final category = json['category'] as String? ?? '';
    return BudgetExpense(
      id: json['id'] as String? ?? '',
      category: category,
      title: json['title'] as String? ?? '',
      // Was: estimated_amount / actual_amount — backend sends single 'amount'.
      amount: (json['amount'] ?? 0).toDouble(),
      expenseType: json['expense_type'] as String? ?? 'estimated',
      isPaid: json['is_paid'] as bool? ?? false,
      vendorName: json['vendor_name'] as String?,
      receiptUrl: json['receipt_url'] as String?,
      // tint is derived — backend has no tint field.
      tint: _categoryTint(category),
    );
  }

  static String _categoryTint(String category) {
    switch (category) {
      case 'decoration':
        return 'rose';
      case 'catering':
        return 'gold';
      case 'photography':
        return 'saffron';
      default:
        return 'saffron';
    }
  }
}

// ---------------------------------------------------------------------------
// NOTIFICATION  →  NotificationResponse
// ---------------------------------------------------------------------------

class NotifItem {
  final String id;
  // icon and tint are derived client-side from notification_type.
  final String icon;
  final String tint;
  // who maps to notification title.
  final String who;
  // text maps to notification body.
  final String text;
  // time is the raw created_at string; format in the UI layer.
  final String time;
  // unread is the inverse of is_read.
  final bool unread;
  final String? actionUrl;
  final String? imageUrl;

  const NotifItem({
    required this.id,
    required this.icon,
    required this.tint,
    required this.who,
    required this.text,
    required this.time,
    required this.unread,
    this.actionUrl,
    this.imageUrl,
  });

  // Legacy positional constructor kept for existing hardcoded UI callsites.
  const NotifItem.positional(
    this.icon,
    this.tint,
    this.who,
    this.text,
    this.time,
    this.unread,
  )   : id = '',
        actionUrl = null,
        imageUrl = null;

  factory NotifItem.fromJson(Map<String, dynamic> json) {
    final type = json['notification_type'] as String? ?? '';
    return NotifItem(
      id: json['id'] as String? ?? '',
      icon: _typeIcon(type),
      tint: _typeTint(type),
      who: json['title'] as String? ?? '',
      text: json['body'] as String? ?? '',
      time: json['created_at'] as String? ?? '',
      unread: !(json['is_read'] as bool? ?? false),
      actionUrl: json['action_url'] as String?,
      imageUrl: json['image_url'] as String?,
    );
  }

  static String _typeIcon(String type) {
    switch (type) {
      case 'booking_confirmed':
        return 'check_circle';
      case 'payment_received':
        return 'payment';
      case 'booking_cancelled':
        return 'cancel';
      case 'offer':
        return 'local_offer';
      default:
        return 'notifications';
    }
  }

  static String _typeTint(String type) {
    switch (type) {
      case 'booking_confirmed':
        return 'green';
      case 'payment_received':
        return 'gold';
      case 'booking_cancelled':
        return 'rose';
      default:
        return 'saffron';
    }
  }
}

// ---------------------------------------------------------------------------
// UI-ONLY TYPES (no backend binding required)
// ---------------------------------------------------------------------------

class Memory {
  final String title;
  final String date;
  final String tint;
  final int photos;
  final int span;
  const Memory({
    required this.title,
    required this.date,
    required this.tint,
    required this.photos,
    required this.span,
  });

  const Memory.positional(
      this.title, this.date, this.tint, this.photos, this.span);
}

class Product {
  final String id;
  final String name;
  final int price;
  final String tint;
  final double rating;
  final int reviews;
  final String? description;
  final List<String>? themes;
  final String category;
  final Map<String, List<String>>? customizationOptions;

  const Product({
    required this.id,
    required this.name,
    required this.price,
    required this.tint,
    required this.rating,
    required this.reviews,
    this.description,
    this.themes,
    required this.category,
    this.customizationOptions,
  });
}

class InvitationTemplate {
  final String id;
  final String name;
  final String previewUrl;
  final String mood;
  const InvitationTemplate(this.id, this.name, this.previewUrl, this.mood);
}

// ---------------------------------------------------------------------------
// ADDRESS  →  UserAddressResponse
// ---------------------------------------------------------------------------

class Address {
  final String id;
  final String label;
  final String fullAddress;
  const Address(this.id, this.label, this.fullAddress);

  factory Address.fromJson(Map<String, dynamic> json) {
    return Address(
      json['id'],
      json['label'] as String? ?? 'Home',
      '${json['address_line_1']}, ${json['city']}, ${json['state']} ${json['postal_code']}',
    );
  }
}

// ---------------------------------------------------------------------------
// REVIEW  →  PackageReviewResponse / VendorReviewResponse
// ---------------------------------------------------------------------------

class Review {
  final String id;
  // reviewer_id is a UUID; username requires a nested user object (not in backend response).
  final String? reviewerId;
  final String userName;
  final String comment;
  final double rating;
  final String date;
  final int likes;

  const Review({
    this.id = '',
    this.reviewerId,
    required this.userName,
    required this.comment,
    required this.rating,
    required this.date,
    this.likes = 0,
  });

  factory Review.fromJson(Map<String, dynamic> json) {
    return Review(
      id: json['id'] as String? ?? '',
      reviewerId: json['reviewer_id'] as String?,
      // reviewer_id is a UUID; display name requires a nested user object.
      userName: (json['reviewer'] as Map?)?['full_name'] as String? ?? 'User',
      comment: json['body'] as String? ?? '',
      rating: (json['rating'] as num? ?? 0).toDouble(),
      date: json['created_at'] as String? ?? '',
      likes: 0, // backend has no likes field
    );
  }
}

// ---------------------------------------------------------------------------
// PACKAGE ITEM (alias kept for import compatibility)
// ---------------------------------------------------------------------------
// PackageItem is defined above.

// ---------------------------------------------------------------------------
// CELEBRATION  →  CelebrationResponse
// ---------------------------------------------------------------------------

class Celebration {
  final String id;
  final String title;
  // Backend sends occasion_id (UUID).
  final String? occasionId;
  final String? occasionName;
  final String? category;
  final String? heroImageUrl;
  final String? status;
  final DateTime? celebrationDate;
  final int guestCount;
  final String? venueName;
  final String? venueAddress;
  final int completionPercentage;
  final double? estimatedBudget;

  Celebration({
    required this.id,
    required this.title,
    this.occasionId,
    this.occasionName,
    this.category,
    this.heroImageUrl,
    this.status,
    this.celebrationDate,
    this.guestCount = 0,
    this.venueName,
    this.venueAddress,
    this.completionPercentage = 0,
    this.estimatedBudget,
  });

  factory Celebration.fromJson(Map<String, dynamic> json) {
    final occasion = json['occasion'] as Map?;
    return Celebration(
      id: json['id'] as String,
      title: json['title'] as String? ?? 'Untitled',
      occasionId: json['occasion_id'] as String?,
      occasionName: occasion?['name'] as String?,
      category: occasion?['category'] as String?,
      heroImageUrl: occasion?['cover_image_url'] as String?,
      status: json['status'] as String?,
      celebrationDate: json['celebration_date'] != null
          ? DateTime.tryParse(json['celebration_date'] as String)
          : null,
      guestCount: json['guest_count'] as int? ?? 0,
      venueName: json['venue_name'] as String?,
      venueAddress: json['venue_address'] as String?,
      completionPercentage: json['completion_percentage'] as int? ?? 0,
      estimatedBudget: json['estimated_budget'] != null
          ? double.tryParse(json['estimated_budget'].toString())
          : null,
    );
  }
}

// ---------------------------------------------------------------------------
// CELEBRATION CHECKLIST ITEM  →  CelebrationChecklistResponse
// ---------------------------------------------------------------------------

class CelebrationChecklistItem {
  final String id;
  final String title;
  final String? description;
  final bool isCompleted;
  final DateTime? completedAt;
  // Backend field: due_date. Was incorrectly read as timing / timing_label.
  final DateTime? dueDate;
  final int displayOrder;
  // timing_label and vendor_name/vendor do NOT exist in backend — removed.

  CelebrationChecklistItem({
    required this.id,
    required this.title,
    this.description,
    required this.isCompleted,
    this.completedAt,
    this.dueDate,
    this.displayOrder = 0,
  });

  factory CelebrationChecklistItem.fromJson(Map<String, dynamic> json) {
    return CelebrationChecklistItem(
      id: json['id'],
      title: json['title'],
      description: json['description'] as String?,
      isCompleted: json['is_completed'] as bool? ?? false,
      completedAt: json['completed_at'] != null
          ? DateTime.tryParse(json['completed_at'] as String)
          : null,
      // Was: json['timing_label'] ?? json['timing'] — backend has due_date.
      dueDate: json['due_date'] != null
          ? DateTime.tryParse(json['due_date'] as String)
          : null,
      displayOrder: json['display_order'] as int? ?? 0,
    );
  }

  // Convenience getter for UI display (replaces the old timing string).
  String? get timingLabel => dueDate != null
      ? '${dueDate!.day}/${dueDate!.month}/${dueDate!.year}'
      : null;
}

// ---------------------------------------------------------------------------
// MEMBERSHIP  →  UserMembershipResponse
// ---------------------------------------------------------------------------

class Membership {
  final String id;
  // Backend field: tier (was: type).
  final String type;
  final String status;
  // Backend field: expires_at (was: validTill as plain string).
  final String validTill;
  final bool autoRenew;
  final double? amountPaid;
  final String currency;
  final int? invitationsRemaining;
  // Computed field from backend: true when status is ACTIVE or GRACE_PERIOD.
  final bool isActive;

  const Membership({
    required this.id,
    required this.type,
    required this.status,
    required this.validTill,
    required this.autoRenew,
    this.amountPaid,
    required this.currency,
    this.invitationsRemaining,
    required this.isActive,
  });

  // Legacy positional constructor kept for existing hardcoded UI callsites.
  const Membership.positional(this.type, this.status, this.validTill)
      : id = '',
        autoRenew = false,
        amountPaid = null,
        currency = 'INR',
        invitationsRemaining = null,
        isActive = false;

  factory Membership.fromJson(Map<String, dynamic> json) {
    return Membership(
      id: json['id'] as String? ?? '',
      type: json['tier'] as String? ?? 'free',
      status: json['status'] as String? ?? 'inactive',
      validTill: json['expires_at'] as String? ?? '',
      autoRenew: json['auto_renew'] as bool? ?? false,
      amountPaid: json['amount_paid'] != null
          ? double.tryParse(json['amount_paid'].toString())
          : null,
      currency: json['currency'] as String? ?? 'INR',
      invitationsRemaining: json['invitations_remaining'] as int?,
      isActive: json['is_active'] as bool? ?? false,
    );
  }
}

// ---------------------------------------------------------------------------
// UI-ONLY TYPES (no backend binding)
// ---------------------------------------------------------------------------

class BudgetLine {
  final String cat;
  final int est;
  final int paid;
  final String tint;
  const BudgetLine(this.cat, this.est, this.paid, this.tint);
}

class Vendor {
  final String id;
  final String cat;
  final String name;
  final String note;
  final double rating;
  final int price; // 1..3
  final String from;
  final int est; // rupees
  final String tint;
  const Vendor(this.id, this.cat, this.name, this.note, this.rating, this.price,
      this.from, this.est, this.tint);
}

class PlanTask {
  final String title;
  final String who;
  bool done;
  PlanTask(this.title, this.who, this.done);
}

class PlanPhase {
  final String phase;
  final List<PlanTask> items;
  const PlanPhase(this.phase, this.items);
}
