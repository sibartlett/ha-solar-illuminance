# Changelog

## 6.0.0 (2026-10-26)

The first release of Solar Illuminance, a fork of
[Illuminance](https://github.com/pnbruckner/ha-illuminance) 5.8.1.

### Renamed to Solar Illuminance

The integration is now Solar Illuminance, with the domain `solar_illuminance`,
so it can be installed alongside Illuminance. Sensors from Illuminance aren't
moved over: add them again in Solar Illuminance, then remove Illuminance.

### Set up in the UI only

YAML configuration is no longer supported, and the `reload` action has been
removed. If your configuration still has a `solar_illuminance:` section, Home
Assistant shows a repair asking you to remove it. Add the sensors in the UI
instead: see [Configuration](README.md#configuration).

### Uses the weather's cloud coverage

If the weather entity reports its cloud coverage, as Met.no, OpenWeatherMap
and AccuWeather do, the sensor now uses it as well as the weather condition.
It's more precise: the conditions map to only a few levels of brightness, so
the value jumped between them. The condition still counts when it's darker,
as in fog, rain or storms, so for any condition the integration knows, the
value is never brighter than before. Other weather entities still use the
condition alone.

### Shows a value while Home Assistant starts

A sensor with a weather data source used to stay unknown until Home Assistant
had started, in case the source turned out to need special treatment. Weather
conditions are now recognised whatever their source, so until the weather is
available, the sensor shows the value without weather data, using the
illuminance divider.

### Repairs for the weather data source

If a sensor's weather data source no longer exists, for example because it was
deleted, Home Assistant now shows a repair. It also shows one if
the source has had no weather data for an hour. Until then, as before, the
sensor uses its illuminance divider instead of the weather.

Renaming the weather data source's entity ID no longer leaves the sensor
without it: the sensor follows the new ID.

### Weather data problems are logged once

An unexpected weather condition is now logged as a warning once, until it
changes or is fixed. It used to be logged as an error each time the weather
changed. A cloud coverage sensor whose state isn't a number is logged the
same way, as an unexpected condition.

### Simple mode follows a change of location

In simple mode, changing Home Assistant's location or time zone used to
leave the sensor using the old sunrise and sunset until the next day. It
now uses the new ones straight away.

### Diagnostics

Each sensor's diagnostics can be downloaded, to include when reporting a
problem. They have its options, how its value was worked out, and the
weather data source's state.

### Each sensor has a device

Each sensor now belongs to a device of its own, named after the sensor.
Renaming the sensor's entry renames both.

### Requires Home Assistant 2026.7

Solar Illuminance needs Home Assistant 2026.7 or newer, and works with the
latest releases.
