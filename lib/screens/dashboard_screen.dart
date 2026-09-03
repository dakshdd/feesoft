import 'package:flutter/material.dart';
import '../widgets/dashboard_icon.dart';
import 'fee_entry_screen.dart';
import 'homework_screen.dart';
import 'attendance_screen.dart';
import 'reportcard_screen.dart';
import 'notice_board_screen.dart';
import 'circular_screen.dart';
import 'chat_box_screen.dart';

/// Model class for dashboard items
class DashboardItem {
  final IconData icon;
  final String label;
  final Widget screen;

  DashboardItem({required this.icon, required this.label, required this.screen});
}

class DashboardScreen extends StatelessWidget {
  final Map<String, List<DashboardItem>> sections = {
    "Academics": [
      DashboardItem(icon: Icons.currency_rupee, label: 'Fees', screen: FeeEntryScreen()),
      DashboardItem(icon: Icons.laptop_chromebook, label: 'Homework', screen: HomeworkScreen()),
      DashboardItem(icon: Icons.people, label: 'Attendance', screen: AttendanceScreen()),
      DashboardItem(icon: Icons.description, label: 'Reportcard', screen: ReportcardScreen()),
    ],
    "Communication": [
      DashboardItem(icon: Icons.dashboard, label: 'Notice Board', screen: NoticeBoardScreen()),
      DashboardItem(icon: Icons.find_in_page, label: 'Circular', screen: CircularScreen()),
      DashboardItem(icon: Icons.chat, label: 'Chat Box', screen: ChatBoxScreen()),
    ],
    "About...": [
      DashboardItem(icon: Icons.upcoming, label: 'Coming Soon', screen: const Placeholder()),
    ],
  };

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: 200.0, // 👈 Banner height
            pinned: true,          // 👈 Title stays visible when collapsed
            flexibleSpace: FlexibleSpaceBar(
              centerTitle: true,
              title: Column(
                mainAxisSize: MainAxisSize.min,
                children: const [
                  Text(
                    "SHARDA INTERNATIONAL SCHOOL",
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                  Text(
                    "GURUGRAM",
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w500,
                      color: Colors.white70,
                    ),
                  ),
                ],
              ),
              background: Image.asset(
                "assets/images/sch.jpg", // 👈 school picture
                fit: BoxFit.cover,
              ),
            ),
          ),
          SliverList(
            delegate: SliverChildListDelegate([
              Container(
                decoration: BoxDecoration(
                  image: DecorationImage(
                    image: const AssetImage("assets/images/school.jpg"), // 👈 background image
                    fit: BoxFit.cover,
                    opacity: 0.8,
                  ),
                ),
                child: Column(
                  children: [
                    ListView(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      padding: const EdgeInsets.all(16),
                      children: sections.entries.map((entry) {
                        return buildSection(context, entry.key, entry.value);
                      }).toList(),
                    ),
                    // 👇 Transparent Company Ad GIF at bottom
                    Container(
                      padding: const EdgeInsets.all(8),
                      alignment: Alignment.center,
                      child: Opacity(
                        opacity: 0.6, // 👈 transparent effect
                        child: Image.asset(
                          "assets/images/dd.gif", // 👈 your GIF file
                          height: 60, // 👈 smaller size
                          fit: BoxFit.contain,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ]),
          ),
        ],
      ),
    );
  }

  /// Modular section builder with colored box
  Widget buildSection(BuildContext context, String title, List<DashboardItem> items) {
    Color boxColor;
    if (title == "Academics") {
      boxColor = Colors.grey.shade300;
    } else if (title == "Communication") {
      boxColor = Colors.blue.shade50;
    } else {
      boxColor = Colors.green.shade50;
    }

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: boxColor,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black12,
            blurRadius: 4,
            offset: const Offset(2, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: Colors.black87,
            ),
          ),
          const SizedBox(height: 10),
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3, // 👈 Always 3 icons per row
              childAspectRatio: 1.0,
            ),
            itemCount: items.length,
            itemBuilder: (context, index) {
              final item = items[index];
              return DashboardIcon(
                icon: item.icon,
                label: item.label,
                circular: true,
                iconSize: 28, // 👈 smaller icon size
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (context) => item.screen),
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}