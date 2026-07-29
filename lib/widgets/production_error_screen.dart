import 'package:flutter/material.dart';

/// Fallback UI shown in place of any widget that throws during build, in
/// release/profile builds only (debug keeps Flutter's default detailed red
/// screen — see main.dart's `ErrorWidget.builder` override).
///
/// Deliberately self-contained (no `context.ty`/app theme extensions, no
/// AppLocalizations): `ErrorWidget.builder` can run for a failure anywhere in
/// the tree, including above MaterialApp itself, so this can't assume any
/// ancestor (Theme, Directionality, Localizations) is actually present.
class ProductionErrorScreen extends StatelessWidget {
  const ProductionErrorScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.ltr,
      child: ColoredBox(
        color: const Color(0xFFF6F1E8),
        child: Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.error_outline_rounded, size: 48, color: Color(0xFFB3261E)),
                const SizedBox(height: 16),
                const Text(
                  'Something went wrong',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: Color(0xFF2A2018)),
                ),
                const SizedBox(height: 8),
                const Text(
                  "This screen couldn't load. Please try again — if it keeps happening, restart the app.",
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 13.5, color: Color(0xFF6B6258), height: 1.4),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
