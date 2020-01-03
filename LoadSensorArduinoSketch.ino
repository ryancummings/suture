/*
 Arduino sketch driving the suture load sensing hardware
 By: Ryan Cummings
 Based on Sparkfun Electronics sketch
 Date: Jan 02 2020
 License: This code is public domain but you buy me a beer if you use this and we meet someday (Beerware license).

 Arduino pin 2 -> HX711 CLK
 3 -> DOUT
 5V -> VCC
 GND -> GND

 Most any pin on the Arduino Uno will be compatible with DOUT/CLK.

 The HX711 board can be powered from 2.7V to 5V so the Arduino 5V power should be fine.
*/

#include "HX711.h"

#define DOUT  3
#define CLK  2

HX711 scale(DOUT, CLK);

float calibration_factor = -10000; //-7050 worked for my 440lb max scale setup

void setup() {
  Serial.begin(9600);
  scale.set_scale();
  scale.tare();	//Reset the scale to 0
  long zero_factor = scale.read_average(); //Get a baseline reading
}

void loop() {
  scale.set_scale(calibration_factor); //Adjust to this calibration factor
  Serial.println(scale.get_units(), 1);
}
