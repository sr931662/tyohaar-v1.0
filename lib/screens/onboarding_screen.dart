import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/ty_button.dart';
import '../data/auth_manager.dart';
import 'root_nav.dart';
import 'auth_screen.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _pageController = PageController();
  int _currentPage = 0;

  final List<OnboardingData> _screens = [
    OnboardingData(
      title: 'Moments That Matter',
      subtitle: 'From a baby’s first steps to golden anniversaries, we turn milestones into memories.',
      icon: Icons.auto_awesome_rounded,
      tint: 'saffron',
    ),
    OnboardingData(
      title: 'Curated Perfection',
      subtitle: 'Browse hand-picked packages designed by experts to fit your unique style and budget.',
      icon: Icons.dashboard_customize_rounded,
      tint: 'rose',
    ),
    PlanOnboardingData(
      title: 'Stress-Free Planning',
      subtitle: 'We handle the vendors, the timeline, and the details. You just enjoy the celebration.',
      icon: Icons.checklist_rtl_rounded,
      tint: 'leaf',
    ),
    OnboardingData(
      title: 'Verified Excellence',
      subtitle: 'Every vendor is Tyohaar-vetted for quality and reliability. Trust is our foundation.',
      icon: Icons.verified_user_rounded,
      tint: 'gold',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Scaffold(
      backgroundColor: ty.paper,
      body: Stack(
        children: [
          // Animated Background Gradient
          AnimatedContainer(
            duration: const Duration(milliseconds: 600),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  ty.tint(_screens[_currentPage].tint).withOpacity(0.15),
                  ty.paper,
                ],
                stops: const [0.0, 0.4],
              ),
            ),
          ),
          
          PageView.builder(
            controller: _pageController,
            onPageChanged: (index) => setState(() => _currentPage = index),
            itemCount: _screens.length,
            itemBuilder: (context, index) {
              return _OnboardingPage(data: _screens[index]);
            },
          ),

          // Bottom Navigation Area
          Positioned(
            bottom: 60,
            left: 24,
            right: 24,
            child: Column(
              children: [
                // Page Indicator
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: List.generate(
                    _screens.length,
                    (index) => AnimatedContainer(
                      duration: const Duration(milliseconds: 300),
                      margin: const EdgeInsets.symmetric(horizontal: 4),
                      height: 8,
                      width: _currentPage == index ? 24 : 8,
                      decoration: BoxDecoration(
                        color: _currentPage == index ? ty.tint(_screens[_currentPage].tint) : ty.line,
                        borderRadius: BorderRadius.circular(4),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 32),
                
                // Primary Action Button
                TyButton(
                  _currentPage == _screens.length - 1 ? 'Start Celebrating' : 'Next',
                  full: true,
                  onTap: () async {
                    if (_currentPage < _screens.length - 1) {
                      _pageController.nextPage(
                        duration: const Duration(milliseconds: 400),
                        curve: Curves.easeInOut,
                      );
                    } else {
                      await AuthManager.instance.completeOnboarding();
                      if (!mounted) return;
                      Navigator.pushReplacement(
                        context,
                        MaterialPageRoute(builder: (_) => const AuthScreen()),
                      );
                    }
                  },
                ),
                
                if (_currentPage < _screens.length - 1)
                  TextButton(
                    onPressed: () async {
                      await AuthManager.instance.completeOnboarding();
                      if (!mounted) return;
                      Navigator.pushReplacement(
                        context,
                        MaterialPageRoute(builder: (_) => const AuthScreen()),
                      );
                    },
                    child: Text('Skip', style: TyType.sans(14, color: ty.ink3, weight: FontWeight.w600)),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class OnboardingData {
  final String title;
  final String subtitle;
  final IconData icon;
  final String tint;
  OnboardingData({required this.title, required this.subtitle, required this.icon, required this.tint});
}

class PlanOnboardingData extends OnboardingData {
  PlanOnboardingData({required super.title, required super.subtitle, required super.icon, required super.tint});
}

class _OnboardingPage extends StatelessWidget {
  final OnboardingData data;
  const _OnboardingPage({required this.data});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 40),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Animated Icon Container
          TweenAnimationBuilder<double>(
            tween: Tween(begin: 0.0, end: 1.0),
            duration: const Duration(milliseconds: 800),
            curve: Curves.elasticOut,
            builder: (context, value, child) {
              return Transform.scale(
                scale: value,
                child: Container(
                  width: 160,
                  height: 160,
                  decoration: BoxDecoration(
                    color: ty.tint(data.tint).withOpacity(0.1),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    data.icon,
                    size: 80,
                    color: ty.tint(data.tint),
                  ),
                ),
              );
            },
          ),
          const SizedBox(height: 60),
          
          // Animated Text Content
          TweenAnimationBuilder<double>(
            tween: Tween(begin: 0.0, end: 1.0),
            duration: const Duration(milliseconds: 600),
            builder: (context, value, child) {
              return Opacity(
                opacity: value,
                child: Transform.translate(
                  offset: Offset(0, 20 * (1 - value)),
                  child: child,
                ),
              );
            },
            child: Column(
              children: [
                Text(
                  data.title,
                  textAlign: TextAlign.center,
                  style: TyType.display(32, color: ty.ink),
                ),
                const SizedBox(height: 16),
                Text(
                  data.subtitle,
                  textAlign: TextAlign.center,
                  style: TyType.sans(16, color: ty.ink2, height: 1.5),
                ),
              ],
            ),
          ),
          const SizedBox(height: 100), // Space for bottom buttons
        ],
      ),
    );
  }
}
