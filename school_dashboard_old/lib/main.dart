import 'package:flutter/material.dart';
import 'screens/dashboard_screen.dart';

void main() {
  runApp(SchoolDashboardApp());
}

class SchoolDashboardApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'School Dashboard',
      theme: ThemeData(primarySwatch: Colors.blue),
      home: DashboardScreen(),
    );
  }
}