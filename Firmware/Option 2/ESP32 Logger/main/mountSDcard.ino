#include <mountsdcard.h>

void MountSDCard(){
  if (!SD.begin(SD_CS)) {
      Serial.println("SD card initialization failed!");
      return;
    }
  
  //NEED TO INCLUDE CHANGING CSV FILE NAME ONCE uploaded to DB
  if (!SD.exists("/gps_log.csv")) {
    File file = SD.open("/gps_log.csv", FILE_WRITE);
    if (file) {
        file.close();
    }
  }

  //Backup directory
  if (!SD.exists("/backup")) {
    SD.mkdir("/backup");
  }

  Serial.println("SD card ready.");
}


//include display of csv files
void printDirectory2(File dir, int numTabs) {
  while (true) {
    File entry = dir.openNextFile();
    if (!entry) {
      // No more files
      break;
    }

    for (uint8_t i = 0; i < numTabs; i++) {
      Serial.print('\t');
    }

    Serial.print(entry.name());
    if (entry.isDirectory()) {
      Serial.println("/");
      printDirectory2(entry, numTabs + 1);
    } else {
      Serial.print("\t\t");
      Serial.println(entry.size(), DEC);
    }

    entry.close();
  }
}

//Print csv file
void readFile(String filename){
  filename.trim(); // remove newline or extra spaces
  File file = SD.open("/" + filename);
  if (!file) {
      Serial.println("Failed to open file: " + filename);
    } else {
      Serial.println("Contents of " + filename + ":");
      while (file.available()) {
        String line = file.readStringUntil('\n');
        Serial.println(line);
      }
      file.close();
    }
}

//Remove file
void removeFile(String filename){
  filename.trim(); // remove newline or extra spaces
  if (SD.exists("/" + filename)) {
    if (SD.remove("/" + filename)) {
      Serial.println("Deleted file: " + filename);
    } else {
      Serial.println("Failed to delete file: " + filename);
    }
  } else {
    Serial.println("File does not exist: " + filename);
  }
}





