//Digital pin 7 for reading in the pulse width from the MaxSonar device.
//This variable is a constant because the pin will not change throughout execution of this code.
const int pwPin = 7;
//variables needed to store values
double pulse, inches, cm;
long time;

void setup()
{
  //This opens up a serial connection to shoot the results back to the PC console
  Serial.begin(9600);
  //currentTime = millis();
}

void loop()
{
  pinMode(pwPin, INPUT);
  //Used to read in the pulse that is being sent by the MaxSonar device.
  //Pulse Width representation with a scale factor of 147 uS per Inch.
  pulse = pulseIn(pwPin, HIGH);

  time = pulseIn(pwPin, HIGH);
  //147uS per inch
  inches = pulse/147.0;
  //change inches to centimetres
  cm = inches*2.54;

  Serial.print(inches);
  Serial.print("in, ");
  Serial.print(cm);
  Serial.print("cm, ");
  Serial.print("Time:");
  Serial.print(time);
  Serial.println();
  
  delay(500);
}
