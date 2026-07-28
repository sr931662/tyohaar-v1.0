import 'package:flutter/material.dart';

import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../data/vendor_models.dart';
import '../../data/services/vendor_service.dart';
import '../../l10n/generated/app_localizations.dart';

List<String> _dayLabels(BuildContext context) {
  final l10n = AppLocalizations.of(context)!;
  return [
    l10n.vendorAvailabilityDayMon,
    l10n.vendorAvailabilityDayTue,
    l10n.vendorAvailabilityDayWed,
    l10n.vendorAvailabilityDayThu,
    l10n.vendorAvailabilityDayFri,
    l10n.vendorAvailabilityDaySat,
    l10n.vendorAvailabilityDaySun,
  ];
}

/// Weekly schedule editor — mirrors the web VendorAvailabilityPage as
/// per-day expandable rows instead of a desktop 7-column grid.
class VendorAvailabilityScreen extends StatefulWidget {
  const VendorAvailabilityScreen({super.key});

  @override
  State<VendorAvailabilityScreen> createState() => _VendorAvailabilityScreenState();
}

class _VendorAvailabilityScreenState extends State<VendorAvailabilityScreen> {
  final _vendorService = VendorService();
  String? _vendorId;
  List<VendorAvailabilityDay> _days = List.generate(7, (i) => VendorAvailabilityDay(dayOfWeek: i));
  bool _isLoading = true;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      final vendor = await _vendorService.getMe();
      if (vendor == null) {
        setState(() => _isLoading = false);
        return;
      }
      final existing = await _vendorService.listAvailability(vendor.id);
      final byDay = {for (final d in existing) d.dayOfWeek: d};
      if (mounted) {
        setState(() {
          _vendorId = vendor.id;
          _days = List.generate(7, (i) => byDay[i] ?? VendorAvailabilityDay(dayOfWeek: i));
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _updateDay(int index, VendorAvailabilityDay updated) {
    setState(() {
      final list = [..._days];
      list[index] = updated;
      _days = list;
    });
  }

  void _copyMondayToWeekdays() {
    final monday = _days[0];
    setState(() {
      _days = List.generate(7, (i) {
        if (i >= 1 && i <= 4) {
          return VendorAvailabilityDay(
            id: _days[i].id,
            dayOfWeek: i,
            isWorking: monday.isWorking,
            openTime: monday.openTime,
            closeTime: monday.closeTime,
            breakStart: monday.breakStart,
            breakEnd: monday.breakEnd,
            maxBookingsPerDay: monday.maxBookingsPerDay,
          );
        }
        return _days[i];
      });
    });
  }

  Future<void> _save() async {
    if (_vendorId == null) return;
    setState(() => _isSaving = true);
    try {
      await Future.wait(_days.map((day) {
        if (day.id != null) {
          return _vendorService.updateAvailability(_vendorId!, day.id!, day);
        }
        return _vendorService.createAvailability(_vendorId!, day);
      }));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(AppLocalizations.of(context)!.vendorAvailabilitySavedMessage)));
        _load();
      }
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(AppLocalizations.of(context)!.vendorAvailabilitySaveError)));
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  Future<String?> _pickTime(String? current) async {
    final parts = current?.split(':');
    final initial = parts != null && parts.length >= 2
        ? TimeOfDay(hour: int.tryParse(parts[0]) ?? 9, minute: int.tryParse(parts[1]) ?? 0)
        : const TimeOfDay(hour: 9, minute: 0);
    final picked = await showTimePicker(context: context, initialTime: initial);
    if (picked == null) return current;
    return '${picked.hour.toString().padLeft(2, '0')}:${picked.minute.toString().padLeft(2, '0')}:00';
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    final l10n = AppLocalizations.of(context)!;

    if (_isLoading) {
      return const Scaffold(backgroundColor: Colors.transparent, body: Center(child: CircularProgressIndicator()));
    }
    if (_vendorId == null) {
      return Scaffold(
        backgroundColor: Colors.transparent,
        body: Center(child: Text(l10n.vendorAvailabilitySetupProfileMessage, style: TyType.sans(14, color: ty.ink2))),
      );
    }

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: ListView.separated(
        padding: const EdgeInsets.all(18),
        itemCount: _days.length + 2,
        separatorBuilder: (_, __) => const SizedBox(height: 10),
        itemBuilder: (context, i) {
          if (i == 0) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: OutlinedButton.icon(
                onPressed: _copyMondayToWeekdays,
                icon: const Icon(Icons.copy_rounded, size: 18),
                label: Text(l10n.vendorAvailabilityCopyMondayLabel),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
            );
          }
          if (i == _days.length + 1) {
            return Padding(
              padding: const EdgeInsets.only(top: 8),
              child: ElevatedButton(
                onPressed: _isSaving ? null : _save, 
                style: ElevatedButton.styleFrom(
                  backgroundColor: ty.saffron,
                  foregroundColor: ty.onPrimary,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: Text(_isSaving ? l10n.vendorAvailabilitySavingLabel : l10n.vendorAvailabilitySaveChangesLabel),
              ),
            );
          }
          final day = _days[i - 1];
          return Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: ty.line)),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(_dayLabels(context)[i], style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                    Switch(
                      value: day.isWorking,
                      onChanged: (v) => _updateDay(i, VendorAvailabilityDay(
                        id: day.id, dayOfWeek: i, isWorking: v, openTime: day.openTime, closeTime: day.closeTime,
                        breakStart: day.breakStart, breakEnd: day.breakEnd, maxBookingsPerDay: day.maxBookingsPerDay,
                      )),
                    ),
                  ],
                ),
                if (day.isWorking) ...[
                  const SizedBox(height: 8),
                  Row(children: [
                    Expanded(child: _timeButton(ty, l10n.vendorAvailabilityOpenLabel, day.openTime, () async {
                      final t = await _pickTime(day.openTime);
                      _updateDay(i, VendorAvailabilityDay(id: day.id, dayOfWeek: i, isWorking: true, openTime: t, closeTime: day.closeTime, breakStart: day.breakStart, breakEnd: day.breakEnd, maxBookingsPerDay: day.maxBookingsPerDay));
                    })),
                    const SizedBox(width: 8),
                    Expanded(child: _timeButton(ty, l10n.vendorAvailabilityCloseLabel, day.closeTime, () async {
                      final t = await _pickTime(day.closeTime);
                      _updateDay(i, VendorAvailabilityDay(id: day.id, dayOfWeek: i, isWorking: true, openTime: day.openTime, closeTime: t, breakStart: day.breakStart, breakEnd: day.breakEnd, maxBookingsPerDay: day.maxBookingsPerDay));
                    })),
                  ]),
                  const SizedBox(height: 8),
                  Row(children: [
                    Expanded(child: _timeButton(ty, l10n.vendorAvailabilityBreakStartLabel, day.breakStart, () async {
                      final t = await _pickTime(day.breakStart);
                      _updateDay(i, VendorAvailabilityDay(id: day.id, dayOfWeek: i, isWorking: true, openTime: day.openTime, closeTime: day.closeTime, breakStart: t, breakEnd: day.breakEnd, maxBookingsPerDay: day.maxBookingsPerDay));
                    })),
                    const SizedBox(width: 8),
                    Expanded(child: _timeButton(ty, l10n.vendorAvailabilityBreakEndLabel, day.breakEnd, () async {
                      final t = await _pickTime(day.breakEnd);
                      _updateDay(i, VendorAvailabilityDay(id: day.id, dayOfWeek: i, isWorking: true, openTime: day.openTime, closeTime: day.closeTime, breakStart: day.breakStart, breakEnd: t, maxBookingsPerDay: day.maxBookingsPerDay));
                    })),
                  ]),
                ],
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _timeButton(TyColors ty, String label, String? value, VoidCallback onTap) {
    final l10n = AppLocalizations.of(context)!;
    return OutlinedButton(
      onPressed: onTap,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(label, style: TyType.sans(10.5, color: ty.ink3)),
          Text(value?.substring(0, value.length >= 5 ? 5 : value.length) ?? l10n.vendorAvailabilityTimeUnsetLabel, style: TyType.sans(13, color: ty.ink)),
        ],
      ),
    );
  }
}
