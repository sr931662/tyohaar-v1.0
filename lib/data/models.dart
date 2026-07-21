import 'package:flutter/material.dart';

/// Production-ready data models for the Tyohaar app.
/// Mapped to FastAPI backend schemas (server/app/schemas/*/response.py).

/// Money/decimal fields are serialized as strings by the backend (e.g.
/// "1500.00") to avoid float precision loss — never call `.toDouble()`
/// directly on a JSON value that might be a String.
double asDouble(dynamic value) {
  if (value == null) return 0.0;
  if (value is num) return value.toDouble();
  return double.tryParse(value.toString()) ?? 0.0;
}

/// Some admin-managed image URL fields (banner_url, thumbnail_url, etc.)
/// are stored as an empty string rather than NULL when unset. Treating ''
/// as "present" breaks `a ?? b` fallback chains (an empty string is not
/// null), which silently renders a broken image instead of falling back —
/// this normalizes both null and blank/whitespace-only values to null.
String? asUrl(dynamic value) {
  if (value == null) return null;
  final s = value.toString().trim();
  return s.isEmpty ? null : s;
}

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
          asUrl(json['profile_photo_url']) ??
          asUrl((json['profile'] as Map?)?['profile_photo_url']),
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
  // Backend field: banner_url — full-width hero image for the detail page.
  final String? heroImageUrl;
  // Backend field: thumbnail_url — square card image for grid browse screens
  // (e.g. the "Other Moments" occasion cards).
  final String? thumbnailUrl;
  // Raw icon URL returned by backend (icon_url field).
  final String? iconUrl;
  // Backend field: theme_color_hex — brand/accent color for this occasion's
  // cards, e.g. '#C8A96E'. Null for occasions not yet migrated by an admin,
  // in which case callers should fall back to _getCategoryTint().
  final String? themeColorHex;

  const Occasion({
    required this.id,
    required this.name,
    this.nameLocalized,
    required this.icon,
    required this.tint,
    this.description,
    required this.category,
    this.heroImageUrl,
    this.thumbnailUrl,
    this.iconUrl,
    this.themeColorHex,
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
    this.thumbnailUrl,
    this.iconUrl,
    this.themeColorHex,
  });

  factory Occasion.fromJson(Map<String, dynamic> json) {
    final name = json['name']?.toString() ?? '';
    final category = json['category_id']?.toString() ?? 'other';
    return Occasion(
      id: json['id'],
      name: name,
      nameLocalized: json['name_localized'] as String?,
      // Backend sends icon_url (URL), not icon_name. _parseIcon falls back to
      // auto_awesome when icon_name is absent, which is the correct default.
      icon: _parseIcon(json['icon_name'] as String?),
      iconUrl: asUrl(json['icon_url']),
      tint: _getCategoryTint(category, name),
      description: json['description'] as String?,
      category: category,
      heroImageUrl: asUrl(json['banner_url']),
      thumbnailUrl: asUrl(json['thumbnail_url']),
      themeColorHex: json['theme_color_hex'] as String?,
    );
  }

  /// Parses [themeColorHex] into a [Color], or null if absent/invalid —
  /// callers should fall back to `context.ty.tint(o.tint)` when this is null.
  Color? get themeColor {
    final hex = themeColorHex;
    if (hex == null || hex.isEmpty) return null;
    var value = hex.replaceFirst('#', '');
    if (value.length != 6) return null;
    final parsed = int.tryParse(value, radix: 16);
    return parsed != null ? Color(0xFF000000 | parsed) : null;
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

  static String _getCategoryTint(String? category, String name) {
    final n = name.toLowerCase();
    
    // Milestones keywords
    if (n.contains('birth') || n.contains('anniv') || n.contains('grad') || n.contains('baby') || n.contains('shower')) {
      return 'rose';
    }
    
    // Memories (Wedding) keywords
    if (n.contains('wedding') || n.contains('mehndi') || n.contains('haldi') || n.contains('sangeet') || n.contains('marriage') || n.contains('engagement')) {
      return 'saffron';
    }
    
    // Growth (Corporate) keywords
    if (n.contains('corporate') || n.contains('annual') || n.contains('office') || n.contains('growth')) {
      return 'gold';
    }

    if (category == 'life_event') return 'rose';
    if (category == 'major_festival') return 'gold';
    return 'saffron';
  }
}

// ---------------------------------------------------------------------------
// OCCASION THEME → OccasionThemeResponse
// ---------------------------------------------------------------------------

class CelebrationTheme {
  final String id;
  final String name;
  final String? description;
  final String? coverImageUrl;
  final String? thumbnailUrl;
  final Map<String, String> colors;
  final bool isFeatured;

  const CelebrationTheme({
    required this.id,
    required this.name,
    this.description,
    this.coverImageUrl,
    this.thumbnailUrl,
    this.colors = const {},
    this.isFeatured = false,
  });

  /// Primary swatch color, falling back to a neutral gold if unset.
  String get primaryColorHex => colors['primary'] ?? '#C8A96E';

  factory CelebrationTheme.fromJson(Map<String, dynamic> json) {
    final rawColors = json['colors'] as Map<String, dynamic>?;
    return CelebrationTheme(
      id: json['id'],
      name: json['name'] ?? '',
      description: json['description'] as String?,
      coverImageUrl: asUrl(json['cover_image_url']),
      thumbnailUrl: asUrl(json['thumbnail_url']),
      colors: rawColors?.map((k, v) => MapEntry(k, v.toString())) ?? const {},
      isFeatured: json['is_featured'] as bool? ?? false,
    );
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
      iconUrl: asUrl(json['icon_url']),
      coverImageUrl: asUrl(json['cover_image_url']),
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
  // Additional images beyond the cover — populated only on the detail
  // endpoint (PackageDetailResponse.gallery). Cover is not duplicated here;
  // the UI is responsible for showing cover first, then these.
  final List<String> galleryImageUrls;
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
    this.galleryImageUrls = const [],
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
      coverImageUrl: asUrl(json['cover_image_url']),
      galleryImageUrls: (json['gallery'] as List?)
              ?.map((g) => g['file_url'] as String? ?? '')
              .where((u) => u.isNotEmpty)
              .toList() ??
          const [],
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
  // Default/minimum quantity from the package template.
  final int quantity;
  // Highest quantity the customer may pick at booking time. Null = uncapped.
  final int? maxQuantity;
  // Derived as !is_mandatory. Backend sends is_mandatory, not is_optional.
  final bool isOptional;
  final bool isMandatory;
  final bool isCustomizable;
  final String? iconUrl;
  // Item's cover/thumbnail image (mirrors Package.coverImageUrl).
  final String? coverImageUrl;
  final List<String> imageUrls;
  final int displayOrder;

  const PackageItem({
    required this.id,
    required this.name,
    this.description,
    this.unit,
    required this.unitPrice,
    required this.quantity,
    this.maxQuantity,
    required this.isOptional,
    required this.isMandatory,
    this.isCustomizable = false,
    this.iconUrl,
    this.coverImageUrl,
    this.imageUrls = const [],
    this.displayOrder = 0,
  });

  /// Whether the customer can select more than the template default —
  /// true whenever maxQuantity is null (uncapped) or greater than quantity.
  bool get isQuantityAdjustable => maxQuantity == null || maxQuantity! > quantity;

  /// Cover first, then gallery images deduped against it — the list a
  /// gallery viewer should page through.
  List<String> get allImageUrls => [
        if (coverImageUrl != null && coverImageUrl!.isNotEmpty) coverImageUrl!,
        ...imageUrls.where((u) => u != coverImageUrl),
      ];

  factory PackageItem.fromJson(Map<String, dynamic> json) {
    final isMandatory = json['is_mandatory'] as bool? ?? true;
    return PackageItem(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String?,
      // Was: json['item_type'] — backend has no item_type field; unit is closest.
      unit: json['unit'] as String?,
      // Was: json['unit_price'] — backend sends base_price.
      unitPrice: asDouble(json['base_price']),
      quantity: json['quantity'] as int? ?? 1,
      maxQuantity: json['max_quantity'] as int?,
      isMandatory: isMandatory,
      // Was: json['is_optional'] — backend sends is_mandatory (inverted).
      isOptional: !isMandatory,
      isCustomizable: json['is_customizable'] as bool? ?? false,
      iconUrl: asUrl(json['icon_url']),
      coverImageUrl: asUrl(json['cover_image_url']),
      imageUrls: (json['images'] as List?)
              ?.map((img) => img['image_url'] as String? ?? '')
              .where((u) => u.isNotEmpty)
              .toList() ??
          const [],
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
  final String celebrationId;
  final String status;
  final String paymentStatus;
  final double totalAmount;
  final double amountPaid;
  final double amountDue;
  final DateTime scheduledDate;
  final String? packageId;
  final String? packageName;
  final String? packageCoverUrl;
  final String currency;
  final String? specialInstructions;
  final String? cancellationReason;
  final DateTime? confirmedAt;
  final DateTime? completedAt;
  // Vendor-provided preparation start date + time (PST), null until set.
  final DateTime? preparationStartAt;
  final DateTime createdAt;

  Booking({
    required this.id,
    required this.bookingNumber,
    required this.celebrationId,
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
    this.preparationStartAt,
    required this.createdAt,
  });

  factory Booking.fromJson(Map<String, dynamic> json) {
    return Booking(
      id: json['id'],
      bookingNumber: json['booking_number'],
      celebrationId: json['celebration_id'],
      status: json['booking_status'],
      paymentStatus: json['payment_status'] as String? ?? 'pending',
      totalAmount: asDouble(json['total_amount']),
      amountPaid: asDouble(json['amount_paid']),
      amountDue: asDouble(json['amount_due']),
      scheduledDate: DateTime.parse(json['scheduled_date']),
      packageId: json['package_id'] as String?,
      packageName: json['package_name'] as String?,
      packageCoverUrl: asUrl(json['package_cover_url']),
      currency: json['currency'] as String? ?? 'INR',
      specialInstructions: json['special_instructions'] as String?,
      cancellationReason: json['cancellation_reason'] as String?,
      confirmedAt: json['confirmed_at'] != null
          ? DateTime.tryParse(json['confirmed_at'] as String)
          : null,
      completedAt: json['completed_at'] != null
          ? DateTime.tryParse(json['completed_at'] as String)
          : null,
      preparationStartAt: json['preparation_start_at'] != null
          ? DateTime.tryParse(json['preparation_start_at'] as String)
          : null,
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
      amount: asDouble(json['amount']),
      expenseType: json['expense_type'] as String? ?? 'estimated',
      isPaid: json['is_paid'] as bool? ?? false,
      vendorName: json['vendor_name'] as String?,
      receiptUrl: asUrl(json['receipt_url']),
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
  // Primary heading shown in the activity card.
  final String title;
  // Optional secondary label, usually the notification category.
  final String? subtitle;
  // Body copy shown under the title.
  final String text;
  // time is the raw created_at string; format in the UI layer.
  final String time;
  // unread is the inverse of is_read.
  final bool unread;
  final String? actionUrl;
  final String? imageUrl;
  final String? referenceType;
  final String? referenceId;

  const NotifItem({
    required this.id,
    required this.icon,
    required this.tint,
    required this.title,
    required this.text,
    required this.time,
    required this.unread,
    this.subtitle,
    this.actionUrl,
    this.imageUrl,
    this.referenceType,
    this.referenceId,
  });

  // Legacy positional constructor kept for existing hardcoded UI callsites.
  const NotifItem.positional(
  this.icon,
  this.tint,
  this.title,
  this.text,
  this.time,
  this.unread,
  )   : id = '',
        subtitle = null,
        actionUrl = null,
        imageUrl = null,
        referenceType = null,
        referenceId = null;

  factory NotifItem.fromJson(Map<String, dynamic> json) {
    final type = json['notification_type'] as String? ?? '';
    return NotifItem(
      id: json['id'] as String? ?? '',
      icon: _typeIcon(type),
      tint: _typeTint(type),
      title: json['title'] as String? ?? '',
      text: json['body'] as String? ?? '',
      time: json['created_at'] as String? ?? '',
      unread: !(json['is_read'] as bool? ?? false),
      subtitle: null,
      actionUrl: asUrl(json['action_url']),
      imageUrl: asUrl(json['image_url']),
      referenceType: json['reference_type'] as String?,
      referenceId: json['reference_id']?.toString(),
    );
  }

  NotifItem copyWith({
    String? id,
    String? icon,
    String? tint,
    String? title,
    String? subtitle,
    String? text,
    String? time,
    bool? unread,
    String? actionUrl,
    String? imageUrl,
    String? referenceType,
    String? referenceId,
  }) {
    return NotifItem(
      id: id ?? this.id,
      icon: icon ?? this.icon,
      tint: tint ?? this.tint,
      title: title ?? this.title,
      subtitle: subtitle ?? this.subtitle,
      text: text ?? this.text,
      time: time ?? this.time,
      unread: unread ?? this.unread,
      actionUrl: actionUrl ?? this.actionUrl,
      imageUrl: imageUrl ?? this.imageUrl,
      referenceType: referenceType ?? this.referenceType,
      referenceId: referenceId ?? this.referenceId,
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
  final String addressType;
  final String? recipientName;
  final String? recipientPhone;
  final String addressLine1;
  final String? addressLine2;
  final String? landmark;
  final String city;
  final String state;
  final String country;
  final String postalCode;
  final bool isDefault;

  const Address({
    required this.id,
    required this.label,
    this.addressType = 'home',
    this.recipientName,
    this.recipientPhone,
    required this.addressLine1,
    this.addressLine2,
    this.landmark,
    required this.city,
    required this.state,
    this.country = 'India',
    required this.postalCode,
    this.isDefault = false,
  });

  /// Single-line summary for display in cards/lists.
  String get fullAddress {
    final parts = [
      addressLine1,
      if (addressLine2 != null && addressLine2!.isNotEmpty) addressLine2,
      if (landmark != null && landmark!.isNotEmpty) 'near $landmark',
      city,
      '$state $postalCode',
    ];
    return parts.join(', ');
  }

  factory Address.fromJson(Map<String, dynamic> json) {
    return Address(
      id: json['id'],
      label: json['label'] as String? ?? 'Home',
      addressType: json['address_type'] as String? ?? 'home',
      recipientName: json['recipient_name'] as String?,
      recipientPhone: json['recipient_phone'] as String?,
      addressLine1: json['address_line_1'] as String? ?? '',
      addressLine2: json['address_line_2'] as String?,
      landmark: json['landmark'] as String?,
      city: json['city'] as String? ?? '',
      state: json['state'] as String? ?? '',
      country: json['country'] as String? ?? 'India',
      postalCode: json['postal_code'] as String? ?? '',
      isDefault: json['is_default'] as bool? ?? false,
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
  // Chosen theme's color palette (e.g. {"primary": "#...", "secondary": "#..."})
  // and cover image, denormalized onto CelebrationResponse since the theme
  // relationship isn't nested. Null when no theme was picked during planning.
  final Map<String, String>? themeColors;
  final String? themeCoverImageUrl;
  // Chosen mood (OccasionMood — distinct from InvitationTemplate.mood, which
  // is an unrelated template-categorization string), denormalized the same
  // way as theme_colors since CelebrationResponse doesn't nest relationships.
  final CelebrationMood? mood;

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
    this.themeColors,
    this.themeCoverImageUrl,
    this.mood,
  });

  factory Celebration.fromJson(Map<String, dynamic> json) {
    final rawThemeColors = json['theme_colors'] as Map?;
    return Celebration(
      id: json['id'] as String,
      title: json['title'] as String? ?? 'Untitled',
      occasionId: json['occasion_id'] as String?,
      occasionName: json['occasion_name'] as String?,
      category: null,
      themeColors: rawThemeColors
          ?.map((k, v) => MapEntry(k.toString(), v.toString())),
      themeCoverImageUrl: asUrl(json['theme_cover_image_url']),
      heroImageUrl: asUrl(json['occasion_hero_image_url']),
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
      mood: CelebrationMood.fromJson(json),
    );
  }
}

/// The chosen atmosphere/vibe for a celebration (e.g. "elegant", "grand",
/// "fun", "romantic"), denormalized onto CelebrationResponse as
/// mood_name/mood_slug/mood_emoji. Null when `mood` is entirely absent
/// (e.g. no mood was picked during planning).
class CelebrationMood {
  final String name;
  final String slug;
  final String? emoji;

  const CelebrationMood({required this.name, required this.slug, this.emoji});

  static CelebrationMood? fromJson(Map<String, dynamic> json) {
    final slug = json['mood_slug'] as String?;
    final name = json['mood_name'] as String?;
    if (slug == null || name == null) return null;
    return CelebrationMood(name: name, slug: slug, emoji: json['mood_emoji'] as String?);
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
