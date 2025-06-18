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