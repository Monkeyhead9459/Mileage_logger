import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: BleHome(),
    );
  }
}

class BleHome extends StatefulWidget {
  @override
  State<BleHome> createState() => _BleHomeState();
}

class _BleHomeState extends State<BleHome> {
  final FlutterBluePlus flutterBlue = FlutterBluePlus.instance;
  BluetoothDevice? espDevice;
  BluetoothCharacteristic? espCharacteristic;

  String receivedData = "No data yet";

  void startScan() async {
    flutterBlue.startScan(timeout: const Duration(seconds: 4));

    flutterBlue.scanResults.listen((results) {
      for (var r in results) {
        if (r.device.name == "ESP32-BLE-Device") {
          espDevice = r.device;
          flutterBlue.stopScan();
          connectToDevice();
        }
      }
    });
  }

  void connectToDevice() async {
    if (espDevice == null) return;

    await espDevice!.connect();
    discoverServices();
  }

  void discoverServices() async {
    if (espDevice == null) return;

    List<BluetoothService> services = await espDevice!.discoverServices();
    for (var service in services) {
      for (var c in service.characteristics) {
        if (c.uuid.toString().toUpperCase().contains("ABCD")) {
          espCharacteristic = c;

          await espCharacteristic!.setNotifyValue(true);
          espCharacteristic!.value.listen((value) {
            setState(() {
              receivedData = utf8.decode(value);
            });
          });
        }
      }
    }
  }

  void sendToESP() async {
    if (espCharacteristic == null) return;

    await espCharacteristic!.write(utf8.encode("hello_from_flutter"));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("ESP32 BLE App")),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            ElevatedButton(
              onPressed: startScan,
              child: const Text("Scan & Connect"),
            ),
            const SizedBox(height: 20),
            Text(
              "Received from ESP32:\n$receivedData",
              style: const TextStyle(fontSize: 18),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 30),
            ElevatedButton(
              onPressed: sendToESP,
              child: const Text("Send to ESP32"),
            ),
          ],
        ),
      ),
    );
  }
}
