import 'package:flutter/material.dart';
import 'screens/home_screen.dart';

void main() {
  runApp(const AcademicBuddyApp());
}

class AcademicBuddyApp extends StatelessWidget {
  const AcademicBuddyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '学搭子',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF6C5CE7),
          brightness: Brightness.dark,
        ),
        scaffoldBackgroundColor: const Color(0xFF0F1117),
        cardColor: const Color(0xFF1A1D28),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFF0F1117),
          elevation: 0,
          centerTitle: true,
        ),
        useMaterial3: true,
      ),
      home: const HomeScreen(),
    );
  }
}
