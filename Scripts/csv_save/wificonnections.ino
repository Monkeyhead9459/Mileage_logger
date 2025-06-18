#include <wificonnections.h>

//Upload csv to database
void wifiupload(){
  wificonnect();
  Serial.println("Attempting Upload to Cloud");

  File file = SD.open("/gps_log.csv");
  if (!file) {
    Serial.println(" Failed to open file may be up to date.");
    recentupload = true;
    return;
  }

  WiFiClientSecure client;
  client.setCACert(rootCACert);  // Use AWS root CA
  HTTPClient http;

  String batchJson = "[";
  String failedLines = "";
  int batchCount = 0;

  while (file.available()) {
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("WiFi lost during upload. Aborting.");
      failedLines += file.readString();  // Save rest
      break;
    }

    String line = file.readStringUntil('\n');
    line.trim();
    if (line == "") continue;

    // Parse CSV line: date,time,lat,lon,alt
    int idx1 = line.indexOf(',');
    int idx2 = line.indexOf(',', idx1 + 1);
    int idx3 = line.indexOf(',', idx2 + 1);
    int idx4 = line.indexOf(',', idx3 + 1);

    if (idx1 < 0 || idx2 < 0 || idx3 < 0 || idx4 < 0) {
      Serial.println("Malformed line skipped: " + line);
      continue;
    }

    String date = line.substring(0, idx1);
    String time = line.substring(idx1 + 1, idx2);
    String lat = line.substring(idx2 + 1, idx3);
    String lon = line.substring(idx3 + 1, idx4);
    String alt = line.substring(idx4 + 1);

    String jsonItem = "{\"dev_esp32\":\"esp32_device_001\",\"date\":\"" + date +
                      "\",\"time\":\"" + time + "\",\"latitude\":" + lat +
                      ",\"longitude\":" + lon + ",\"altitude\":" + alt + "}";

    if (batchCount > 0) batchJson += ",";
    batchJson += jsonItem;
    batchCount++;

    if (batchCount == 25 || file.available() == 0) {
      batchJson += "]";

      http.begin(client, serverName);
      http.addHeader("Content-Type", "application/json");

      int httpCode = http.POST(batchJson);
      String response = http.getString();
      http.end();

      if (httpCode == 200) {
        Serial.printf("Batch of %d items uploaded successfully.\n", batchCount);
        Serial.println(response);

        // Write successfully sent lines to dated backup
        for (int i = 0; i < batchCount; ++i) {
          String backupFile = "/backup/" + date + ".csv";
          File bkp = SD.open(backupFile, FILE_APPEND);
          if (bkp) {
            bkp.println(line);
            bkp.close();
          }
        }

      } else {
        Serial.printf("Batch upload failed! Code: %d\n", httpCode);
        failedLines += batchJson;  // optional fallback
      }

      batchJson = "[";  // Reset batch
      batchCount = 0;
      delay(1000);  // throttle AWS calls
    }
  }

  file.close();

  // Overwrite GPS log with failed lines (if any)
  SD.remove("/gps_log.csv");
  if (failedLines.length() > 0) {
    File out = SD.open("/gps_log.csv", FILE_WRITE);
    out.print(failedLines);
    out.close();
    Serial.println("Rewritten file with failed uploads.");
  } else {
    Serial.println("All available data uploaded and cleared.");
    recentupload = true;
  }
}  

void wificonnect(){
  // Set WiFi to station mode (not access point)
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();  // Disconnect from any current connection

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("Already connected to WiFi.");
  return;
  }

  //Try loading
  preferences.begin("wifi-creds", true); //access flash
  String ssidEncrypted = preferences.getString("ssid", "");
  String passwordEncrypted = preferences.getString("password", "");
  preferences.end();
  String ssid = xorEncryptDecrypt(ssidEncrypted);
  String password = xorEncryptDecrypt(passwordEncrypted);

  if (ssid == "" || password == "") {
    Serial.println("No saved WiFi credentials.");
    preferences.end();
    return;
  }

 // Connect to WiFi
  Serial.printf("Connecting to %s", ssid.c_str());
  WiFi.begin(ssid.c_str(), password.c_str());

  int timeout = 0;
  while (WiFi.status() != WL_CONNECTED && timeout < 20) {
    delay(500);
    Serial.print(".");
    timeout++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nWiFi failed to connect to saved credentials.");
  }
}

void wificlear(){
  preferences.begin("wifi-creds", false); //access flash
  preferences.clear();
  Serial.println("Credentials cleared. Rebooting...");
  ESP.restart();
}


//Manually Setup Wifi Over COMs
void wifisetup(){
  

  // Try loading saved credentials
  preferences.begin("wifi-creds", false);
  String ssidEncrypted = preferences.getString("ssid", "");
  String passwordEncrypted = preferences.getString("password", "");
  preferences.end();
  String ssid = xorEncryptDecrypt(ssidEncrypted);
  String password = xorEncryptDecrypt(passwordEncrypted);

  if (ssid == "" || password == "") {
    Serial.println("No saved WiFi credentials. Please enter them:");

    Serial.print("Enter SSID: ");
    ssid = readInput();
    Serial.print("Enter Password: ");
    password = readInput();

    Serial.println("Attempting to connect...");

    // Set WiFi to station mode (not access point)
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();  // Disconnect from any current connection
    delay(100);
    WiFi.begin(ssid.c_str(), password.c_str());
    delay(100);

    int tries = 0;
    while (WiFi.status() != WL_CONNECTED && tries < 20) {
      delay(500);
      Serial.print(".");
      tries++;
    }

    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("\n Connected!");
      Serial.println(WiFi.localIP());

      //  Save and encrypt only after successful connection
      preferences.end();  // close read session
      preferences.begin("wifi-creds", false);  // open for write

      ssidEncrypted = xorEncryptDecrypt(ssid);
      passwordEncrypted = xorEncryptDecrypt(password);
      preferences.end();
      preferences.begin("wifi-creds", false);  // Reopen for write
      preferences.putString("ssid", ssidEncrypted);
      preferences.putString("password", passwordEncrypted);
      Serial.println("Credentials saved to flash.");
      preferences.end();
    } else {
      Serial.println("\n Failed to connect. Credentials NOT saved.");
      preferences.end();
    }  
  } else {
    preferences.end();
    wificonnect();
  }
}

//Scan Wifi Networks
bool ScanWifi(bool debug){
  bool mywififound =false;
  // Load saved SSID from flash
   preferences.begin("wifi-creds", false);
  String ssidEncrypted = preferences.getString("ssid", "");
  String passwordEncrypted = preferences.getString("password", "");
  preferences.end();
  String ssid = xorEncryptDecrypt(ssidEncrypted);
  String password = xorEncryptDecrypt(passwordEncrypted);


  if(debug){
    Serial.println("Starting WiFi scan...");
  }
  // Set WiFi to station mode (not access point)
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();  // Disconnect from any current connection
 
  delay(500);
  int n = WiFi.scanNetworks();  // Perform network scan
  if(debug){
    Serial.println("Scan complete.");
  }

  if (n == -2) {
  if(debug){
    Serial.println("WiFi scan failed.");
  }    
    return false;
  }
  else if (n == 0) {
    if(debug){
      Serial.println("No networks found.");
    }
  } 
  else {
    if(debug){
      Serial.println();
      Serial.print(n);
      Serial.println(" networks found:");
    }
    for (int i = 0; i < n; ++i) {
      // Print SSID, RSSI (signal strength), and encryption type
      String scannedSSID = WiFi.SSID(i);
      if(debug){
        Serial.print(i + 1);
        Serial.print(": ");
        Serial.print(WiFi.SSID(i));
        Serial.print(" (");
        Serial.print(WiFi.RSSI(i));
        Serial.print(" dBm) ");
        Serial.println((WiFi.encryptionType(i) == WIFI_AUTH_OPEN) ? "[OPEN]" : "[SECURED]");
        delay(10);
      }

      if (scannedSSID == ssid) {
        mywififound = true;
      }
    }
    if (ssid != "") {
      if (mywififound) {
        Serial.println("Saved WiFi network \"" + ssid + "\" is in range.");
        return true;
      } else {
        if(debug){
          Serial.println("Saved WiFi network \"" + ssid + "\" not found.");
        }
      }
    } else {
      if(debug){
         Serial.println("No saved WiFi credentials found in flash.");
      }
    }
    return mywififound;
  }
}

void dbconnecttest(){
  ScanWifi(true);
  wificonnect();
  
  String jsonData = "{\"dev_esp32\":\"esp32_device_001\",\"date\":\"2031-06-05\",\"time\":\"12:00:00\",\"latitude\":-43.5,\"longitude\":172.6,\"altitude\":22.6}";
  
  if (WiFi.status() == WL_CONNECTED) {
    WiFiClientSecure client;
    client.setCACert(rootCACert);

    HTTPClient http;
    http.begin(serverName);
    http.addHeader("Content-Type", "application/json");

    int httpResponseCode = http.POST(jsonData);
    String response = http.getString();

    if (httpResponseCode > 0) {
      Serial.println("Data sent successfully.");
    } else {
      Serial.print("Error on sending POST: ");
       Serial.println(http.errorToString(httpResponseCode));
    }

    Serial.print("Response Code: ");
    Serial.println(httpResponseCode);
    Serial.println("Response: " + response);

    http.end();
  }

}

String xorEncryptDecrypt(String data) {
  preferences.end(); //Ensure is closed
  preferences.begin("crypto", true);
  String key = preferences.getString("xor_key", "");
  
  preferences.end();
  if (key == "") {
    Serial.println("No encryption key found.");
    return "";  // Fail-safe: return empty string or original
  }

  String result = "";
  for (int i = 0; i < data.length(); i++) {
    result += char(data[i] ^ key[i % key.length()]);
  }
  return result;
}

void setupencrypt(){
  preferences.end();//ensure is closed
  //Encryption key
  preferences.begin("crypto", false);
  String checkkey = preferences.getString("xor_key", "");
  if(checkkey == ""){
    String generatedKey = String(random(100000, 999999));
    preferences.putString("xor_key", generatedKey);
    Serial.println("Encryption Key generated");
  }
  else{
    Serial.println("Encryption Key Exists");
  }
  preferences.end();
}

void readSavedCredentials() {
  preferences.begin("wifi-creds", true);  // read-only

  String ssidEncrypted = preferences.getString("ssid", "");
  String passwordEncrypted = preferences.getString("password", "");

  preferences.end();
  preferences.begin("crypto", true);  // read encryption key
  String xorKey = preferences.getString("xor_key", "");
  preferences.end();

  String ssidDecrypted = xorEncryptDecrypt(ssidEncrypted);
  String passwordDecrypted = xorEncryptDecrypt(passwordEncrypted);

  Serial.println("Encrypted SSID: " + ssidEncrypted);
  Serial.println("Decrypted SSID: " + ssidDecrypted);
  Serial.println("Encrypted Password: " + passwordEncrypted);
  Serial.println("Decrypted Password: " + passwordDecrypted);
  Serial.println("XOR Encryption Key: " + xorKey);
}

