import 'package:flutter/widgets.dart';

/// Plain data models for the Tyohaar UI layer.
/// Swap these for API/JSON-backed models when the Node backend is ready.

class Occasion {
  final String id;
  final String en;
  final String sub; // mother-tongue name
  final IconData icon; 
  final String tint; // saffron | rose | leaf | gold
  final String blurb;
  final String category; // 'life' | 'major_festival' | 'minor_festival'
  final String? heroImage;

  const Occasion(this.id, this.en, this.sub, this.icon, this.tint, this.blurb, this.category, {this.heroImage});
}

class Package {
  final String id;
  final String name;
  final int price;
  final List<String> inclusions;
  final String theme;
  final String description;
  final String coverImage;
  final String tint;
  final String category; // 'life' | 'major_festival' | 'minor_festival'
  const Package({
    required this.id,
    required this.name,
    required this.price,
    required this.inclusions,
    required this.theme,
    required this.description,
    required this.coverImage,
    required this.tint,
    required this.category,
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
}

class Membership {
  final String type;
  final String status;
  final String validTill;
  const Membership(this.type, this.status, this.validTill);
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

class Guest {
  String name;
  int count;
  String rsvp; // yes | maybe | pending
  Guest(this.name, this.count, this.rsvp);
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

class BudgetLine {
  final String cat;
  final int est;
  final int paid;
  final String tint;
  const BudgetLine(this.cat, this.est, this.paid, this.tint);
}

class NotifItem {
  final String icon;
  final String tint;
  final String who;
  final String text;
  final String time;
  final bool unread;
  const NotifItem(this.icon, this.tint, this.who, this.text, this.time, this.unread);
}

class Memory {
  final String title;
  final String date;
  final String tint;
  final int photos;
  final int span; // 1 or 2 grid columns
  const Memory(this.title, this.date, this.tint, this.photos, this.span);
}

class ExploreItem {
  final String title;
  final String tint;
  final String tag;
  const ExploreItem(this.title, this.tint, this.tag);
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
