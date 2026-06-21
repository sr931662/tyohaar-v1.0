import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/common.dart';

class AboutAppScreen extends StatelessWidget {
  const AboutAppScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'About App'),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
        children: [
          Center(
            child: Column(
              children: [
                const SizedBox(height: 24),
                Container(
                  width: 100,
                  height: 100,
                  decoration: BoxDecoration(color: ty.saffron, borderRadius: BorderRadius.circular(28)),
                  child: const Icon(Icons.celebration_rounded, color: Colors.white, size: 50),
                ),
                const SizedBox(height: 16),
                Text('Tyohaar', style: TyType.display(32, color: ty.ink)),
                Text('Version 1.0.4 (Build 122)', style: TyType.sans(12, color: ty.ink3)),
              ],
            ),
          ),
          const SizedBox(height: 48),
          Text('Our Mission', style: TyType.eyebrow(11, color: ty.ink3)),
          const SizedBox(height: 12),
          Text(
            'At Tyohaar, we believe that every milestone deserves to be celebrated with joy and zero stress. Our mission is to preserve tradition while embracing the convenience of the modern world, making family gatherings more meaningful and effortless.',
            style: TyType.sans(15, color: ty.ink2, height: 1.6),
          ),
          const SizedBox(height: 32),
          _item(context, 'Website', 'www.tyohaar.app'),
          _item(context, 'Follow us on Instagram', '@tyohaar.app'),
          _item(context, 'Contact Email', 'hello@tyohaar.app'),
          const SizedBox(height: 48),
          Center(
            child: Text('Made with ❤️ in Jaipur, Rajasthan', style: TyType.sans(13, color: ty.ink3)),
          ),
        ],
      ),
    );
  }

  Widget _item(BuildContext context, String label, String value) {
    final ty = context.ty;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
          Text(value, style: TyType.sans(14, color: ty.saffronDeep, weight: FontWeight.w700)),
        ],
      ),
    );
  }
}
