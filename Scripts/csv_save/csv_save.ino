//Main Libraries
#include <TinyGPSPlus.h>
#include <HardwareSerial.h>
#include <SPI.h>
#include <SD.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <Preferences.h>

//Local Files
#include "serialcommands.h"
#include "root_ca.h"
#include "mountsdcard.h"
#include "CollectGPSData.h"
#include "wificonnections.h"

//variables/definitions
bool gpslog = false;
bool gpscollect = true;
unsigned long previousMillisgps = 0;
unsigned long intervalgps = 5000; // Delay in milliseconds for gps for 5 secounds
unsigned long previousMilliswifi = 0; //Start value set to ensure wifi checkin
unsigned long intervalwifi = 300000; // Delay in milliseconds for gps
bool recentupload = false;
Preferences preferences;
//const char* ssid = "TP-Link_C8BD";
//const char* password = "4LXPxQd8";
const char* serverName = "https://ynoor7m7xi.execute-api.ap-southeast-2.amazonaws.com/v1/esp32WriteToDynamodb";  // Replace with your API URL
#define SD_CS 5

// Create a GPS object
TinyGPSPlus gps;

void setup() {
  Serial.begin(115200); //ESP coms
  Serial2.begin(9600, SERIAL_8N1, 16, 17); //GPS coms
  setupencrypt(); //ensures encryption key valid or created
  MountSDCard(); //Sets up sd card 
  recentupload = false; //ensure checks for wifi and upload on startup
 }

void loop() {
  checkSerialCommands();//See if recieved any com commands

   //see how long since last upload
  if(millis() - previousMilliswifi >= intervalwifi){
    recentupload = false;
    previousMilliswifi = millis();
  }

  //see if should upload
  if (recentupload == false){
    if(ScanWifi(true)){
      wifiupload();
    }
  }

  if(gpscollect == true){
    // Check if it's time to perform the action that requires the delay
    if (millis() - previousMillisgps >= intervalgps) {
      previousMillisgps = millis(); // Store the current time
      CollectGPSData();//Save gps data to SD card
    }
  }  
}
