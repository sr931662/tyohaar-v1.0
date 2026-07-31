import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/material.dart';

import '../l10n/generated/app_localizations.dart';

/// Wraps the whole app and shows a slim "you're offline" bar whenever the
/// device has no network connectivity. Purely presentational — it doesn't
/// block interaction or retry anything itself; screens still handle their
/// own load/retry failures, this just gives the user an immediate, global
/// explanation for why things aren't loading.
class OfflineBanner extends StatefulWidget {
  final Widget child;
  const OfflineBanner({super.key, required this.child});

  @override
  State<OfflineBanner> createState() => _OfflineBannerState();
}

class _OfflineBannerState extends State<OfflineBanner> {
  final Connectivity _connectivity = Connectivity();
  StreamSubscription<List<ConnectivityResult>>? _subscription;
  bool _isOffline = false;

  @override
  void initState() {
    super.initState();
    _subscription = _connectivity.onConnectivityChanged.listen(_update);
    _connectivity.checkConnectivity().then(_update);
  }

  void _update(List<ConnectivityResult> results) {
    final offline = results.isEmpty || results.every((r) => r == ConnectivityResult.none);
    if (mounted && offline != _isOffline) {
      setState(() => _isOffline = offline);
    }
  }

  @override
  void dispose() {
    _subscription?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        if (_isOffline)
          Material(
            color: Colors.black87,
            child: SafeArea(
              bottom: false,
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 12),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.wifi_off_rounded, color: Colors.white, size: 16),
                    const SizedBox(width: 8),
                    Flexible(
                      child: Text(
                        AppLocalizations.of(context)!.commonNoInternetConnection,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Colors.white, fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        Expanded(child: widget.child),
      ],
    );
  }
}
