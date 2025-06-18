#ifndef WifiConnections_H
#define WifiConnections_H


void wifiupload();
bool ScanWifi(bool debug);
void dbconnecttest();
void wifisetup();
void wificonnect();
void wificlear();
String xorEncryptDecrypt(String data);
void setupencrypt();
void readSavedCredentials();

#endif