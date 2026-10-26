# <img src="custom_components/solar_illuminance/brand/icon.png" alt="Solar Illuminance Sensor" width="50" height="50"/> Solar Illuminance Sensor

[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![Release](https://img.shields.io/github/v/release/sibartlett/ha-solar-illuminance)](https://github.com/sibartlett/ha-solar-illuminance/releases)
[![Tests](https://github.com/sibartlett/ha-solar-illuminance/actions/workflows/tests.yml/badge.svg)](https://github.com/sibartlett/ha-solar-illuminance/actions/workflows/tests.yml)

Creates a `sensor` entity that estimates outdoor illuminance based on either sun elevation or time of day.
In either case, the value can be further adjusted based on current weather conditions or cloud coverage obtained from another, existing entity.

Solar Illuminance is a fork of [Illuminance](https://github.com/pnbruckner/ha-illuminance) by [Phil Bruckner](https://github.com/pnbruckner), renamed so the two can be installed side by side.


## Modes of operation
Three modes are available: normal, irradiance & simple.

### Normal/Irradiance modes - Sun elevation
These modes use an algorithm from the US Naval Observatory[^1] for estimating sun illuminance or irradiance based on the sun's elevation (aka altitude.) The maximum illuminance value is about 150,000 lx, and the maximum irradiance value is about 1,250 Watts/M².
Below is an example of what the illuminance might look like over a three day period.

<p align="center">
  <img src=images/normal.png>
</p>

[^1]: Janiczek, P. M., and DeYoung, J. A. _Computer Programs for Sun and Moon Illuminance With Contingent Tables and Diagrams_. Circular No. 171. Washington, D. C.: United States Naval Observatory, 1987 [Google Scholar](https://scholar.google.com/scholar_lookup?title=Computer%20programs%20for%20sun%20and%20moon%20illuminance%20with%20contingent%20tables%20and%20diagrams&author=P.%20M.%20Janiczek&author=J.%20A.%20Deyoung&publication_year=1987&book=Computer%20programs%20for%20sun%20and%20moon%20illuminance%20with%20contingent%20tables%20and%20diagrams)

### Simple mode - Time of day
At night the value is 10 lx. From a little before sunrise to a little after the value is ramped up to whatever the current conditions indicate. The same happens around sunset, except the value is ramped down. For historical reasons, the maximum value is 10,000 lx. Below is an example of what that might look like over a three day period.

<p align="center">
  <img src=images/simple.png>
</p>

## Supported weather sources
Any weather entity that uses the [standard list of conditions](https://www.home-assistant.io/integrations/weather/#condition-mapping), or that provides a cloud coverage percentage, should work with this integration.
The following sources of weather data are known to be supported:

Integration | Notes
-|-
[AccuWeather](https://www.home-assistant.io/integrations/accuweather/) | `weather`
[Buienradar](https://www.home-assistant.io/integrations/buienradar/) | `weather`
[ecobee](https://www.home-assistant.io/integrations/ecobee/) |
[Meteorologisk institutt (Met.no)](https://www.home-assistant.io/integrations/met/) | `weather`
[OpenWeatherMap](https://www.home-assistant.io/integrations/openweathermap/) | `weather`; cloud_coverage & condition `sensor`

## Installation

The integration software must first be installed as a custom component.
You can use HACS to manage the installation and provide update notifications.
Or you can manually install the software.

<details>
<summary>With HACS</summary>

1. Add this repo as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories/):
   It should then appear as a new integration. Click on it. If necessary, search for "solar illuminance".
   ```text
   https://github.com/sibartlett/ha-solar-illuminance
   ```
   Or use this button:
  
   [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=sibartlett&repository=ha-solar-illuminance&category=integration)

1. Download the integration using the appropriate button.

</details>

<details>
<summary>Manual Installation</summary>

Download `solar_illuminance.zip` from the [latest release](https://github.com/sibartlett/ha-solar-illuminance/releases/latest),
and unzip it into `<config>/custom_components/solar_illuminance`,
where `<config>` is your Home Assistant configuration directory.

</details>

### Post Installation

After it has been downloaded you will need to restart Home Assistant.

### Versions

This custom integration supports HomeAssistant versions 2026.7 or newer.

## Configuration

Add sensors in the UI: go to **Settings** -> **Devices & services** -> **Add integration** and search for "Solar Illuminance". Each sensor has the following options. All but the name can be changed later with **Configure**; rename the sensor by renaming its entry.

Option | Description
-|-
Name | Name of the sensor. Default is `Solar Illuminance`.
Mode | `Normal` (default) uses sun elevation, `Simple` uses time of day, and `Irradiance` is the same as `Normal`, except the value is expressed as irradiance in Watts/M².
Update period in minutes | How often the sensor updates. Minimum is 0.5 (30 seconds). Default is 5.
Weather data source | Optional entity that indicates current weather conditions or cloud coverage percentage.
Illuminance divider when no weather data | Divisor to use when weather data is not available. Must be in the range of 1 (clear) through 10 (dark). Default is 10 if a weather data source is selected, or 1 if not.

YAML configuration is not supported.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
