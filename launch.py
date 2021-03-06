#python packages
from __future__ import division
import thread
import threading
import time
import json
import serial
import csv
import uuid
import math

#insert modules as needed
import sys
sys.path.insert(0, "/home/pi/Desktop/Balloonatics/Sensors/Temperature")
sys.path.insert(0, "/home/pi/Desktop/Balloonatics/Camera")


from camera import *
from temperature import *


#arduino links
BAUD_RATE = 9600

genericArduinoSerial = None
gpsSerial = None
pressureSerial = None

#file location
BASE_DIRECTORY = '/home/pi/Desktop/data/'

#filenames
GENERIC_ARDUINO_FILENAME = ''
GENERIC_ARDUINO_KEYS = ['time', 'geiger_cpm', 'anemometer_rpm']

GPS_ARDUINO_FILENAME = ''
GPS_ARDUINO_KEYS = ['time', 'gps_timestamp', 'lat', 'lat_direction', 
'lng', 'lng_direction', 'fix_quality', 'num_satelites','hdop', 'altitude', 'height_geoid_ellipsoid']

PRESSURE_ARDUINO_FILENAME = ''
PRESSURE_ARDUINO_KEYS = ['time', 'exterior_pressure', 'exterior_humidity', 'exterior_temperature', 'estimated_altitude', 'sound_time','blue_voltage', 'red_voltage', 'white_voltage']

GPIO_FILENAME = ''
GPIO_KEYS = getTemperatureKeys()


#pressure/cutdown
last_pressure_samples = []
NUM_PRESSURE_SAMPLES = 60
PRESSURE_THRESHOLD = 1560 #in Pa
has_cut_down = False

#time
start_time = None
TIME_THRESHOLD = 3600 #1 hour
CUTOFF_SIGNAL = 'c'


def operateCamera():
    while True:
        takeVideo();
        takePhoto();

def handleSerialInput(serial, responseFunction):
    while True:
        serialInput = str(serial.readline())
        if serialInput is not None and len(serialInput) > 0:
            responseFunction(serialInput)

def handleGenericArduinoSensor():
    def genericArduinioFunction(serialInput):
        try:
            serialInput = serialInput.replace('\r', '')
            serialInput = serialInput.replace('\n', '')
            dictionaryRepresentaion = json.loads(serialInput)
            addValueToCSV(GENERIC_ARDUINO_FILENAME, GENERIC_ARDUINO_KEYS, dictionaryRepresentaion)
        except:
            pass

    handleSerialInput(genericArduinoSerial, genericArduinioFunction)

def handleGPSData():
    def gpsHandler(string):
        if string.startswith('$GPGGA'):
            components = string.split(',')
            if len(components) >= 12:
                gps_timestamp = components[1]
                lat = components[2]
                directionLat = components[3]
                lng = components[4]
                directionLng = components[5]
                fix_quality = components[6]
                num_satelites = components[7]
                hdop = components[8]
                altitude = components[9]
                height_geoid_ellipsoid = components[11]
                dictionary = {'gps_timestamp': gps_timestamp, 
                        'lat' : lat, 
                        'lat_direction' : directionLat, 
                        'lng' : lng,
                        'lng_direction' : directionLng, 
                        'fix_quality' : fix_quality, 
                        'num_satelites' : num_satelites, 
                        'hdop' : hdop, 
                        'altitude' : altitude, 
                        'height_geoid_ellipsoid' : height_geoid_ellipsoid}
                addValueToCSV(GPS_ARDUINO_FILENAME, GPS_ARDUINO_KEYS, dictionary)

    handleSerialInput(gpsSerial, gpsHandler)



def handleRaspberryPiGPIO():
    while True:
        tempDictionary = getTemperatureReadingJSON()
        addValueToCSV(GPIO_FILENAME, GPIO_KEYS, tempDictionary)
        time.sleep(1)

def handlePressureSensor():
    def pressureFunction(serialInput):
        global last_pressure_samples
        try:
            global has_cut_down
            dictionaryRepresentaion = json.loads(serialInput)
            pressure = dictionaryRepresentaion['exterior_pressure'] 
            addValueToCSV(PRESSURE_ARDUINO_FILENAME, PRESSURE_ARDUINO_KEYS, dictionaryRepresentaion)
            if pressure is not None and pressure > 0 and has_cut_down == False:
                last_pressure_samples.append(pressure)
                length = len(last_pressure_samples)
                if length > NUM_PRESSURE_SAMPLES:
                    last_pressure_samples = last_pressure_samples[NUM_PRESSURE_SAMPLES-length:]
                    average = reduce(lambda x, y: x + y, last_pressure_samples) / length
                    if average < PRESSURE_THRESHOLD:
                        cutdown()
        except:
            pass

    handleSerialInput(pressureSerial, pressureFunction)


def cutdown():
    global has_cut_down
    current_time = time.time()
    if has_cut_down == False:
        if current_time - start_time > TIME_THRESHOLD:
            #send the signal a bunch of times. Safe > Sorry.
            has_cut_down = True
            for i in xrange(0,20):
                pressureSerial.write(CUTOFF_SIGNAL)
            filename =  BASE_DIRECTORY + 'cutdown' + str(uuid.uuid4()) + '.txt'
            with open(filename, 'w') as file:
                file.write('CUTDOWN AT: ' + str(time.time()))


#pressure in pascals        
def getAltitudeFromPressure(pressure):
    pressure /= 1000
    if pressure > 22.707:
        altitude = 44397.5-44388.3 * ((pressure/101.29) ** .19026)
    elif pressure < 2.483:
        altitude = 72441.47 * ((pressure/2.488) ** -.0878) - 47454.96
    else:
        altitude = 11019.12 - 6369.43 * math.log(pressure/22.65)
    return altitude

def addValueToCSV(filename, keys, dictionary):
    dictionary = filterCSVDictionary(keys, dictionary)
    
    with open(filename, 'a') as file:
        writer = csv.DictWriter(file, keys)
        writer.writerow(dictionary)

def filterCSVDictionary(keys, dictionary):
    filteredDictionary = {}
    for key in keys:
        if not key in dictionary:
            #add time if not already there
            if key == 'time':
                filteredDictionary[key] = time.time()
            else:
                filteredDictionary[key] = ''
        else:
            filteredDictionary[key]= dictionary[key]
    return filteredDictionary


def createCSVs():
    global BASE_DIRECTORY
    #create csv for geiger counter
    global GENERIC_ARDUINO_FILENAME
    GENERIC_ARDUINO_FILENAME = BASE_DIRECTORY + "arduino_one" + str(uuid.uuid4()) + ".csv"
    createCSV(GENERIC_ARDUINO_FILENAME, GENERIC_ARDUINO_KEYS)

    global GPS_ARDUINO_FILENAME
    GPS_ARDUINO_FILENAME = BASE_DIRECTORY + "gps" + str(uuid.uuid4()) + ".csv"
    createCSV(GPS_ARDUINO_FILENAME, GPS_ARDUINO_KEYS)

    global PRESSURE_ARDUINO_FILENAME
    PRESSURE_ARDUINO_FILENAME = BASE_DIRECTORY + "pressure" + str(uuid.uuid4()) + ".csv"
    createCSV(PRESSURE_ARDUINO_FILENAME, PRESSURE_ARDUINO_KEYS)

    global GPIO_FILENAME
    GPIO_FILENAME = BASE_DIRECTORY + 'gpio' + str(uuid.uuid4()) + '.csv'
    createCSV(GPIO_FILENAME, GPIO_KEYS)


def createCSV(filename, keys):
    with open(filename, 'wb') as file:
        dict_writer = csv.DictWriter(file, keys)
        dict_writer.writeheader()

def openSerial():
    global genericArduinoSerial
    global gpsSerial
    global pressureSerial
    
    while genericArduinoSerial == None:
        try:
            genericArduinoSerial = serial.Serial('/dev/ttyACM0', BAUD_RATE)
        except:
            genericArduinoSerial = None

    while gpsSerial == None:
        try:
            gpsSerial = serial.Serial('/dev/ttyACM1', BAUD_RATE)
        except:
            gpsSerial = None
    while pressureSerial == None:
        try:
            pressureSerial = serial.Serial('/dev/ttyACM2', BAUD_RATE)
        except:
            pressureSerial = None

def main():
    openSerial();
    global start_time
    start_time = time.time()
    createCSVs()
    thread.start_new_thread(operateCamera, ())
    thread.start_new_thread(handleGenericArduinoSensor, ())
    thread.start_new_thread(handleGPSData, ())
    thread.start_new_thread(handlePressureSensor, ())
    #something needs to occupy the main thread
    handleRaspberryPiGPIO()
    
   
    
    


main()
