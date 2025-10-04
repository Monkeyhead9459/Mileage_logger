//Main Libraries
#include <TinyGPSPlus.h>
#include <HardwareSerial.h>
#include <SPI.h>
#include <SD.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <Preferences.h>
#include <Update.h>
#include <ArduinoJson.h>

//Local Files
#include "serialcommands.h"
#include "root_ca.h"
#include "mountsdcard.h"
#include "CollectGPSData.h"
#include "wificonnections.h"

//variables/definitions
bool gpslog = false;
bool gpscollect = true;
bool manualmode = false; 
unsigned long previousMillisgps = 0;
unsigned long intervalgps = 5000; // Delay in milliseconds for gps for 5 secounds
unsigned long previousMilliswifi = 0; //Start value set to ensure wifi checkin
unsigned long intervalwifi = 300000; // Delay in milliseconds for gps
unsigned long previousMillisfix = 0;// Start in milliseconds for previous fix for 1 minute
unsigned long intervalfix = 60000; // Delay in milliseconds for fix for 1 minute
bool recentupload = false;
bool debug= false;
String lastSeenLine = "";  // Global variable to track last known line
Preferences preferences;
#define CURRENT_VERSION "1.0.0"
const char* versionUrl = "https://raw.githubusercontent.com/Monkeyhead9459/Mileage_logger/main/Scripts/firmware/version.json";
const char* firmwareUrl = "https://raw.githubusercontent.com/Monkeyhead9459/Mileage_logger/main/Scripts/firmware/firmware.bin";
const char* serverName = "https://ynoor7m7xi.execute-api.ap-southeast-2.amazonaws.com/v1/esp32WriteToDynamodb";  // Replace with your API URL
#define SD_CS 5

// Create a GPS object
TinyGPSPlus gps;

void setup() {
  Serial.begin(115200); //ESP coms
  Serial2.begin(9600, SERIAL_8N1, 16, 17); //GPS coms
  Serial.println("*********Firmware Version: " CURRENT_VERSION "*********");
  setupencrypt(); //ensures encryption key valid or created
  MountSDCard(); //Sets up sd card 
  //Check OTA
  wificonnect();
  if(WiFi.status() == WL_CONNECTED){
    String latestFirmwareURL;
    if (checkForUpdate(latestFirmwareURL)) {
      performOTA(latestFirmwareURL.c_str());
    }
    wifiupload();
    recentupload = true; //ensure checks for wifi and upload on startup
  }
}

void loop() {
  checkSerialCommands();//See if recieved any com commands

  if(manualmode == false){
    //see how long since last upload
    if(millis() - previousMilliswifi >= intervalwifi){
      previousMilliswifi = millis();
      //see if should upload
      if (recentupload == false){
        if(WiFi.status() == WL_CONNECTED || ScanWifi()){
          wifiupload();
        }
      }
      else{
        recentupload = false;
      }
    }  
    //Check to see if gps is saving data
    if(millis() - previousMillisfix >= intervalfix){
      previousMillisfix = millis();
      checkForNewData();
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
