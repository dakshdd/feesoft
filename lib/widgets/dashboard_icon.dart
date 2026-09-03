import 'package:flutter/material.dart';

class DashboardIcon extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool circular;
  final double iconSize; // 👈 new property
  final VoidCallback onTap;

  const DashboardIcon({
    Key? key,
    required this.icon,
    required this.label,
    required this.onTap,
    this.circular = false,
    this.iconSize = 32, // 👈 default size
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(circular ? 50 : 8),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              shape: circular ? BoxShape.circle : BoxShape.rectangle,
              color: Colors.white,
              boxShadow: [
                BoxShadow(
                  color: Colors.black12,
                  blurRadius: 4,
                  offset: const Offset(2, 2),
                ),
              ],
            ),
            child: Icon(
              icon,
              size: iconSize, // 👈 use new property
              color: Colors.redAccent,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            label,
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 12, // 👈 smaller text for compact look
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}