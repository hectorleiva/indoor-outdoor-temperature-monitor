# Indoor/Outdoor Temperature Monitor

Written for the Adafruit Matrix Portal M4 using CircuitPython
https://www.adafruit.com/product/4745

It uses the BME680: https://www.adafruit.com/product/3660 for indoor temperature readings and https://openweathermap.org/ for outdoor temperature readings.

## Getting started

- Adafruit IO account https://io.adafruit.com/ to publish the readings to an IoT dashboard display
- `secrets.py` file that contains the following:
	```python
		ssid: # string of your wifi network
		password: # password to log into your wifi network
		latitude: # for OpenWeather
		longitude: # for OpenWeather
		timezone: # for OpenWeather
		sealevel: # for BME680 sensor
		openweather_token: # for OpenWeather
		openweather_units: # for OpenWeather and for determining how to display temperature info
		aio_username: # for Adafruit IO
		aio_key: # for Adafruit IO
	```
