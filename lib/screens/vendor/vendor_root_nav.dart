import 'package:flutter/material.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';
import '../../data/app_state.dart';
import '../../widgets/ty_button.dart';
import 'vendor_home_screen.dart';

class VendorRootNav extends StatefulWidget {
  const VendorRootNav({super.key});

  @override
  State<VendorRootNav> createState() => _VendorRootNavState();
}

class _VendorRootNavState extends State<VendorRootNav> {
  int _index = 0;
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();

  late final List<Widget> _pages;

  @override
  void initState() {
    super.initState();
    _pages = [
      VendorHomeScreen(onOpenDrawer: () => _scaffoldKey.currentState?.openDrawer()),
      const Center(child: Text('Schedule')),
      const Center(child: Text('Portfolio')),
      const _VendorBusinessTab(),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;

    return Scaffold(
      key: _scaffoldKey,
      drawer: _VendorSidebar(
        onNavigate: (i) {
          setState(() => _index = i);
          Navigator.pop(context);
        },
      ),
      body: IndexedStack(
        index: _index,
        children: _pages,
      ),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: ty.paper,
          border: Border(top: BorderSide(color: ty.line2)),
        ),
        padding: EdgeInsets.only(
          top: 10,
          bottom: MediaQuery.of(context).padding.bottom + 10,
        ),
        child: Row(
          children: [
            _navItem(0, Icons.dashboard_outlined, Icons.dashboard_rounded, 'Home'),
            _navItem(1, Icons.calendar_today_outlined, Icons.calendar_today_rounded, 'Schedule'),
            _navItem(2, Icons.collections_outlined, Icons.collections_rounded, 'Portfolio'),
            _navItem(3, Icons.business_center_outlined, Icons.business_center_rounded, 'Business'),
          ],
        ),
      ),
    );
  }

  Widget _navItem(int i, IconData icon, IconData active, String label) {
    final ty = context.ty;
    final selected = _index == i;
    final color = selected ? ty.saffron : ty.ink3;
    
    return Expanded(
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () => setState(() => _index = i),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(selected ? active : icon, color: color, size: 24),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 10.5,
                fontWeight: selected ? FontWeight.w700 : FontWeight.w600,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _VendorBusinessTab extends StatelessWidget {
  const _VendorBusinessTab();

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Scaffold(
      backgroundColor: ty.paper,
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text('Business Settings', style: TyType.display(28, color: ty.ink)),
              const SizedBox(height: 12),
              Text('Manage your vendor profile and settings here.', 
                  textAlign: TextAlign.center,
                  style: TyType.sans(15, color: ty.ink2)),
              const SizedBox(height: 40),
              TyButton(
                'Switch to Customer POV',
                full: true,
                kind: TyButtonKind.soft,
                leadingIcon: Icons.person_outline_rounded,
                onTap: () => AppState.instance.setPOV(UserPOV.customer),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _VendorSidebar extends StatelessWidget {
  final ValueChanged<int> onNavigate;
  const _VendorSidebar({required this.onNavigate});

  @override
  Widget build(BuildContext context) {
    final ty = context.ty;
    return Drawer(
      backgroundColor: ty.paper,
      width: MediaQuery.of(context).size.width * 0.82,
      child: Column(
        children: [
          _buildHeader(context),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(vertical: 12),
              children: [
                _drawerItem(context, Icons.dashboard_outlined, 'Dashboard', 0),
                _drawerItem(context, Icons.calendar_today_outlined, 'Schedule', 1),
                _drawerItem(context, Icons.collections_outlined, 'Portfolio', 2),
                _drawerItem(context, Icons.business_center_outlined, 'Business', 3),
                const Divider(height: 32, indent: 20, endIndent: 20, color: Colors.black12),
                _drawerItem(
                  context, 
                  Icons.swap_horiz_rounded, 
                  'Switch to Customer Mode', 
                  -1, 
                  onTap: () => AppState.instance.setPOV(UserPOV.customer),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
            decoration: BoxDecoration(border: Border(top: BorderSide(color: ty.line2))),
            child: TyButton('Sign out', kind: TyButtonKind.ghost, full: true, onTap: () {}),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    final ty = context.ty;
    return Container(
      padding: EdgeInsets.fromLTRB(20, MediaQuery.of(context).padding.top + 20, 20, 24),
      decoration: BoxDecoration(
        color: ty.surface,
        border: Border(bottom: BorderSide(color: ty.line2)),
      ),
      child: Row(
        children: [
          Container(
            width: 54,
            height: 54,
            alignment: Alignment.center,
            decoration: BoxDecoration(color: ty.ink, shape: BoxShape.circle),
            child: const Icon(Icons.business_center_rounded, color: Colors.white, size: 24),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Frame Stories', style: TyType.sans(18, color: ty.ink, weight: FontWeight.w700)),
                Text('Vendor Partner', style: TyType.sans(12.5, color: ty.ink3)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _drawerItem(BuildContext context, IconData icon, String label, int targetIndex, {VoidCallback? onTap}) {
    final ty = context.ty;
    return ListTile(
      leading: Icon(icon, color: ty.ink2, size: 22),
      title: Text(label, style: TyType.sans(15, color: ty.ink, weight: FontWeight.w600)),
      contentPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 2),
      onTap: onTap ?? (() => onNavigate(targetIndex)),
    );
  }
}
