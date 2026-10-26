import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../../data/services/invitation_service.dart';
import '../../l10n/generated/app_localizations.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../widgets/common.dart';
import 'invitation_labels.dart';

/// The host's own gate: scan a pass, type its code or find the guest, then
/// record entry or exit. Built for speed — one scan, one tap.
///
/// Nothing is shown as "checked in" until the server says it recorded it.
/// A check-in that got no answer keeps its scan id, so tapping again is safe:
/// the server either records it once or replays the earlier success.
class GateScanScreen extends StatefulWidget {
  final String celebrationId;
  final String celebrationTitle;

  /// Off for widget tests (no camera platform) or devices without one.
  final bool startCamera;
  const GateScanScreen({
    super.key,
    required this.celebrationId,
    required this.celebrationTitle,
    this.startCamera = true,
  });

  @override
  State<GateScanScreen> createState() => _GateScanScreenState();
}

class _GateScanScreenState extends State<GateScanScreen> {
  final _service = InvitationService();
  final _codeCtrl = TextEditingController();
  final _searchCtrl = TextEditingController();
  final MobileScannerController _scanner = MobileScannerController(
    detectionSpeed: DetectionSpeed.noDuplicates,
    formats: const [BarcodeFormat.qrCode],
  );

  GateSessionInfo? _session;
  late bool _cameraOn = widget.startCamera;
  bool _busy = false;
  GatePassRef? _ref;
  GateResult? _result;
  String? _error;
  int _party = 1;
  List<GateGuest> _matches = [];
  Timer? _searchDebounce;
  String? _lastScanned;
  DateTime _lastScanAt = DateTime.fromMillisecondsSinceEpoch(0);

  @override
  void initState() {
    super.initState();
    _loadSession();
  }

  @override
  void dispose() {
    _scanner.dispose();
    _codeCtrl.dispose();
    _searchCtrl.dispose();
    _searchDebounce?.cancel();
    super.dispose();
  }

  Future<void> _loadSession() async {
    try {
      final s = await _service.gateSession(widget.celebrationId);
      if (mounted) setState(() => _session = s);
    } catch (_) {/* counters are a convenience; the gate still works */}
  }

  void _onDetect(BarcodeCapture capture) {
    final raw = capture.barcodes.isEmpty ? null : capture.barcodes.first.rawValue;
    if (raw == null || _busy || _result != null) return;
    // The same pass held in front of the camera fires repeatedly.
    final now = DateTime.now();
    if (raw == _lastScanned && now.difference(_lastScanAt) < const Duration(seconds: 4)) return;
    _lastScanned = raw;
    _lastScanAt = now;
    _verify(GatePassRef(code: raw, method: 'qr'));
  }

  Future<void> _verify(GatePassRef ref) async {
    final l10n = AppLocalizations.of(context)!;
    FocusScope.of(context).unfocus();
    setState(() {
      _busy = true;
      _error = null;
      _ref = ref;
      _result = null;
    });
    try {
      final result = await _service.gateVerify(widget.celebrationId, ref);
      if (!mounted) return;
      final g = result.guest;
      setState(() {
        _result = result;
        _party = g == null ? 1 : (g.rsvpPartySize ?? 1).clamp(1, 1 + g.plusOnesAllowed);
      });
      _feedback(result.result);
    } catch (e) {
      if (mounted) setState(() => _error = isNoResponse(e) ? l10n.invGateNoConnectionVerify : invitationErrorMessage(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _record({required bool checkIn}) async {
    final l10n = AppLocalizations.of(context)!;
    final ref = _ref;
    if (ref == null || _busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final result = checkIn
          ? await _service.gateCheckIn(widget.celebrationId, ref, partySize: _party)
          : await _service.gateCheckOut(widget.celebrationId, ref);
      if (!mounted) return;
      setState(() => _result = result);
      _feedback(result.result);
      if (result.recorded) _loadSession();
    } catch (e) {
      // Same ref (same scan id) is kept, so the retry is idempotent.
      if (mounted) {
        setState(() => _error = isNoResponse(e) ? l10n.invGateNoConnectionRecord : invitationErrorMessage(e));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _feedback(String result) {
    final ok = result == 'valid' || result == 'checked_in' || result == 'checked_out';
    ok ? HapticFeedback.mediumImpact() : HapticFeedback.heavyImpact();
  }

  void _next() {
    setState(() {
      _result = null;
      _ref = null;
      _error = null;
      _matches = [];
      _party = 1;
    });
    _codeCtrl.clear();
    _searchCtrl.clear();
  }

  void _onSearch(String q) {
    _searchDebounce?.cancel();
    if (q.trim().length < 2) {
      setState(() => _matches = []);
      return;
    }
    _searchDebounce = Timer(const Duration(milliseconds: 300), () async {
      try {
        final found = await _service.gateSearch(widget.celebrationId, q.trim());
        if (mounted) setState(() => _matches = found);
      } catch (e) {
        if (mounted) setState(() => _error = invitationErrorMessage(e));
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final s = _session;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: l10n.invGateTitle),
      body: ListView(
        padding: EdgeInsets.fromLTRB(16, 4, 16, 24 + MediaQuery.paddingOf(context).bottom),
        children: [
          Text(widget.celebrationTitle, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: TyType.display(19, color: ty.ink)),
          const SizedBox(height: 10),
          Row(children: [
            _counter(context, s?.arrivedGuests, l10n.invStatArrived),
            const SizedBox(width: 8),
            _counter(context, s?.arrivedPeople, l10n.invStatPeopleIn),
            const SizedBox(width: 8),
            _counter(context, s?.stillExpected, l10n.invStatExpected),
          ]),
          const SizedBox(height: 14),
          if (_result != null || _error != null) _resultCard(context) else ...[
            _scannerBox(context),
            const SizedBox(height: 14),
            _manualEntry(context),
          ],
        ],
      ),
    );
  }

  Widget _scannerBox(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    return Column(children: [
      ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: AspectRatio(
          aspectRatio: 1,
          child: _cameraOn
              ? Stack(fit: StackFit.expand, children: [
                  MobileScanner(
                    controller: _scanner,
                    onDetect: _onDetect,
                    errorBuilder: (context, error) => Container(
                      color: ty.surface2,
                      padding: const EdgeInsets.all(24),
                      alignment: Alignment.center,
                      child: Text(
                        error.errorCode == MobileScannerErrorCode.permissionDenied
                            ? l10n.invCameraDenied
                            : l10n.invCameraUnavailable,
                        textAlign: TextAlign.center,
                        style: TyType.sans(14, color: ty.ink2),
                      ),
                    ),
                  ),
                  IgnorePointer(
                    child: Center(
                      child: Container(
                        width: 220,
                        height: 220,
                        decoration: BoxDecoration(
                          border: Border.all(color: Colors.white.withValues(alpha: 0.85), width: 3),
                          borderRadius: BorderRadius.circular(18),
                        ),
                      ),
                    ),
                  ),
                  if (_busy) const Center(child: CircularProgressIndicator()),
                ])
              : Container(
                  color: ty.surface2,
                  alignment: Alignment.center,
                  child: Icon(Icons.qr_code_scanner_rounded, size: 64, color: ty.ink3),
                ),
        ),
      ),
      TextButton.icon(
        onPressed: () => setState(() => _cameraOn = !_cameraOn),
        icon: Icon(_cameraOn ? Icons.videocam_off_outlined : Icons.videocam_outlined),
        label: Text(_cameraOn ? l10n.invCameraOff : l10n.invCameraOn),
      ),
    ]);
  }

  Widget _manualEntry(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final labels = InvitationLabels(context);
    InputDecoration deco(String label, {String? hint}) => InputDecoration(
          labelText: label,
          hintText: hint,
          filled: true,
          fillColor: ty.surface,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
        );
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [
        Expanded(
          child: TextField(
            controller: _codeCtrl,
            textCapitalization: TextCapitalization.characters,
            autocorrect: false,
            enableSuggestions: false,
            style: const TextStyle(fontFamily: 'monospace', letterSpacing: 2, fontWeight: FontWeight.w700),
            decoration: deco(l10n.invGateCodeLabel, hint: 'K7QM-3XPD'),
            onSubmitted: (v) => v.trim().isEmpty ? null : _verify(GatePassRef(code: v.trim(), method: 'manual')),
          ),
        ),
        const SizedBox(width: 8),
        SizedBox(
          height: 56,
          child: FilledButton(
            style: FilledButton.styleFrom(backgroundColor: ty.saffronDeep),
            onPressed: _busy
                ? null
                : () {
                    final v = _codeCtrl.text.trim();
                    if (v.isNotEmpty) _verify(GatePassRef(code: v, method: 'manual'));
                  },
            child: Text(l10n.invGateCheck),
          ),
        ),
      ]),
      const SizedBox(height: 12),
      TextField(
        controller: _searchCtrl,
        decoration: deco(l10n.invGateSearchLabel, hint: l10n.invGateSearchHint),
        onChanged: _onSearch,
      ),
      for (final g in _matches)
        ListTile(
          contentPadding: const EdgeInsets.symmetric(horizontal: 4),
          title: Text(g.name, style: TyType.sans(14.5, color: ty.ink, weight: FontWeight.w600)),
          subtitle: Text([labels.allowance(g.plusOnesAllowed), if (g.phoneMasked != null) g.phoneMasked!].join(' · '),
              style: TyType.sans(12.5, color: ty.ink3)),
          trailing: g.entryStatus == 'checked_in'
              ? Text(l10n.invPassInside, style: TyType.sans(12, color: ty.leaf, weight: FontWeight.w700))
              : const Icon(Icons.chevron_right_rounded),
          onTap: () => _verify(GatePassRef(guestId: g.id, method: 'search')),
        ),
      if (_searchCtrl.text.trim().length >= 2 && _matches.isEmpty)
        Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(l10n.invGateNoMatches, style: TyType.sans(13, color: ty.ink3)),
        ),
    ]);
  }

  Widget _resultCard(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;
    final labels = InvitationLabels(context);
    final r = _result;
    final g = r?.guest;
    final color = r == null ? ty.rose : labels.gateColor(r.result);
    final canCheckIn = r?.result == 'valid';
    final canCheckOut = g?.entryStatus == 'checked_in' && r?.result != 'checked_in';

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: ty.surface,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: color.withValues(alpha: 0.6), width: 2),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (r != null) ...[
          Semantics(
            liveRegion: true,
            child: Row(children: [
              Icon(
                labels.gateColor(r.result) == ty.leaf ? Icons.check_circle_rounded : Icons.error_rounded,
                color: color,
                size: 30,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  r.replayed ? l10n.invGateReplayed(labels.gateResult(r.result)) : labels.gateResult(r.result),
                  style: TyType.display(21, color: color),
                ),
              ),
            ]),
          ),
          const SizedBox(height: 6),
          Text(r.message, style: TyType.sans(13.5, color: ty.ink2)),
        ],
        if (g != null) ...[
          const SizedBox(height: 14),
          Text(g.name, style: TyType.display(24, color: ty.ink)),
          const SizedBox(height: 6),
          Text(labels.allowance(g.plusOnesAllowed), style: TyType.sans(14, color: ty.ink, weight: FontWeight.w600)),
          if (g.rsvpPartySize != null) Text(l10n.invGateRsvpParty(g.rsvpPartySize!), style: TyType.sans(13, color: ty.ink2)),
          if (labels.window(g.arrivalWindowStart, g.arrivalWindowEnd) != null)
            Text(l10n.invGateExpectedAt(labels.window(g.arrivalWindowStart, g.arrivalWindowEnd)!),
                style: TyType.sans(13, color: ty.ink2)),
          if (g.vehicleNumber != null) Text(l10n.invGateVehicle(g.vehicleNumber!), style: TyType.sans(13, color: ty.ink2)),
          if (g.checkedInAt != null)
            Text(l10n.invGateInSince(labels.when(g.checkedInAt!)), style: TyType.sans(13, color: ty.ink2)),
        ],
        for (final w in r?.warnings ?? const <String>[])
          Container(
            margin: const EdgeInsets.only(top: 10),
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(color: ty.gold.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(10)),
            child: Text(labels.warning(w), style: TyType.sans(12.5, color: ty.ink, weight: FontWeight.w700)),
          ),
        if (canCheckIn && g!.plusOnesAllowed > 0) ...[
          const SizedBox(height: 14),
          Row(children: [
            Expanded(child: Text(l10n.invGatePeopleEntering, style: TyType.sans(14, color: ty.ink))),
            IconButton(
              tooltip: l10n.invAllowanceLess,
              onPressed: _party > 1 ? () => setState(() => _party--) : null,
              icon: const Icon(Icons.remove_circle_outline_rounded),
            ),
            Text('$_party', style: TyType.sans(18, color: ty.ink, weight: FontWeight.w800)),
            IconButton(
              tooltip: l10n.invAllowanceMore,
              onPressed: _party < 1 + g.plusOnesAllowed ? () => setState(() => _party++) : null,
              icon: const Icon(Icons.add_circle_outline_rounded),
            ),
          ]),
        ],
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: Text(_error!, style: TyType.sans(13.5, color: ty.rose, weight: FontWeight.w700)),
          ),
        const SizedBox(height: 16),
        if (canCheckIn)
          _action(context, _busy ? l10n.invSaving : l10n.invGateCheckIn, ty.leaf, () => _record(checkIn: true)),
        if (canCheckOut) ...[
          const SizedBox(height: 8),
          _action(context, _busy ? l10n.invSaving : l10n.invGateCheckOut, ty.saffronDeep, () {
            // A check-out is a new action: give it its own scan id.
            _ref = _ref?.withNewScanId();
            _record(checkIn: false);
          }),
        ],
        if (_error != null && _ref != null && r == null) ...[
          const SizedBox(height: 8),
          _action(context, l10n.commonTryAgain, ty.saffronDeep, () => _verify(_ref!)),
        ],
        const SizedBox(height: 8),
        SizedBox(
          width: double.infinity,
          height: 50,
          child: OutlinedButton(onPressed: _busy ? null : _next, child: Text(l10n.invGateNext)),
        ),
      ]),
    );
  }

  Widget _action(BuildContext context, String label, Color color, VoidCallback onTap) => SizedBox(
        width: double.infinity,
        height: 54,
        child: FilledButton(
          style: FilledButton.styleFrom(backgroundColor: color, foregroundColor: Colors.white),
          onPressed: _busy ? null : onTap,
          child: Text(label, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
        ),
      );

  Widget _counter(BuildContext context, int? value, String label) {
    final ty = context.ty;
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: ty.line)),
        child: Column(children: [
          Text(value?.toString() ?? '–', style: TyType.display(20, color: ty.ink)),
          Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: TyType.sans(11.5, color: ty.ink3)),
        ]),
      ),
    );
  }
}
