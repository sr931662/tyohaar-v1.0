import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../theme/responsive.dart';
import '../widgets/ty_button.dart';
import '../data/auth_manager.dart';
import '../l10n/generated/app_localizations.dart';
import 'auth_screen.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _pageController = PageController();
  int _currentPage = 0;

  List<OnboardingData> _buildScreens(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return [
      OnboardingData(
        title: l10n.onboardingSlideOneTitle,
        subtitle: l10n.onboardingSlideOneSubtitle,
        icon: Icons.auto_awesome_rounded,
        image: 'assets/images/onboarding 1.png',
        tint: 'saffron',
      ),
      OnboardingData(
        title: l10n.onboardingSlideTwoTitle,
        subtitle: l10n.onboardingSlideTwoSubtitle,
        icon: Icons.dashboard_customize_rounded,
        image: 'assets/images/onboarding 2.png',
        tint: 'rose',
      ),
      PlanOnboardingData(
        title: l10n.onboardingSlideThreeTitle,
        subtitle: l10n.onboardingSlideThreeSubtitle,
        icon: Icons.checklist_rtl_rounded,
        image: 'assets/images/onboarding 3.png',
        tint: 'leaf',
      ),
      OnboardingData(
        title: l10n.onboardingSlideFourTitle,
        subtitle: l10n.onboardingSlideFourSubtitle,
        icon: Icons.verified_user_rounded,
        image: 'assets/images/onboarding 4.png',
        tint: 'gold',
      ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;
    final l10n = AppLocalizations.of(context)!;
    final screens = _buildScreens(context);

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
                  ty.tint(screens[_currentPage].tint).withValues(alpha: 0.15),
                  ty.paper,
                ],
                stops: const [0.0, 0.4],
              ),
            ),
          ),

          PageView.builder(
            controller: _pageController,
            onPageChanged: (index) => setState(() => _currentPage = index),
            itemCount: screens.length,
            itemBuilder: (context, index) {
              return _OnboardingPage(data: screens[index]);
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
                    screens.length,
                    (index) => AnimatedContainer(
                      duration: const Duration(milliseconds: 300),
                      margin: EdgeInsets.symmetric(horizontal: resp.w(4)),
                      height: resp.h(8),
                      width: _currentPage == index ? resp.w(24) : resp.w(8),
                      decoration: BoxDecoration(
                        color: _currentPage == index
                            ? ty.tint(screens[_currentPage].tint)
                            : ty.line,
                        borderRadius: BorderRadius.circular(4),
                      ),
                    ),
                  ),
                ),
                SizedBox(height: resp.h(32)),

                // Primary Action Button
                TyButton(
                  _currentPage == screens.length - 1
                      ? l10n.onboardingStartCelebratingButtonLabel
                      : l10n.tutorialNext,
                  full: true,
                  onTap: () async {
                    if (_currentPage < screens.length - 1) {
                      _pageController.nextPage(
                        duration: const Duration(milliseconds: 400),
                        curve: Curves.easeInOut,
                      );
                    } else {
                      await AuthManager.instance.completeOnboarding();
                      if (!context.mounted) return;
                      Navigator.pushReplacement(
                        context,
                        MaterialPageRoute(builder: (_) => const AuthScreen()),
                      );
                    }
                  },
                ),

                if (_currentPage < screens.length - 1)
                  TextButton(
                    onPressed: () async {
                      await AuthManager.instance.completeOnboarding();
                      if (!context.mounted) return;
                      Navigator.pushReplacement(
                        context,
                        MaterialPageRoute(builder: (_) => const AuthScreen()),
                      );
                    },
                    child: Text(l10n.tutorialSkip,
                        style: TyType.sans(resp.sp(14),
                            color: ty.ink3, weight: FontWeight.w600)),
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
  OnboardingData(
      {required this.title,
      required this.subtitle,
      required this.icon,
      required this.image,
      required this.tint});
}

class PlanOnboardingData extends OnboardingData {
  PlanOnboardingData(
      {required super.title,
      required super.subtitle,
      required super.icon,
      required super.image,
      required super.tint});
}

class _OnboardingPage extends StatelessWidget {
  final OnboardingData data;
  const _OnboardingPage({required this.data});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final resp = context.resp;

    return LayoutBuilder(
      builder: (context, constraints) => SingleChildScrollView(
        // Vertical scroll here doesn't fight the PageView's horizontal swipe,
        // and gives short screens / larger accessibility text scales a
        // graceful fallback instead of a RenderFlex overflow.
        padding: EdgeInsets.symmetric(horizontal: resp.w(40)),
        child: ConstrainedBox(
          constraints: BoxConstraints(minHeight: constraints.maxHeight),
          child: IntrinsicHeight(
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
                          color: ty.tint(data.tint).withValues(alpha: 0.1),
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
                        style: TyType.sans(resp.sp(16),
                            color: ty.ink2, height: 1.5),
                      ),
                    ],
                  ),
                ),
                SizedBox(height: resp.h(100)), // Space for bottom buttons
              ],
            ),
          ),
        ),
      ),
    );
  }
}
