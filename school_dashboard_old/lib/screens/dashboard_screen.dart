import 'package:flutter/material.dart';
import '../widgets/dashboard_icon.dart';
import 'fee_entry_screen.dart';
import 'homework_screen.dart';
import 'attendance_screen.dart';
import 'reportcard_screen.dart';
import 'notice_board_screen.dart';
import 'circular_screen.dart';
import 'chat_box_screen.dart';

class DashboardScreen extends StatelessWidget {
  final Map<String, List<Map<String, dynamic>>> sections = {
    "Academics": [
      {
        'icon': Icons.currency_rupee,
        'label': 'Fees',
        'screen': FeeEntryScreen(),
      },
      {
        'icon': Icons.laptop_chromebook,
        'label': 'Homework',
        'screen': HomeworkScreen(),
      },
      {
        'icon': Icons.people,
        'label': 'Attendance',
        'screen': AttendanceScreen(),
      },
      {
        'icon': Icons.description,
        'label': 'Reportcard',
        'screen': ReportcardScreen(),
      },
    ],
    "Communication": [
      {
        'icon': Icons.dashboard,
        'label': 'Notice Board',
        'screen': NoticeBoardScreen(),
      },
      {
        'icon': Icons.find_in_page,
        'label': 'Circular',
        'screen': CircularScreen(),
      },
      {
        'icon': Icons.chat,
        'label': 'Chat Box',
        'screen': ChatBoxScreen(),
      },
    ],
    "Misc": [
      // Future features can be added here
    ],
  };

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("School Dashboard")),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: sections.entries.map((entry) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                entry.key,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 10),
              GridView.count(
                crossAxisCount: 2,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                childAspectRatio: 1.2,
                children: entry.value.map((item) {
                  return DashboardIcon(
                    icon: item['icon'],
                    label: item['label'],
                    onTap: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => item['screen'],
                        ),
                      );
                    },
                  );
                }).toList(),
              ),
              const SizedBox(height: 20),
            ],
          );
        }).toList(),
      ),
    );
  }
}