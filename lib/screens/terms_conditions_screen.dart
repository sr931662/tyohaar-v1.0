import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shimmer/shimmer.dart';
import 'package:intl/intl.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/common.dart';
import '../widgets/simple_html_text.dart';
import '../data/services/common_service.dart';
import '../l10n/generated/app_localizations.dart';

class TermsConditionsScreen extends StatefulWidget {
  const TermsConditionsScreen({super.key});

  @override
  State<TermsConditionsScreen> createState() => _TermsConditionsScreenState();
}

class _TermsConditionsScreenState extends State<TermsConditionsScreen> {
  TermsVersion? _terms;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final terms = await context.read<CommonService>().getTerms();
      if (mounted) setState(() { _terms = terms; _loading = false; });
    } catch (_) {
      if (mounted) setState(() { _error = AppLocalizations.of(context)!.termsConditionsLoadError; _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: l10n.termsConditionsTitle),
      body: _loading
          ? Shimmer.fromColors(
              baseColor: ty.line,
              highlightColor: ty.surface2,
              child: ListView(
                padding: const EdgeInsets.all(20),
                children: List.generate(5, (_) => Container(
                  margin: const EdgeInsets.only(bottom: 20),
                  height: 80,
                  decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(12)),
                )),
              ),
            )
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.error_outline_rounded, size: 48, color: ty.rose),
                      const SizedBox(height: 12),
                      Text(_error!, style: TyType.sans(14, color: ty.ink2)),
                      const SizedBox(height: 16),
                      TextButton(
                        onPressed: _load,
                        child: Text(l10n.commonTryAgain, style: TyType.sans(14, color: ty.saffron, weight: FontWeight.w700)),
                      ),
                    ],
                  ),
                )
              : ListView(
                  padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                  children: [
                    if (_terms != null) ...[
                      Text(
                        l10n.policyVersionEffective(
                          _terms!.version,
                          DateFormat('d MMM y').format(_terms!.effectiveDate),
                        ),
                        style: TyType.sans(12, color: ty.ink3),
                      ),
                      const SizedBox(height: 24),
                      SimpleHtmlText(
                        _terms!.content,
                        bodyStyle: TyType.sans(14, color: ty.ink2, height: 1.7),
                        linkColor: ty.saffron,
                      ),
                    ],
                  ],
                ),
    );
  }
}
