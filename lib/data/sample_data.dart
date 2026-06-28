import 'package:flutter/material.dart';
import 'models.dart';

/// Sample content mirroring the web/prototype data. UI-only — replace with API.
class TyData {
  const TyData._();

  static const List<Occasion> occasions = [
    // Life Events
    Occasion.positional('haldi', 'Haldi', 'Haldi', Icons.spa_rounded, 'gold', 'A golden start to your forever.', 'life'),
    Occasion.positional('mehndi', 'Mehndi', 'Mehndi', Icons.brush_rounded, 'leaf', 'Intricate patterns of joy.', 'life'),
    Occasion.positional('proposal', 'Proposal Setup', 'Prastaav', Icons.favorite_rounded, 'rose', 'The moment that changes everything.', 'life'),
    Occasion.positional('bachelorette', 'Bachelorette', 'Party', Icons.nightlife_rounded, 'saffron', 'One last fling before the ring.', 'life'),
    Occasion.positional('birthday', 'Birthday', 'Janmdin', Icons.cake_rounded, 'saffron', 'From a baby’s first to a grandparent’s grand.', 'life'),
    Occasion.positional('anniversary', 'Anniversary', 'Saalgirah', Icons.auto_awesome_rounded, 'rose', 'Years worth toasting, together.', 'life'),
    Occasion.positional('housewarm', 'Housewarming', 'Griha Pravesh', Icons.home_work_rounded, 'leaf', 'Bless the new threshold, the right way.', 'life'),
    Occasion.positional('engagement', 'Engagement', 'Sagai', Icons.diamond_rounded, 'rose', 'Where two families become one.', 'life'),
    Occasion.positional('babyshower', 'Baby Shower', 'Godh Bharai', Icons.child_care_rounded, 'saffron', 'Welcome the little one with love.', 'life'),
    Occasion.positional('genderreveal', 'Gender Reveal', 'Khushkhabri', Icons.celebration_rounded, 'gold', 'Pink or Blue, we celebrate you.', 'life'),
    Occasion.positional('retirement', 'Retirement Party', 'Sanyas', Icons.emoji_events_rounded, 'leaf', 'A grand salute to a great career.', 'life'),

    // Major Festivals
    Occasion.positional('diwali', 'Diwali', 'Deepavali', Icons.local_fire_department_rounded, 'gold', 'The festival of lights and prosperity.', 'major_festival'),
    Occasion.positional('ekadashi', 'Ekadashi Decoration', 'Ekadashi', Icons.temple_hindu_rounded, 'saffron', 'Sacred decor for a holy day.', 'major_festival'),
    Occasion.positional('navratri', 'Navratri Decoration', 'Navratri', Icons.brightness_high_rounded, 'rose', 'Nine nights of divine celebration.', 'major_festival'),
    Occasion.positional('birthday_bash', 'Birthday Bash', 'Birthday', Icons.celebration_rounded, 'saffron', 'Make your special day unforgettable.', 'life'),
    Occasion.positional('anniversary_dinner', 'Anniversary Dinner', 'Anniversary', Icons.restaurant_rounded, 'rose', 'Celebrate your love with elegance.', 'life'),
    Occasion.positional('housewarming_griha', 'Griha Pravesh', 'Housewarming', Icons.home_rounded, 'leaf', 'Welcome positive vibes to your new home.', 'life'),
    Occasion.positional('durgapuja', 'Durga Puja', 'Pujo', Icons.temple_hindu_rounded, 'saffron', 'Celebrating the victory of good over evil.', 'major_festival'),
    Occasion.positional('ganeshchaturthi', 'Ganesh Chaturthi', 'Vinayaka Chavithi', Icons.temple_hindu_rounded, 'gold', 'Welcoming the Lord of Beginnings.', 'major_festival'),
    Occasion.positional('holi', 'Holi', 'Phagwah', Icons.palette_rounded, 'rose', 'A riot of colors and happiness.', 'major_festival'),
    Occasion.positional('dussehra', 'Dussehra', 'Vijayadashami', Icons.shield_rounded, 'saffron', 'The triumph of righteousness.', 'major_festival'),
    Occasion.positional('christmas', 'Christmas', 'Bada Din', Icons.park_rounded, 'leaf', 'Spreading peace and joy.', 'major_festival', heroImageUrl: 'assets/images/christmas.png'),
    Occasion.positional('newyear', 'New Year', 'Nav Varsh', Icons.auto_awesome_rounded, 'gold', 'A fresh start to a wonderful year.', 'major_festival'),
    Occasion.positional('shivratri', 'Shivratri', 'Mahashivratri', Icons.temple_hindu_rounded, 'leaf', 'The great night of Shiva.', 'major_festival'),

    // Minor Festivals
    Occasion.positional('janmashtami', 'Janmashtami', 'Gokulashtami', Icons.music_note_rounded, 'gold', 'Celebrating the birth of Lord Krishna.', 'minor_festival'),
    Occasion.positional('ramnavami', 'Ram Navami', 'Ram Navami', Icons.architecture_rounded, 'saffron', 'The birth of Lord Rama.', 'minor_festival'),
    Occasion.positional('rakshabandhan', 'Raksha Bandhan', 'Rakhi', Icons.volunteer_activism_rounded, 'rose', 'Celebrating the bond of protection.', 'minor_festival'),
    Occasion.positional('karvachauth', 'Karva Chauth', 'Karva Chauth', Icons.brightness_2_rounded, 'rose', 'A prayer for long life and love.', 'minor_festival'),
    Occasion.positional('lohri', 'Lohri', 'Lohri', Icons.whatshot_rounded, 'saffron', 'Celebrating the harvest and the sun.', 'minor_festival'),
    Occasion.positional('pongal', 'Pongal', 'Thai Pongal', Icons.agriculture_rounded, 'leaf', 'A festival of gratitude to nature.', 'minor_festival'),
    Occasion.positional('makarsankranti', 'Makar Sankranti', 'Uttarayan', Icons.air_rounded, 'gold', 'The transition of the sun.', 'minor_festival'),
    Occasion.positional('baisakhi', 'Baisakhi', 'Vaisakhi', Icons.agriculture_rounded, 'saffron', 'The harvest festival of Punjab.', 'minor_festival'),
    Occasion.positional('gurupurab', 'Gurupurab', 'Gurupurab', Icons.light_mode_rounded, 'gold', 'Celebrating the light of the Gurus.', 'minor_festival'),
    Occasion.positional('eid', 'Eid', 'Eid-ul-Fitr', Icons.nightlight_round, 'leaf', 'A celebration of faith and feast.', 'minor_festival'),
  ];

  static const List<Package> packages = [
    // Life Events
    Package(
      id: 'p_ess',
      name: 'Essential Birthday',
      price: 25000,
      category: 'life',
      inclusions: ['Balloons & Streamers', '1-Tier Custom Cake', 'Sound System', 'Digital Invites'],
      theme: 'Colorful Fun',
      description: 'The perfect foundation for a beautiful birthday without the fuss.',
      coverImageUrl: 'assets/images/birthday banner.png',
      tint: 'leaf',
    ),
    Package(
      id: 'p_anniv_prem',
      name: 'Premium Anniversary',
      price: 65000,
      category: 'life',
      inclusions: ['Exotic Floral Decor', '2-Tier Luxury Cake', 'Professional Photographer', 'Live Acoustic Singer'],
      theme: 'Midnight Rose',
      description: 'Celebrate your love with a touch of class and intimacy.',
      coverImageUrl: 'anniv_elegance',
      tint: 'rose',
    ),
    Package(
      id: 'p_haldi_har',
      name: 'Haldi Harmony',
      price: 45000,
      category: 'life',
      inclusions: ['Marigold Decor', 'Dhol Players', 'Seating for 30', 'Traditional Snacks'],
      theme: 'Saffron Yellow',
      description: 'A vibrant setup for your sun-soaked haldi ceremony.',
      coverImageUrl: 'haldi_har',
      tint: 'gold',
    ),
    Package(
      id: 'p_prop_lux',
      name: 'Proposal Surprise',
      price: 85000,
      category: 'life',
      inclusions: ['Rooftop Venue', 'Hidden Photographer', 'Marry Me Neon Sign', '5-Course Dinner'],
      theme: 'Starlight Romance',
      description: 'The ultimate way to say "Yes" in style.',
      coverImageUrl: 'prop_surprise',
      tint: 'saffron',
    ),
    Package(
      id: 'p_baby_prem',
      name: 'Baby Shower Premium',
      price: 55000,
      category: 'life',
      inclusions: ['Pastel Decor', 'Godh Bharai Rituals', 'Photo Booth', 'Custom Favors'],
      theme: 'Dreamy Clouds',
      description: 'A gentle and beautiful welcome for your bundle of joy.',
      coverImageUrl: 'baby_prem',
      tint: 'rose',
    ),

    // Major Festivals
    Package(
      id: 'p_diwali_grand',
      name: 'Diwali Grandeur',
      price: 120000,
      category: 'major_festival',
      inclusions: ['Full Home Illumination', 'Flower Rangoli Art', 'Gourmet Mithai Box', 'Laxmi Puja Setup'],
      theme: 'Royal Festival',
      description: 'Host the most magnificent Diwali gathering in your neighborhood.',
      coverImageUrl: 'diwali_grand',
      tint: 'gold',
    ),
    Package(
      id: 'p_ganesh_prem',
      name: 'Ganesh Utsav Special',
      price: 75000,
      category: 'major_festival',
      inclusions: ['Eco-friendly Mandap', 'Daily Fresh Flowers', 'Modak Platter', 'Visarjan Assistance'],
      theme: 'Divine Peace',
      description: 'A sacred and beautiful welcoming for Bappa.',
      coverImageUrl: 'ganesh_prem',
      tint: 'saffron',
    ),
    Package(
      id: 'p_navratri_night',
      name: 'Navratri Dandiya Night',
      price: 95000,
      category: 'major_festival',
      inclusions: ['Garba Arena Decor', 'DJ with Folk Music', 'Refreshment Counters', 'Dandiya Sticks'],
      theme: 'Neon Garba',
      description: 'Bring the energy of Gujarat to your private Navratri party.',
      coverImageUrl: 'navratri_night',
      tint: 'rose',
    ),
    Package(
      id: 'p_holi_hung',
      name: 'Holi Hungama',
      price: 40000,
      category: 'major_festival',
      inclusions: ['Organic Colors', 'Mist Fans', 'Rain Dance Setup', 'Thandai Bar'],
      theme: 'Splash of Joy',
      description: 'A colorful and messy celebration without any of the clean-up stress.',
      coverImageUrl: 'holi_hung',
      tint: 'leaf',
    ),
    Package(
      id: 'p_christmas_joy',
      name: 'Christmas Joy',
      price: 50000,
      category: 'major_festival',
      inclusions: ['7ft Decorated Tree', 'Santa Visit', 'Plum Cake', 'Dinner Spread'],
      theme: 'Winter Wonderland',
      description: 'A cozy and festive Christmas experience at home.',
      coverImageUrl: 'christmas_joy',
      tint: 'leaf',
    ),

    // Minor Festivals
    Package(
      id: 'p_rakhi_love',
      name: 'Raksha Bandhan Bundle',
      price: 15000,
      category: 'minor_festival',
      inclusions: ['Designer Rakhi Set', 'Thali Decor', 'Artisanal Sweets', 'Photo Printout'],
      theme: 'Sibling Bond',
      description: 'Make the promise of protection special with this curated kit.',
      coverImageUrl: 'rakhi_love',
      tint: 'rose',
    ),
    Package(
      id: 'p_karva_special',
      name: 'Karva Chauth Special',
      price: 28000,
      category: 'minor_festival',
      inclusions: ['Henna Artist', 'Sargi Basket', 'Moon-viewing Setup', 'Professional Makeup'],
      theme: 'Devotion',
      description: 'Everything you need for a traditional and elegant fast.',
      coverImageUrl: 'karva_special',
      tint: 'saffron',
    ),
    Package(
      id: 'p_lohri_fire',
      name: 'Lohri Bonfire Bash',
      price: 35000,
      category: 'minor_festival',
      inclusions: ['Bonfire Setup', 'Dhol Performance', 'Peanuts & Rewri', 'Gidda Group'],
      theme: 'Harvest Heat',
      description: 'Warm up your winter with a traditional Lohri celebration.',
      coverImageUrl: 'lohri_fire',
      tint: 'gold',
    ),
    Package(
      id: 'p_makar_kite',
      name: 'Makar Sankranti Kite Fest',
      price: 22000,
      category: 'minor_festival',
      inclusions: ['Kite & Manjha Supply', 'Terrace Decor', 'Til-Gud Sweets', 'Music System'],
      theme: 'Flying High',
      description: 'A fun-filled day of kite flying with friends and family.',
      coverImageUrl: 'makar_kite',
      tint: 'saffron',
    ),
    Package(
      id: 'p_eid_feast',
      name: 'Eid-ul-Fitr Feast',
      price: 60000,
      category: 'minor_festival',
      inclusions: ['Islamic Motif Decor', 'Sheer Khurma Service', 'Gourmet Biryani', 'Henna Artists'],
      theme: 'Graceful Eid',
      description: 'Celebrate the completion of Ramadan with a grand feast.',
      coverImageUrl: 'eid_feast',
      tint: 'leaf',
    ),
  ];

  static const List<Package> bestSellers = [
    Package(
      id: 'bs1',
      name: 'Birthday Bliss',
      price: 35000,
      category: 'life',
      inclusions: ['Themed Decor', 'Activities for Kids', 'Catering'],
      theme: 'Playful',
      description: 'Make their day magical with our top-rated birthday bundle.',
      coverImageUrl: 'bday_bliss',
      tint: 'saffron',
    ),
    Package(
      id: 'bs2',
      name: 'Anniversary Elegance',
      price: 75000,
      category: 'life',
      inclusions: ['Floral Setup', 'Candlelight Dinner', 'Music'],
      theme: 'Romantic',
      description: 'Celebrate your love with a touch of class and intimacy.',
      coverImageUrl: 'anniv_elegance',
      tint: 'rose',
    ),
    Package(
      id: 'bs3',
      name: 'Proposal Surprise',
      price: 45000,
      category: 'life',
      inclusions: ['Rooftop Booking', 'Hidden Photographer', 'Marry Me Sign'],
      theme: 'Surprise',
      description: 'The ultimate way to say "Yes" in style.',
      coverImageUrl: 'prop_surprise',
      tint: 'gold',
    ),
    Package(
      id: 'bs4',
      name: 'Baby Shower Premium',
      price: 60000,
      category: 'life',
      inclusions: ['Pastel Decor', 'Godh Bharai Rituals', 'Photo Booth'],
      theme: 'Serene',
      description: 'A gentle and beautiful welcome for your bundle of joy.',
      coverImageUrl: 'baby_prem',
      tint: 'saffron',
    ),
    Package(
      id: 'bs5',
      name: 'Bachelorette Bash',
      price: 55000,
      category: 'life',
      inclusions: ['Private Lounge', 'Karaoke', 'Custom Cocktails'],
      theme: 'Grand',
      description: 'The wildest night for the bride-to-be and her squad.',
      coverImageUrl: 'bach_bash',
      tint: 'rose',
    ),
  ];

  static const List<InvitationTemplate> invitations = [
    InvitationTemplate('i1', 'Traditional Gold', 'inv_trad_gold', 'Traditional'),
    InvitationTemplate('i2', 'Modern Minimal', 'inv_mod_min', 'Modern'),
    InvitationTemplate('i3', 'Floral Dream', 'inv_floral', 'Serene'),
    InvitationTemplate('i4', 'Royal Red', 'inv_royal', 'Grand'),
    InvitationTemplate('i5', 'Fun & Playful', 'inv_fun', 'Playful'),
  ];

  static const List<Address> addresses = [
    Address('a1', 'Home', 'A-42, Sky Heights, Sector 5, Malviya Nagar, Jaipur, Rajasthan 302017'),
    Address('a2', 'Office', 'B-10, IT Park, Sitapura Industrial Area, Jaipur, Rajasthan 302022'),
  ];

  static const Membership userMembership = Membership('Gold', 'Active', '12 Dec 2026');

  static const List<String> vibes = [
    'Intimate', 'Grand', 'Traditional', 'Modern', 'Playful', 'Serene'
  ];

  static const int budgetTotal = 600000;
  static const List<BudgetLine> budget = [
    BudgetLine('Venue', 220000, 100000, 'leaf'),
    BudgetLine('Catering', 187500, 50000, 'saffron'),
    BudgetLine('Photography', 140000, 0, 'rose'),
    BudgetLine('Décor', 85000, 42000, 'gold'),
    BudgetLine('Music', 65000, 0, 'leaf'),
    BudgetLine('Invitations', 12000, 12000, 'saffron'),
  ];

  // Keeping Vendor for internal references if needed, but UI will focus on Packages
  static const List<Vendor> vendors = [
    Vendor('v5', 'Venue', 'The Courtyard', 'Heritage open-air', 4.7, 3, '₹2.2L', 220000, 'leaf'),
    Vendor('v1', 'Catering', 'Saffron Table', 'Live thali counters', 4.9, 3, '₹1,250 / plate', 187500, 'saffron'),
    Vendor('v2', 'Décor', 'Marigold & Co.', 'Floral & light design', 4.8, 2, '₹85,000', 85000, 'gold'),
    Vendor('v3', 'Photography', 'Frame Stories', 'Candid + cinematic', 4.9, 3, '₹1.4L', 140000, 'rose'),
    Vendor('v4', 'Music', 'Dhol & Disco', 'Live dhol + DJ', 4.7, 2, '₹65,000', 65000, 'leaf'),
    Vendor('v6', 'Mehendi', 'Henna by Roohi', 'Bridal & guest art', 5.0, 1, '₹18,000', 18000, 'rose'),
    Vendor('v7', 'Invitations', 'Paper Diya', 'Bespoke e-cards', 4.8, 1, '₹12,000', 12000, 'saffron'),
    Vendor('v8', 'Cake & Sweets', 'Mithai Modern', 'Heirloom + dessert bar', 4.9, 2, '₹24,000', 24000, 'gold'),
  ];

  static List<Guest> seedGuests() => [
        Guest(id: 'g1', name: 'Sharma Family', count: 6, rsvpStatus: 'attending'),
        Guest(id: 'g2', name: 'Nanaji & Naniji', count: 2, rsvpStatus: 'attending'),
        Guest(id: 'g3', name: 'Priya & Rohit', count: 3, rsvpStatus: 'maybe'),
        Guest(id: 'g4', name: 'Kapoor Household', count: 5, rsvpStatus: 'pending'),
        Guest(id: 'g5', name: 'Anjali Mehta', count: 1, rsvpStatus: 'attending'),
        Guest(id: 'g6', name: 'Verma Family', count: 4, rsvpStatus: 'pending'),
        Guest(id: 'g7', name: 'Dr. Rao', count: 2, rsvpStatus: 'maybe'),
        Guest(id: 'g8', name: 'Iyer Cousins', count: 7, rsvpStatus: 'attending'),
      ];

  static List<PlanPhase> planTemplate() => [
        PlanPhase('Now', [
          PlanTask('Set the date & guest count', 'You', true),
          PlanTask('Lock the budget range', 'You', true),
        ]),
        PlanPhase('8 weeks before', [
          PlanTask('Confirm the venue', 'The Courtyard', true),
          PlanTask('Shortlist catering tasting', 'Saffron Table', false),
          PlanTask('Send save-the-dates', 'Paper Diya', false),
        ]),
        PlanPhase('4 weeks before', [
          PlanTask('Finalise décor & lighting', 'Marigold & Co.', false),
          PlanTask('Book photographer', 'Frame Stories', false),
          PlanTask('Plan the menu', 'Family', false),
        ]),
        PlanPhase('Celebration week', [
          PlanTask('Confirm headcount with caterer', 'You', false),
          PlanTask('Mehendi evening', 'Henna by Roohi', false),
          PlanTask('Welcome the family', 'Everyone', false),
        ]),
      ];

  static const List<NotifItem> notifs = [
    NotifItem.positional('chat', 'rose', 'Frame Stories', 'shared 3 sample albums for your review', '12m', true),
    NotifItem.positional('check', 'leaf', 'The Courtyard', 'confirmed your booking for Sat, 14 June', '1h', true),
    NotifItem.positional('users', 'saffron', 'Sharma Family', 'RSVP’d — 6 guests coming', '3h', true),
    NotifItem.positional('wallet', 'gold', 'Payment', '₹1,00,000 advance to The Courtyard succeeded', '5h', false),
    NotifItem.positional('spark', 'saffron', 'Tyohaar', 'Your plan is 35% complete — next: catering tasting', '1d', false),
    NotifItem.positional('gift', 'rose', 'Mithai Modern', 'sent a festive dessert-bar proposal', '2d', false),
  ];

  static const List<Memory> memories = [
    Memory.positional('Diwali at Home', 'Nov 2025', 'saffron', 48, 2),
    Memory.positional('Dadi’s 70th', 'Sep 2025', 'gold', 126, 1),
    Memory.positional('Holi 2025', 'Mar 2025', 'rose', 73, 1),
    Memory.positional('Aarav & Sneha', 'Dec 2024', 'leaf', 312, 2),
    Memory.positional('Naming Ceremony', 'Aug 2024', 'rose', 54, 1),
    Memory.positional('Griha Pravesh', 'May 2024', 'leaf', 61, 1),
  ];
}
