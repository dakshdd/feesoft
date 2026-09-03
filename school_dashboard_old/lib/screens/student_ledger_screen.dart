import 'package:flutter/material.dart';

class StudentLedgerScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Student Ledger'),
      ),
      body: ListView(
        children: [
          ListTile(
            title: Text('Student Name'),
            subtitle: Text('Ledger details here'),
          ),
          ListTile(
            title: Text('Fee Status'),
            subtitle: Text('Paid / Pending'),
          ),
        ],
      ),
    );
  }
}