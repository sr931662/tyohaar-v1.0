import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/ty_button.dart';
import '../widgets/common.dart';

class MyProfileScreen extends StatelessWidget {
  const MyProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'My Profile'),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          Center(
            child: Stack(
              children: [
                Container(
                  width: 100,
                  height: 100,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(color: ty.saffron, shape: BoxShape.circle),
                  child: Text('A', style: TextStyle(color: ty.onPrimary, fontWeight: FontWeight.w800, fontSize: 40)),
                ),
                Positioned(
                  bottom: 0,
                  right: 0,
                  child: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(color: ty.ink, shape: BoxShape.circle, border: Border.all(color: ty.paper, width: 2)),
                    child: const Icon(Icons.camera_alt_rounded, color: Colors.white, size: 16),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),
          _field(context, 'Full Name', 'Aarav Sharma'),
          _field(context, 'Email Address', 'aarav.sharma@gmail.com'),
          _field(context, 'Phone Number', '+91 98765 43210'),
          _field(context, 'Gender', 'Male'),
          _field(context, 'Date of Birth', '12 June 1995'),
          const SizedBox(height: 40),
          TyButton('Save Changes', full: true, onTap: () => Navigator.pop(context)),
        ],
      ),
    );
  }

  Widget _field(BuildContext context, String label, String value) {
    final ty = context.ty;
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label.toUpperCase(), style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 8),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: BoxDecoration(
              color: ty.surface,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: ty.line, width: 1.5),
            ),
            child: Text(value, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }
}
