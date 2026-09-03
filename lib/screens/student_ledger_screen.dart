import 'package:flutter/material.dart';
import '../services/receipt_service.dart';

class StudentLedgerScreen extends StatelessWidget {
  final ReceiptService receiptService = ReceiptService();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Student Ledger")),
      body: ListView.builder(
        itemCount: 10, // Example data
        itemBuilder: (context, index) {
          return ListTile(
            title: Text("Student $index"),
            subtitle: Text("Ledger details..."),
            trailing: IconButton(
              icon: Icon(Icons.print),
              onPressed: () {
                receiptService.printReceipt("Student $index");
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text("Printing receipt for Student $index"),
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}
