import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../../theme/colors.dart';
import '../../../theme/typography.dart';
import '../../../data/services/booking_service.dart';

class VendorMultimediaScreen extends StatefulWidget {
  const VendorMultimediaScreen({super.key});

  @override
  State<VendorMultimediaScreen> createState() => _VendorMultimediaScreenState();
}

class _VendorMultimediaScreenState extends State<VendorMultimediaScreen> {
  final _bookingService = BookingService();
  List<Map<String, dynamic>> _bookings = [];
  bool _isLoading = true;
  final Set<String> _uploadingIds = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      final bookings = await _bookingService.listVendorBookingMedia();
      if (mounted) setState(() { _bookings = bookings; _isLoading = false; });
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _uploadPhoto(String bookingId) async {
    final image = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 85);
    if (image == null) return;
    setState(() => _uploadingIds.add(bookingId));
    try {
      await _bookingService.uploadEventPhoto(bookingId, File(image.path));
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Photo uploaded.')));
      _load();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Upload failed.')));
    } finally {
      if (mounted) setState(() => _uploadingIds.remove(bookingId));
    }
  }

  Future<void> _uploadVideo(String bookingId) async {
    final video = await ImagePicker().pickVideo(source: ImageSource.gallery);
    if (video == null) return;
    setState(() => _uploadingIds.add(bookingId));
    try {
      await _bookingService.uploadEventVideo(bookingId, File(video.path));
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Video uploaded.')));
      _load();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Upload failed.')));
    } finally {
      if (mounted) setState(() => _uploadingIds.remove(bookingId));
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Scaffold(
      backgroundColor: ty.paper,
      appBar: AppBar(title: const Text('Multimedia')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _bookings.isEmpty
              ? Center(child: Text('No assigned bookings yet', style: TyType.sans(14, color: ty.ink2)))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView.separated(
                    padding: const EdgeInsets.all(18),
                    itemCount: _bookings.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 10),
                    itemBuilder: (context, i) {
                      final b = _bookings[i];
                      final bookingId = b['booking_id'] as String;
                      final canUpload = b['can_upload'] as bool? ?? false;
                      final isUploading = _uploadingIds.contains(bookingId);
                      return Container(
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(color: ty.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: ty.line)),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(b['event_title']?.toString() ?? 'Event', style: TyType.sans(15, color: ty.ink, weight: FontWeight.w700)),
                            Text(b['customer_name']?.toString() ?? '—', style: TyType.sans(13, color: ty.ink2)),
                            const SizedBox(height: 6),
                            Text('📷 ${b['image_count'] ?? 0} · 🎞️ ${b['video_count'] ?? 0}', style: TyType.sans(12, color: ty.ink3)),
                            const SizedBox(height: 10),
                            if (canUpload)
                              Wrap(spacing: 8, children: [
                                OutlinedButton(
                                  onPressed: isUploading ? null : () => _uploadPhoto(bookingId),
                                  child: Text(isUploading ? 'Uploading…' : '📷 Upload Photo'),
                                ),
                                OutlinedButton(
                                  onPressed: isUploading ? null : () => _uploadVideo(bookingId),
                                  child: Text(isUploading ? 'Uploading…' : '🎞️ Upload Video'),
                                ),
                              ])
                            else
                              Text('Media upload unlocks once this booking is confirmed.', style: TyType.sans(12, color: ty.ink3)),
                          ],
                        ),
                      );
                    },
                  ),
                ),
    );
  }
}
