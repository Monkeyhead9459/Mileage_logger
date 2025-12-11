#include <CollectGPSData.h>

void CollectGPSData(){
  while (Serial2.available()) {
      gps.encode(Serial2.read());
    }

    if (gps.date.isValid() && gps.time.isValid() && gps.location.isUpdated() && gps.location.isValid()) {
      File file = SD.open("/gps_log.csv", FILE_APPEND);
      if (file) {
        char date[11];   // YYYY-MM-DD
        char time[9];    // HH:MM:SS
        float latitude = gps.location.lat();
        float longitude =gps.location.lng();
        float altitude = gps.altitude.meters();


        sprintf(date, "%04d-%02d-%02d", gps.date.year(), gps.date.month(), gps.date.day());
        sprintf(time, "%02d:%02d:%02d", gps.time.hour(), gps.time.minute(), gps.time.second());

        file.printf("%s,%s,%.6f,%.6f,%.2f\n", date, time,
                    latitude, longitude, altitude);

        file.close();
        if (gpslog ==true){
          Serial.printf("Logged: %s, %s, Lat: %.6f, Lon: %.6f, Alt: %.2f\n",date, time, latitude, longitude, altitude);
          
        }
      } else {
        Serial.println("Failed to open file on SD.");
      }
    }

}

void checkForNewData() {
  String currentLastLine = getLastLine("/gps_log.csv");

  if (currentLastLine != lastSeenLine && currentLastLine != "") {
    Serial.println("Confirmed new GPS logs:");
    if(debug){
      Serial.println("Previous Check " +lastSeenLine);
      Serial.println("Last Line Logged " +currentLastLine);
    }
    
    lastSeenLine = currentLastLine;  // Update the stored line
    
  }else {
    Serial.println("No new GPS logs since last check rebooting.");
    if(debug==false){
     ESP.restart();
    }
    else{
      Serial.println("Debug mode on not rebooting.");
    }
  }
}

String getLastLine(const char* path) {
  File file = SD.open(path);
  if (!file) {
    Serial.println("Failed to open file");
    return "";
  }

  String lastLine = "";
  while (file.available()) {
    String line = file.readStringUntil('\n');
    if (line.length() > 0) {
      lastLine = line;
    }
  }

  file.close();
  return lastLine;
}