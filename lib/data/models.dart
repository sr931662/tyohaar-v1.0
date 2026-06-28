import 'package:flutter/material.dart';

/// Production-ready data models for the Tyohaar app.
/// Mapped to FastAPI backend schemas.

class User {
  final String id;
  final String phone;
  final String? email;
  final String? fullName;
  final String? firstName;
  final String? lastName;
  final String? profilePhotoUrl;
  final String role;
  final String status;

  User({
    required this.id,
    required this.phone,
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
      profilePhotoUrl: json['profile_photo_url'],
      role: json['role'] ?? 'customer',
      status: json['account_status'] ?? 'active',
    );
  }

  String get displayName => fullName ?? (firstName != null ? '$firstName ${lastName ?? ""}' : phone);
}

class Occasion {
  final String id;
  final String name;
  final String? nameLocalized;
  final IconData icon;
  final String tint;
  final String? description;
  final String category;
  final String? heroImageUrl;

  const Occasion({
    required this.id,
    required this.name,
    this.nameLocalized,
    required this.icon,
    required this.tint,
    this.description,
    required this.category,
    this.heroImageUrl,
  });

  // Compatibility constructor for positional arguments
  const Occasion.positional(this.id, this.name, this.nameLocalized, this.icon, this.tint, this.description, this.category, {this.heroImageUrl});

  factory Occasion.fromJson(Map<String, dynamic> json) {
    return Occasion(
      id: json['id'],
      name: json['name'],
      nameLocalized: json['name_localized'],
      icon: _parseIcon(json['icon_name']),
      tint: json['tint'] ?? _getCategoryTint(json['category']),
      description: json['description'],
      category: json['category'],
      heroImageUrl: json['hero_image_url'],
    );
  }

  static IconData _parseIcon(String? name) {
    switch (name) {
      case 'spa': return Icons.spa_rounded;
      case 'brush': return Icons.brush_rounded;
      case 'favorite': return Icons.favorite_rounded;
      case 'cake': return Icons.cake_rounded;
      case 'celebration': return Icons.celebration_rounded;
      default: return Icons.auto_awesome_rounded;
    }
  }

  static String _getCategoryTint(String category) {
    if (category == 'life_event') return 'rose';
    if (category == 'major_festival') return 'gold';
    return 'saffron';
  }
}

class Package {
  final String id;
  final String name;
  final double price;
  final List<String> inclusions;
  final String theme;
  final String? description;
  final String? coverImageUrl;
  final String tint;
  final String category;

  const Package({
    required this.id,
    required this.name,
    required this.price,
    required this.inclusions,
    required this.theme,
    this.description,
    this.coverImageUrl,
    required this.tint,
    required this.category,
  });

  factory Package.fromJson(Map<String, dynamic> json) {
    return Package(
      id: json['id'],
      name: json['name'],
      price: (json['base_price'] ?? 0).toDouble(),
      inclusions: (json['items'] as List?)?.map((item) => item['name'] as String).toList() ?? [],
      theme: json['slug'] ?? 'Default',
      description: json['description'],
      coverImageUrl: json['cover_image_url'],
      tint: json['tint'] ?? 'saffron',
      category: json['category_id'] ?? 'general',
    );
  }
}

class Booking {
  final String id;
  final String bookingNumber;
  final String status;
  final double totalAmount;
  final double amountPaid;
  final DateTime scheduledDate;
  final String? packageName;
  final String? packageCoverUrl;

  Booking({
    required this.id,
    required this.bookingNumber,
    required this.status,
    required this.totalAmount,
    required this.amountPaid,
    required this.scheduledDate,
    this.packageName,
    this.packageCoverUrl,
  });

  factory Booking.fromJson(Map<String, dynamic> json) {
    return Booking(
      id: json['id'],
      bookingNumber: json['booking_number'],
      status: json['booking_status'],
      totalAmount: (json['total_amount'] ?? 0).toDouble(),
      amountPaid: (json['amount_paid'] ?? 0).toDouble(),
      scheduledDate: DateTime.parse(json['scheduled_date']),
      packageName: json['package']?['name'],
      packageCoverUrl: json['package']?['cover_image_url'],
    );
  }
}

class Wallet {
  final double availableBalance;
  final int rewardPoints;
  final String currency;

  Wallet({
    required this.availableBalance,
    required this.rewardPoints,
    required this.currency,
  });

  factory Wallet.fromJson(Map<String, dynamic> json) {
    return Wallet(
      availableBalance: (json['available_balance'] ?? 0).toDouble(),
      rewardPoints: json['reward_points'] ?? 0,
      currency: json['currency'] ?? 'INR',
    );
  }
}

class WalletTransaction {
  final String id;
  final String type;
  final double amount;
  final String description;
  final DateTime createdAt;

  WalletTransaction({
    required this.id,
    required this.type,
    required this.amount,
    required this.description,
    required this.createdAt,
  });

  factory WalletTransaction.fromJson(Map<String, dynamic> json) {
    return WalletTransaction(
      id: json['id'],
      type: json['transaction_type'],
      amount: (json['amount'] ?? 0).toDouble(),
      description: json['description'] ?? '',
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

class Guest {
  final String id;
  final String name;
  int count;
  String rsvpStatus;

  Guest({
    required this.id,
    required this.name,
    this.count = 1,
    required this.rsvpStatus,
  });

  factory Guest.fromJson(Map<String, dynamic> json) {
    return Guest(
      id: json['id'],
      name: json['name'],
      count: json['group_size'] ?? 1,
      rsvpStatus: json['rsvp_status'] ?? 'pending',
    );
  }
}

class BudgetExpense {
  final String category;
  final double estimatedAmount;
  final double actualAmount;
  final String tint;

  BudgetExpense({
    required this.category,
    required this.estimatedAmount,
    required this.actualAmount,
    required this.tint,
  });

  factory BudgetExpense.fromJson(Map<String, dynamic> json) {
    return BudgetExpense(
      category: json['category'],
      estimatedAmount: (json['estimated_amount'] ?? 0).toDouble(),
      actualAmount: (json['actual_amount'] ?? 0).toDouble(),
      tint: json['tint'] ?? 'saffron',
    );
  }
}

class NotifItem {
  final String icon;
  final String tint;
  final String who;
  final String text;
  final String time;
  final bool unread;
  const NotifItem({
    required this.icon,
    required this.tint,
    required this.who,
    required this.text,
    required this.time,
    required this.unread,
  });

  const NotifItem.positional(this.icon, this.tint, this.who, this.text, this.time, this.unread);
}

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

  const Memory.positional(this.title, this.date, this.tint, this.photos, this.span);
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
  final String category; // 'Decoration', 'Cake', 'Bouquet'
  final Map<String, List<String>>? customizationOptions; // For Cakes etc.

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

class Address {
  final String id;
  final String label;
  final String fullAddress;
  const Address(this.id, this.label, this.fullAddress);

  factory Address.fromJson(Map<String, dynamic> json) {
    return Address(
      json['id'],
      json['label'] ?? 'Home',
      '${json['address_line_1']}, ${json['city']}, ${json['state']} ${json['postal_code']}',
    );
  }
}

class Review {
  final String userName;
  final String comment;
  final double rating;
  final String date;
  final int likes;
  const Review({
    required this.userName,
    required this.comment,
    required this.rating,
    required this.date,
    this.likes = 0,
  });
}

// RESTORED UI-ONLY TYPES
class Membership {
  final String type;
  final String status;
  final String validTill;
  const Membership(this.type, this.status, this.validTill);
}

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
