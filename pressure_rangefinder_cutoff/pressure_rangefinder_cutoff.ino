#include <ArduinoJson.h>

const int BAUD_RATE = 9600;

//range finder
const int pwPin = 7;
double pulse, inches, cm;
long time;

//pressure sensor
int pressure = A0;
int pressvalue = 0;

//cutoff
int cutoffPin = A1;

void setup()
{
  Serial.begin(BAUD_RATE);
  analogReference(EXTERNAL);
  pinMode(cutoffPin, OUTPUT);
}

void loop()
{
  //range finder data collection
  pinMode(pwPin, INPUT);
  pulse = pulseIn(pwPin, HIGH);
  time = pulseIn(pwPin, HIGH);
  inches = pulse/147.0;
  cm = inches*2.54;

  Serial.print(inches);
  Serial.print("in, ");
  Serial.print(cm);
  Serial.print("cm, ");
  Serial.print("Time:");
  Serial.print(time);
  Serial.println();

  //collect pressure sensor values
  int rawPressureValue = analogRead(pressure);
  sendRawPressure(rawPressureValue);

  //send a signal to relay to trigger cutoff
  String raspberryPiInput = Serial.readString();
  if (raspberryPiInput.length() > 0) {
      StaticJsonBuffer<200> jsonBuffer;
      JsonObject& root = jsonBuffer.parseObject(raspberryPiInput);
      boolean shouldCut = root["altitudeReached"];
      if(shouldCut) {
        cutoff();
      }
  }
  
  delay(500);
}

void sendRawPressure(int rawPressure) {
  StaticJsonBuffer<200> jsonBuffer;
  JsonObject& root = jsonBuffer.createObject();
  root["raw_exterior_pressure"] = rawPressure;
  root.printTo(Serial);
}

void cutoff() {
  analogWrite(cutoffPin, 255);
}