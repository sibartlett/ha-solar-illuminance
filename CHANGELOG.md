# Changelog

## 6.0.0 (2026-10-27)

The first release of Solar Illuminance, a fork of
[Illuminance](https://github.com/pnbruckner/ha-illuminance) 5.8.1. To move
your sensors over, see
[Moving from Illuminance](README.md#moving-from-illuminance).

### Differences from Illuminance

- **A new name.** The integration is Solar Illuminance, with the domain
  `solar_illuminance`, so it can be installed alongside Illuminance. It
  doesn't take over Illuminance's sensors: add them again.
- **Two sensors, without modes.** Each entry has an Illuminance sensor, in
  lx, and an Irradiance sensor, in W/m², which is disabled until you enable
  it. Both follow the sun's elevation, as normal mode did.
  - Simple mode has gone: its value only changed with the time of day and
    the weather, so automations written for it need new levels.
  - Irradiance mode is now the Irradiance sensor.
  - Sensors are named after their entry and what they measure. The default
    entry name is "Solar", giving "Solar Illuminance" and "Solar
    Irradiance"; an entry named "Garden" has "Garden Illuminance" and
    "Garden Irradiance".
- **Set up in the UI only.** YAML configuration isn't supported, and there's
  no `reload` action. If your configuration has a `solar_illuminance:`
  section, Home Assistant shows a repair asking you to remove it. See
  [Configuration](README.md#configuration).
- **Requires Home Assistant 2026.9** or newer, for probatio, which replaced
  voluptuous in Home Assistant 2026.9.

### New

- **Cloud coverage from weather entities.** If the weather entity reports its
  cloud coverage, as Met.no, OpenWeatherMap and AccuWeather do, it's used as
  well as the condition, so the value changes smoothly instead of jumping
  between a few levels. The condition still counts when it's darker, as in
  fog, rain or storms, so for any condition the integration knows, the value
  is never brighter than Illuminance's.
- **Repairs for the weather data source.** Home Assistant shows a repair if
  the source no longer exists, or has had no weather data for an hour. In the
  meantime, the illuminance divider is used. If the source's entity ID is
  renamed, the sensors follow it.
- **Diagnostics.** Each entry's diagnostics can be downloaded, to include when
  reporting a problem. They show its options, how the value was worked out,
  and the weather data source's state.

### Improved

- **A value while Home Assistant starts.** Until the weather data source is
  available, the sensors use the illuminance divider, instead of staying
  unknown until Home Assistant has started.
- **Fewer log messages.** An unexpected weather condition is logged as a
  warning once, until it changes or is fixed, instead of as an error each time
  the weather changes.
