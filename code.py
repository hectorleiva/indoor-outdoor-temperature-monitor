#!/usr/bin/env python3
# Get temperature from sensor and temperature from OpenWeather and display it on the MatrixPortal

import time
import board
import terminalio
from adafruit_matrixportal.matrixportal import MatrixPortal

from busio import I2C
import adafruit_bme680

try:
    from secrets import secrets
    LATITUDE = secrets['latitude']
    LONGITUDE = secrets['longitude']
    SEALEVEL = secrets['sealevel']
    OPENWEATHER_TOKEN = secrets['openweather_token']
    OPENWEATHER_UNITS = secrets['openweather_units']
except ImportError:
    print("WiFi secrets, Openweather API Tokens, and Latitude/Longitude values are kept in secrets.py, please add them!")
    raise

# --- Display setup ---
matrixportal = MatrixPortal(
    status_neopixel=board.NEOPIXEL
)

# Create a static label
# "IN"
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(2, 4),
    text_scale=1
)

# "OUT"
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(35, 4),
    text_scale=1
)

# "F" for degrees for INDOORS
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(26, 16),
    text_scale=1
)

# "F" for degrees for OUTDOORS
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(59, 16),
    text_scale=1
)

# Dynamic labels
# Temperature INDOORS
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(2, 18),
    text_scale=2
)

# Temperature OUTDOORS
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(35, 18),
    text_scale=2
)

matrixportal.set_text("IN", 0)
matrixportal.set_text("OUT", 1)
matrixportal.set_text("F" if OPENWEATHER_UNITS is "imperial" else "C", 2)
matrixportal.set_text("F" if OPENWEATHER_UNITS is "imperial" else "C", 3)


def sensor_data_stringified(bme680, units):
    if units is "imperial":
        temperature = "%0.0f" % ((bme680.temperature * 1.8) + 32)
    else:
        temperature = "%0.0f" % bme680.temperature

    # pressure = "%0.1fhPa" % bme680.pressure
    # gas = "{}%".format(bme680.gas)
    return str(temperature)

def callWeatherAPI(token, lat, lng, units, last_weather_value):
    DATA_SOURCE = 'https://api.openweathermap.org/data/2.5/onecall?units={}&lat={}&lon={}&appid={}&exclude=minutely,hourly,daily,alerts'.format(
        units,
        lat,
        lng,
        token
    )

    print(DATA_SOURCE)
    try:
        current_value = matrixportal.network.fetch_data(DATA_SOURCE, json_path=['current', 'temp'])
        return parseForTemperature(current_value)
    except Exception as e:
        print("There was an issue trying to get the last weather API value")
        print(e);
    
    return last_weather_value

def parseForTemperature(weatherData):
    return int(weatherData[0])

def logDataToAdafruitIO(outdoor_temp, indoor_temp):
    try:
        matrixportal.push_to_io("outdoor-temp", outdoor_temp)
        matrixportal.push_to_io("indoor-temp-sensor", indoor_temp)
    except:
        print('there was an error with the matrixportal push_to_io')

def determineColorsForDisplay(outdoor_temp, indoor_temp, units):
    if not (isinstance(outdoor_temp, int) or isinstance(outdoor_temp, float)) or not (isinstance(indoor_temp, int) or isinstance(indoor_temp, float)):
        return

    HOT_COLOR = 'd41c0f'
    NEUTRAL_COLOR = 'ffffff'
    COLD_COLOR = '034eff'

    outdoor_display_assignments = [1,3,5]
    indoor_display_assignments = [0,2,4]

    if units is "imperial":
        for i in outdoor_display_assignments:
            if outdoor_temp > 89:
                matrixportal.set_text_color(HOT_COLOR, i)
            elif outdoor_temp < 35:
                matrixportal.set_text_color(COLD_COLOR, i)
            else:
                matrixportal.set_text_color(NEUTRAL_COLOR, i)
        for i in indoor_display_assignments:
            if indoor_temp > 80:
                matrixportal.set_text_color(HOT_COLOR, i)
            elif indoor_temp < 50:
                matrixportal.set_text_color(COLD_COLOR, i)
            else:
                matrixportal.set_text_color(NEUTRAL_COLOR, i)
    else:
        for i in outdoor_display_assignments:
            if outdoor_temp > 31:
                matrixportal.set_text_color(HOT_COLOR, i)
            elif outdoor_temp < 2:
                matrixportal.set_text_color(COLD_COLOR, i)
            else:
                matrixportal.set_text_color(NEUTRAL_COLOR, i)
        for i in indoor_display_assignments:
            if indoor_temp > 26:
                matrixportal.set_text_color(HOT_COLOR, i)
            elif indoor_temp < -2:
                matrixportal.set_text_color(COLD_COLOR, i)
            else:
                matrixportal.set_text_color(NEUTRAL_COLOR, i)


def writeTemperatureValuesToDisplay(outdoor_temp, indoor_temp):
    matrixportal.set_text(indoor_temp, 4)
    matrixportal.set_text(outdoor_temp, 5)

# Global Values
outdoor_temp = '??'
indoor_temp = '??'
NEXT_OUTDOOR_TEMP_SYNC = 0
NEXT_ADAFRUIT_IO_SYNC = 0

# Set-up Indoor Temperature Sensor
i2c = I2C(board.SCL, board.SDA)
bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c)
bme680.sea_level_pressure = SEALEVEL

while True:
    NOW = time.time() # Current epoch time in seconds, UTC

    # Immediately write the values out to the display
    writeTemperatureValuesToDisplay(outdoor_temp, indoor_temp)

    if NOW > NEXT_OUTDOOR_TEMP_SYNC:
        NEXT_OUTDOOR_TEMP_SYNC = NOW + (60 * 60) # Network call every hour
        outdoor_temp = callWeatherAPI(OPENWEATHER_TOKEN, LATITUDE, LONGITUDE, OPENWEATHER_UNITS, outdoor_temp)

    indoor_temp = sensor_data_stringified(bme680, OPENWEATHER_UNITS)

    writeTemperatureValuesToDisplay(outdoor_temp, indoor_temp)

    determineColorsForDisplay(int(outdoor_temp), int(indoor_temp), OPENWEATHER_UNITS)

    # if NOW > NEXT_ADAFRUIT_IO_SYNC:
    #     NEXT_ADAFRUIT_IO_SYNC = NOW + (60 * 5) # Network call every 5 minutes
    #     logDataToAdafruitIO(outdoor_temp, indoor_temp)

    time.sleep(10) # wait 10 seconds