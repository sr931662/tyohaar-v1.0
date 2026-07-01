import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../data/services/vendor_service.dart';
import '../../widgets/ty_button.dart';
import '../../widgets/ty_chip.dart';
import '../../widgets/common.dart';

class VendorAvailabilityScreen extends StatefulWidget {
  const VendorAvailabilityScreen({super.key});

  @override
  State<VendorAvailabilityScreen> createState() => _VendorAvailabilityScreenState();
}

class _VendorAvailabilityScreenState extends State<VendorAvailabilityScreen> {
  final VendorService _vendorService = VendorService();
  bool _isLoading = true;
  bool _isSaving = false;
  VendorProfile? _profile;

  TimeOfDay _openTime = const TimeOfDay(hour: 9, minute: 0);
  TimeOfDay _closeTime = const TimeOfDay(hour: 21, minute: 0);
  final Set<String> _offDays = {};

  final List<String> _days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    try {
      final profile = await _vendorService.getMyVendorProfile();
      if (mounted) {
        setState(() {
          _profile = profile;
          // Parse existing hours if any
          final hours = profile.workingHours?['mon'];
          if (hours != null) {
            _openTime = _parseTime(hours['open']);
            _closeTime = _parseTime(hours['close']);
          }
          // Parse off days
          for (final day in _days) {
            final dayKey = day.toLowerCase();
            if (profile.workingHours?[dayKey]?['is_open'] == false) {
              _offDays.add(day);
            }
          }
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  TimeOfDay _parseTime(String? timeStr) {
    if (timeStr == null) return const TimeOfDay(hour: 9, minute: 0);
    final parts = timeStr.split(':');
    return TimeOfDay(hour: int.parse(parts[0]), minute: int.parse(parts[1]));
  }

  String _formatTime(TimeOfDay time) {
    return '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}';
  }

  Future<void> _save() async {
    if (_isSaving) return;
    setState(() => _isSaving = true);

    try {
      final Map<String, dynamic> workingHours = {};
      for (final day in _days) {
        final dayKey = day.toLowerCase();
        final isOff = _offDays.contains(day);
        workingHours[dayKey] = {
          'is_open': !isOff,
          'open': isOff ? null : _formatTime(_openTime),
          'close': isOff ? null : _formatTime(_closeTime),
        };
      }

      await _vendorService.updateVendorProfile(_profile!.id, {
        'working_hours': workingHours,
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Availability updated!')),
        );
        Navigator.pop(context);
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isSaving = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to update. Please try again.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    if (_isLoading) {
      return Scaffold(backgroundColor: ty.paper, body: const Center(child: CircularProgressIndicator()));
    }

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: tyAppBar(context, title: 'Business Hours'),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text('Operating Times', style: TyType.display(22, color: ty.ink)),
          const SizedBox(height: 8),
          Text('Set your standard opening and closing hours.', style: TyType.sans(14, color: ty.ink2)),
          const SizedBox(height: 24),
          Row(
            children: [
              Expanded(child: _timePicker(context, 'OPENING', _openTime, (t) => setState(() => _openTime = t))),
              const SizedBox(width: 16),
              Expanded(child: _timePicker(context, 'CLOSING', _closeTime, (t) => setState(() => _closeTime = t))),
            ],
          ),
          const SizedBox(height: 40),
          Text('Weekly Off-Days', style: TyType.display(22, color: ty.ink)),
          const SizedBox(height: 8),
          Text('Select the days your business is closed.', style: TyType.sans(14, color: ty.ink2)),
          const SizedBox(height: 20),
          Wrap(
            spacing: 10,
            runSpacing: 12,
            children: _days.map((day) {
              final isOff = _offDays.contains(day);
              return TyChip(
                label: day,
                active: isOff,
                onTap: () {
                  setState(() {
                    if (isOff) _offDays.remove(day);
                    else _offDays.add(day);
                  });
                },
              );
            }).toList(),
          ),
          const SizedBox(height: 60),
          TyButton(
            _isSaving ? 'Saving...' : 'Save Availability',
            full: true,
            enabled: !_isSaving,
            onTap: _save,
          ),
        ],
      ),
    );
  }

  Widget _timePicker(BuildContext context, String label, TimeOfDay current, Function(TimeOfDay) onSelected) {
    final ty = context.ty;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: TyType.eyebrow(10, color: ty.ink3)),
        const SizedBox(height: 8),
        GestureDetector(
          onTap: () async {
            final t = await showTimePicker(context: context, initialTime: current);
            if (t != null) onSelected(t);
          },
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
            decoration: BoxDecoration(
              color: ty.surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: ty.line, width: 1.5),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(current.format(context), style: TyType.sans(16, color: ty.ink, weight: FontWeight.w700)),
                Icon(Icons.access_time_rounded, size: 18, color: ty.saffron),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
