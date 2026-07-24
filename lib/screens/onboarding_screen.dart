import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../theme/responsive.dart';
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
      image: 'assets/images/onboarding 1.png',
      tint: 'saffron',
    ),
    OnboardingData(
      title: 'Curated Perfection',
      subtitle: 'Browse hand-picked packages designed by experts to fit your unique style and budget.',
      icon: Icons.dashboard_customize_rounded,
      image: 'assets/images/onboarding 2.png',
      tint: 'rose',
    ),
    PlanOnboardingData(
      title: 'Stress-Free Planning',
      subtitle: 'We handle the vendors, the timeline, and the details. You just enjoy the celebration.',
      icon: Icons.checklist_rtl_rounded,
      image: 'assets/images/onboarding 3.png',
      tint: 'leaf',
    ),
    OnboardingData(
      title: 'Verified Excellence',
      subtitle: 'Every vendor is Tyohaar-vetted for quality and reliability. Trust is our foundation.',
      icon: Icons.verified_user_rounded,
      image: 'assets/images/onboarding 4.png',
      tint: 'gold',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;

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
            bottom: resp.h(60),
            left: resp.w(24),
            right: resp.w(24),
            child: Column(
              children: [
                // Page Indicator
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: List.generate(
                    _screens.length,
                    (index) => AnimatedContainer(
                      duration: const Duration(milliseconds: 300),
                      margin: EdgeInsets.symmetric(horizontal: resp.w(4)),
                      height: resp.h(8),
                      width: _currentPage == index ? resp.w(24) : resp.w(8),
                      decoration: BoxDecoration(
                        color: _currentPage == index ? ty.tint(_screens[_currentPage].tint) : ty.line,
                        borderRadius: BorderRadius.circular(4),
                      ),
                    ),
                  ),
                ),
                SizedBox(height: resp.h(32)),
                
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
                    child: Text('Skip', style: TyType.sans(resp.sp(14), color: ty.ink3, weight: FontWeight.w600)),
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
  final String image;
  final String tint;
  OnboardingData({required this.title, required this.subtitle, required this.icon, required this.image, required this.tint});
}

class PlanOnboardingData extends OnboardingData {
  PlanOnboardingData({required super.title, required super.subtitle, required super.icon, required super.image, required super.tint});
}

class _OnboardingPage extends StatelessWidget {
  final OnboardingData data;
  const _OnboardingPage({required this.data});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;

    return SingleChildScrollView(
      physics: const NeverScrollableScrollPhysics(), // Managed by PageView
      child: Container(
        height: MediaQuery.of(context).size.height,
        padding: EdgeInsets.symmetric(horizontal: resp.w(40)),
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
                    width: resp.w(220),
                    height: resp.w(220),
                    decoration: BoxDecoration(
                      color: ty.tint(data.tint).withOpacity(0.1),
                      shape: BoxShape.circle,
                    ),
                    child: Padding(
                      padding: EdgeInsets.all(resp.w(24)),
                      child: Image.asset(
                        data.image,
                        fit: BoxFit.contain,
                      ),
                    ),
                  ),
                );
              },
            ),
            SizedBox(height: resp.h(60)),
            
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
                    style: TyType.display(resp.sp(32), color: ty.ink),
                  ),
                  SizedBox(height: resp.h(16)),
                  Text(
                    data.subtitle,
                    textAlign: TextAlign.center,
                    style: TyType.sans(resp.sp(16), color: ty.ink2, height: 1.5),
                  ),
                ],
              ),
            ),
            SizedBox(height: resp.h(100)), // Space for bottom buttons
          ],
        ),
      ),
    );
  }
}
