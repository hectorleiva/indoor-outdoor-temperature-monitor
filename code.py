#!/usr/bin/env python3
# Get temperature from sensor and temperature from OpenWeather and display it on the MatrixPortal

import board
import terminalio
import time
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

    # To determine time using the Adafruit Time Service
    TIMEZONE = secrets['timezone']
    AIO_USERNAME = secrets['aio_username']
    AIO_KEY = secrets['aio_key']
except ImportError:
    print("WiFi secrets, Openweather API Tokens, and Latitude/Longitude values are kept in secrets.py, please add them!")
    raise

# --- Display setup ---
matrixportal = MatrixPortal(
    status_neopixel=board.NEOPIXEL,
    bit_depth=4
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
    return str(int(temperature))

def callWeatherAPI(token, lat, lng, units, last_weather_value):
    DATA_SOURCE = 'https://api.openweathermap.org/data/2.5/onecall?units={}&lat={}&lon={}&appid={}&exclude=minutely,hourly,daily,alerts'.format(
        units,
        lat,
        lng,
        token
    )

    print(DATA_SOURCE)
    try:
        current_value = matrixportal.network.fetch_data(DATA_SOURCE, json_path=['current'])
        return current_value[0] # this returns the weather data as an object
    except Exception as e:
        print("There was an issue trying to get the last weather API value")
        print(e);
    
    return last_weather_value

def callTimeService():
    TIME_URL = "https://io.adafruit.com/api/v2/%s/integrations/time/strftime?x-aio-key=%s" % (AIO_USERNAME, AIO_KEY)
    # See https://apidock.com/ruby/DateTime/strftime for full options
    TIME_URL += "&fmt=%25s" # return date time data in UNIX timestamp
    response = matrixportal.network.fetch_data(TIME_URL)
    return int(response)

def determineColorsForDisplay(weather_data, indoor_temp: str, units: str, unix_timestamp: int):
    outdoor_temp = int(weather_data['temp'])
    indoor_temp = int(indoor_temp)

    SHOULD_DIM_DISPLAY = unix_timestamp > weather_data['sunset'] or unix_timestamp < weather_data['sunrise']

    if (SHOULD_DIM_DISPLAY):
        HOT_COLOR = '#150201'        # 9 shades darker than 'd41c0f'
        NEUTRAL_COLOR = '#191919'    # 9 shades darker than 'ffffff'
        COLD_COLOR = '#000719'       # 9 shades darker than '034eff'
    else:
        HOT_COLOR = '#d41c0f'
        NEUTRAL_COLOR = '#ffffff'
        COLD_COLOR = '#034eff'

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
            if indoor_temp > 83:
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


def writeTemperatureValuesToDisplay(outdoor_temp: str, indoor_temp: str):
    matrixportal.set_text(indoor_temp, 4)
    matrixportal.set_text(outdoor_temp, 5)

# Global Values
outdoor_temp_object = {}
indoor_temp = ''
NEXT_OUTDOOR_TEMP_SYNC = 0
UNIX_TIMESTAMP_FROM_TIME_SERVICE = 0

# Set-up Indoor Temperature Sensor
i2c = I2C(board.SCL, board.SDA)
bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c)
bme680.sea_level_pressure = SEALEVEL

# Initialized values
writeTemperatureValuesToDisplay('la', 'Ho') # ??Hola, como estas?

while True:
    NOW = time.time() # Current epoch time in seconds, UTC

    if NOW > NEXT_OUTDOOR_TEMP_SYNC:
        NEXT_OUTDOOR_TEMP_SYNC = NOW + (60 * 60) # Network call every hour
        UNIX_TIMESTAMP_FROM_TIME_SERVICE = callTimeService()
        outdoor_temp_object = callWeatherAPI(OPENWEATHER_TOKEN, LATITUDE, LONGITUDE, OPENWEATHER_UNITS, outdoor_temp_object)

    indoor_temp = sensor_data_stringified(bme680, OPENWEATHER_UNITS)

    writeTemperatureValuesToDisplay(str(int(outdoor_temp_object['temp'])), indoor_temp)

    determineColorsForDisplay(outdoor_temp_object, indoor_temp, OPENWEATHER_UNITS, UNIX_TIMESTAMP_FROM_TIME_SERVICE)

    time.sleep(20) # wait 20 seconds