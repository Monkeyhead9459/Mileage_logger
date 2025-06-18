#include <WiFi.h>
#include <HTTPClient.h>

// Replace with your network credentials
const char* ssid = "TP-Link_C8BD";
const char* password = "4LXPxQd8";
const char* serverName = "https://ynoor7m7xi.execute-api.ap-southeast-2.amazonaws.com/v1/esp32WriteToDynamodb";  // Replace with your API URL


void setup() {
  Serial.begin(115200);

  Serial.println("Starting WiFi scan...");

  // Set WiFi to station mode (not access point)
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();  // Disconnect from any current connection

  delay(100);

  int n = WiFi.scanNetworks();  // Perform network scan
  Serial.println("Scan complete.");
  
  if (n == 0) {
    Serial.println("No networks found.");
  } else {
    Serial.println();
    Serial.print(n);
    Serial.println(" networks found:");
    for (int i = 0; i < n; ++i) {
      // Print SSID, RSSI (signal strength), and encryption type
      Serial.print(i + 1);
      Serial.print(": ");
      Serial.print(WiFi.SSID(i));
      Serial.print(" (");
      Serial.print(WiFi.RSSI(i));
      Serial.print(" dBm) ");
      Serial.println((WiFi.encryptionType(i) == WIFI_AUTH_OPEN) ? "[OPEN]" : "[SECURED]");
      delay(10);
    }
  }

  // Start Wi-Fi
  Serial.println("Connecting to WiFi...");
  WiFi.begin(ssid, password);

    // Wait for connection
    while (WiFi.status() != WL_CONNECTED) {
      delay(500);
      Serial.print(".");
    }

  Serial.println();
  Serial.println("Connected to WiFi!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());


  String jsonData = "{\"dev_esp32\":\"esp32_device_001\",\"timestamp\":\"2024-06-05T12:00:00Z\",\"latitude\":-43.5,\"longitude\":172.6}";

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverName);
    http.addHeader("Content-Type", "application/json");

    int httpResponseCode = http.POST(jsonData);
    String response = http.getString();

    Serial.print("Response Code: ");
    Serial.println(httpResponseCode);
    Serial.println("Response: " + response);

    http.end();
  }


}

void loop() {
  // Your loop code here (e.g., sending data, etc.)
}

