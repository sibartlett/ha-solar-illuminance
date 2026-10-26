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

### Each sensor has a device

Each sensor now belongs to a device of its own, named after the sensor.
Renaming the sensor's entry renames both.

### Requires Home Assistant 2026.7

Solar Illuminance needs Home Assistant 2026.7 or newer, and works with the
latest releases.
