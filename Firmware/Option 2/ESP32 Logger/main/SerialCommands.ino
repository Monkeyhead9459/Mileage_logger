#include <serialcommands.h>

//Serial Commands
void checkSerialCommands(){
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();  // Remove any whitespace or newline chars
    command.toLowerCase();
    Serial.println(command);
    Serial.print(">\n");

    if (command.equals("log stop")) {
      Serial.println("Stop Writing GPS to COMs");
      gpslog = false;
    } 
    else if (command.equals("log start")) {
      
      Serial.println("Start Writing GPS to COMs");
      gpslog=true;
    }
    else if (command.equals("sd mount")) {
      MountSDCard();
    }
    else if (command.equals("wifi scan")) {
      unsigned long testtimestart = millis();
      ScanWifi();
      unsigned long testtimeend = millis();
      Serial.print("Function took ");
      Serial.print(testtimeend - testtimestart);
      Serial.println(" ms to run.");

    }  
    else if (command.equals("print directory")) {
      File root = SD.open("/");
      printDirectory2(root, 0);
      root.close();
    } 
    else if (command.equals("read file")) {
      Serial.println("Enter full file name:");
      String userInput = "";
      // Wait until something is typed
      while (userInput.length() == 0) {
        delay(100);
        if (Serial.available()) {
          userInput = Serial.readStringUntil('\n');
          userInput.trim(); // Remove newline or extra spaces
        }
      }
      readFile(userInput);
    }   
    else if (command.equals("remove file")) {
      Serial.println("Enter full file name *TO DELETE*:");
      String userInput = "";
      // Wait until something is typed
      while (userInput.length() == 0) {
        delay(100);
        if (Serial.available()) {
          userInput = Serial.readStringUntil('\n');
          userInput.trim(); // Remove newline or extra spaces
        }
      }
      removeFile(userInput);
    }  
    else if (command.equals("gps stop")) {
      Serial.println("Stopping GPS Tracking");
      gpscollect = false;
    }
    else if (command.equals("gps start")) {
      Serial.println("Starting GPS Tracking");
      gpscollect = true;
    }
    else if (command.equals("db test")) {
      dbconnecttest();
    } 
    else if (command.equals("wifi setup")) {
      wifisetup();
    }  
    else if (command.equals("wifi connect")) {
      wificonnect();
    }  
    else if (command.equals("wifi clear")) {
      wificlear();
    } 
    else if (command.equals("wifi upload")) {
      wifiupload();
    } 
    else if (command.equals("debug flash")) {
      readSavedCredentials();
    }  
    else if (command.equals("manual mode off")) {
      manualmode = false; 
    } 
    else if (command.equals("manual mode on")) {
      manualmode = true; 
    }
    else if (command.equals("github check")) {
      void githubcheck(); 
    }
    else if (command.equals("debug on")) {
      debug = true; 
    }
    else if (command.equals("debug off")) {
      debug = false; 
    }
    else if (command.equals("fix check")) {
      void checkForNewData();
    }
    else if (command.equals("help")) {
      Serial.println("Available commands:");
      Serial.println("  log start / log stop");
      Serial.println("  gps start / gps stop");
      Serial.println("  wifi setup / wifi connect / wifi clear / wifi scan / wifi upload");
      Serial.println("  sd mount / print directory / read file / remove file");
      Serial.println("  db test");
      Serial.println("  manual mode on / manual mode off");
      Serial.println("  github check");
      Serial.println("  debug on / debug off");
      Serial.println("  fix check");
    }     
    else {
      Serial.print("Unknown command: ");
      Serial.println(command);
    }
  }
}

String readInput() {
  while (!Serial.available()) {
    delay(100);
  }
  String input = Serial.readStringUntil('\n');
  input.trim();  // Remove whitespace/newline
  return input;
}