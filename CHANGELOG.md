# Changelog

## 6.0.0 (2026-10-26)

The first release of Solar Illuminance, a fork of
[Illuminance](https://github.com/pnbruckner/ha-illuminance) 5.8.1.

### Renamed to Solar Illuminance

The integration is now Solar Illuminance, with the domain `solar_illuminance`,
so it can be installed alongside Illuminance. Sensors from Illuminance aren't
moved over: add them again in Solar Illuminance, then remove Illuminance.

### Illuminance and irradiance sensors, without modes

The mode option has been removed. Each entry now has two sensors, on a device
named after the entry: Illuminance, in lx, and Irradiance, in W/m², which is
disabled until you enable it. Both follow the sun's elevation, as normal mode
did.

- Simple mode has gone: its value only changed with the time of day and the
  weather. Automations written for it need new levels.
- Irradiance mode is now the irradiance sensor.
- The default name is now "Solar", giving "Solar Illuminance" and "Solar
  Irradiance". The sensors are named after the entry and their device class,
  so an entry named "Garden" has "Garden Illuminance" and "Garden
  Irradiance".

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

### Diagnostics

Each entry's diagnostics can be downloaded, to include when reporting a
problem. They have its options, how its value was worked out, and the
weather data source's state.

### Requires Home Assistant 2026.9

Solar Illuminance needs Home Assistant 2026.9 or newer, and works with the
latest releases. It uses probatio, which replaced voluptuous in Home Assistant
2026.9.
