import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/typography.dart';
import '../data/models.dart';
import '../data/services/media_service.dart';
import '../widgets/photo_placeholder.dart';
import '../widgets/common.dart';

class MemoriesScreen extends StatefulWidget {
  const MemoriesScreen({super.key});

  @override
  State<MemoriesScreen> createState() => _MemoriesScreenState();
}

class _MemoriesScreenState extends State<MemoriesScreen> {
  final MediaService _mediaService = MediaService();
  List<Memory> _memories = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadMemories();
  }

  Future<void> _loadMemories() async {
    try {
      final memories = await _mediaService.listMemories();
      setState(() {
        _memories = memories;
        _isLoading = false;
      });
    } catch (e) {
      debugPrint('Error loading memories: $e');
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Scaffold(
      backgroundColor: ty.paper,
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator())
        : ListView(
            padding: const EdgeInsets.fromLTRB(18, 12, 18, 28),
            children: [
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Memories', style: TyType.display(26, color: ty.ink)),
                        const SizedBox(height: 1),
                        Text('Your family’s story, year by year',
                            style: TyType.sans(13, color: ty.ink2)),
                      ],
                    ),
                  ),
                  const ChromeIconButton(icon: Icons.search_rounded),
                ],
              ),
              const SizedBox(height: 20),
              if (_memories.isEmpty)
                _buildEmptyState(context)
              else
                _grid(context),
            ],
          ),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    final ty = context.ty;
    return Center(
      child: Padding(
        padding: const EdgeInsets.only(top: 80),
        child: Column(
          children: [
            Icon(Icons.photo_library_outlined, size: 64, color: ty.ink3),
            const SizedBox(height: 16),
            Text('No memories yet', style: TyType.display(20, color: ty.ink)),
            const SizedBox(height: 8),
            Text('Complete your first celebration to start your gallery.', 
              style: TyType.sans(14, color: ty.ink2)),
          ],
        ),
      ),
    );
  }

  Widget _grid(BuildContext context) {
    final rows = <Widget>[];
    int i = 0;
    while (i < _memories.length) {
      final m = _memories[i];
      if (m.span == 2) {
        rows.add(_tile(context, m, fullWidth: true));
        i += 1;
      } else {
        final left = _memories[i];
        final hasRight = i + 1 < _memories.length && _memories[i + 1].span == 1;
        rows.add(Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: _tile(context, left)),
            const SizedBox(width: 12),
            if (hasRight)
              Expanded(child: _tile(context, _memories[i + 1]))
            else
              const Expanded(child: SizedBox()),
          ],
        ));
        i += hasRight ? 2 : 1;
      }
      rows.add(const SizedBox(height: 12));
    }
    return Column(children: rows);
  }

  Widget _tile(BuildContext context, Memory m, {bool fullWidth = false}) {
    final h = fullWidth ? 150.0 : 170.0;
    return GestureDetector(
      onTap: () {},
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: Stack(
          children: [
            PhotoPlaceholder(tint: m.tint, height: h, arch: false),
            Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.bottomCenter,
                    end: Alignment.topCenter,
                    colors: [Colors.black.withOpacity(0.6), Colors.transparent],
                    stops: const [0, 0.6],
                  ),
                ),
              ),
            ),
            Positioned(
              top: 10,
              right: 10,
              child: TyPill('📷 ${m.photos}'),
            ),
            Positioned(
              left: 13,
              bottom: 11,
              right: 13,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(m.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TyType.display(fullWidth ? 22 : 18, color: Colors.white)),
                  const SizedBox(height: 2),
                  Text(m.date,
                      style: TextStyle(
                          fontSize: 11.5, color: Colors.white.withOpacity(0.85))),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
