# <img src="custom_components/solar_illuminance/brand/icon.png" alt="Solar Illuminance" width="50" height="50"/> Solar Illuminance

[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![Release](https://img.shields.io/github/v/release/sibartlett/ha-solar-illuminance)](https://github.com/sibartlett/ha-solar-illuminance/releases)
[![Tests](https://github.com/sibartlett/ha-solar-illuminance/actions/workflows/tests.yml/badge.svg)](https://github.com/sibartlett/ha-solar-illuminance/actions/workflows/tests.yml)

Estimates the outdoor illuminance from the sun's elevation, adjusted for the current weather conditions or cloud coverage from another, existing entity.

Solar Illuminance is a fork of [Illuminance](https://github.com/pnbruckner/ha-illuminance) by [Phil Bruckner](https://github.com/pnbruckner), renamed so the two can be installed side by side.
Coming from Illuminance? See [Moving from Illuminance](#moving-from-illuminance).

## Use cases

- Turn lights on when it gets dark outside, and off when it's bright, without an outdoor light sensor. Unlike sunset and sunrise, the value is lower on a dark, stormy day.
- Close blinds or awnings when the sun is strong.
- Compare it with an indoor light sensor, to tell whether a room is dark because it's dark outside.

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
1. Restart Home Assistant.

</details>

<details>
<summary>Manual Installation</summary>

Download `solar_illuminance.zip` from the [latest release](https://github.com/sibartlett/ha-solar-illuminance/releases/latest),
and unzip it into `<config>/custom_components/solar_illuminance`,
where `<config>` is your Home Assistant configuration directory. Then restart Home Assistant.

</details>

### Versions

This custom integration supports Home Assistant 2026.7 or newer.

## Configuration

Add sensors in the UI: go to **Settings** -> **Devices & services** -> **Add integration** and search for "Solar Illuminance". Each sensor has the following options. All but the name can be changed later with **Configure**; rename the sensors by renaming their entry.

Option | Description
-|-
Name | Name of the entry, and so of its device and sensors. Default is `Solar`.
Update period in minutes | How often the sensor updates. Minimum is 0.5 (30 seconds). Default is 5.
Weather data source | Optional entity that indicates current weather conditions or cloud coverage percentage.
Illuminance divider when no weather data | Divisor to use when weather data is not available. Must be in the range of 1 (clear) through 10 (dark). Default is 10 if a weather data source is selected, or 1 if not.

YAML configuration is not supported.

## Sensors

Each entry has two sensors, on a device named after the entry:

- **Illuminance**, in lx. For an entry named "Solar", it's "Solar Illuminance".
- **Irradiance**, the same estimate in W/m². It's disabled to begin with: enable it in the sensor's settings if you need it, for example to compare with a weather station's solar radiation.

They use an algorithm from the US Naval Observatory[^1] for estimating sun illuminance based on the sun's elevation (aka altitude). The maximum illuminance value is about 150,000 lx, which is about 1,250 W/m².
Below is an example of what the illuminance might look like over a three day period.

<p align="center">
  <img src="images/normal.png" alt="The illuminance over three days, rising and falling with the sun">
</p>

[^1]: Janiczek, P. M., and DeYoung, J. A. _Computer Programs for Sun and Moon Illuminance With Contingent Tables and Diagrams_. Circular No. 171. Washington, D. C.: United States Naval Observatory, 1987 [Google Scholar](https://scholar.google.com/scholar_lookup?title=Computer%20programs%20for%20sun%20and%20moon%20illuminance%20with%20contingent%20tables%20and%20diagrams&author=P.%20M.%20Janiczek&author=J.%20A.%20Deyoung&publication_year=1987&book=Computer%20programs%20for%20sun%20and%20moon%20illuminance%20with%20contingent%20tables%20and%20diagrams)

## Supported weather sources
Any weather entity that uses the [standard list of conditions](https://www.home-assistant.io/integrations/weather/#condition-mapping), or any sensor that provides a cloud coverage percentage, should work with this integration.
If a weather entity also reports its cloud coverage, whichever of the two indicates it's darker is used: the cloud coverage is more precise, but the condition also reflects fog, rain and storms.
The following sources of weather data are known to be supported:

Integration | Notes
-|-
[AccuWeather](https://www.home-assistant.io/integrations/accuweather/) | `weather`, with cloud coverage
[Buienradar](https://www.home-assistant.io/integrations/buienradar/) | `weather`
[ecobee](https://www.home-assistant.io/integrations/ecobee/) | `weather`, including its extra conditions: snowy-heavy, tornado and hazy
[Environment Canada](https://www.home-assistant.io/integrations/environment_canada/) | `weather`
[Meteorologisk institutt (Met.no)](https://www.home-assistant.io/integrations/met/) | `weather`, with cloud coverage
[OpenWeatherMap](https://www.home-assistant.io/integrations/openweathermap/) | `weather`, with cloud coverage; cloud_coverage & condition `sensor`
Any integration | A `sensor` whose state is the cloud coverage, from 0 to 100%

### How the weather changes the value

The value without weather is divided by a number from 1 (clear) to 10 (dark).

Each weather condition has its own divisor:

Divisor | Conditions
-|-
1 | sunny, clear-night, windy
2 | partlycloudy, windy-variant, hazy
3 | mostlycloudy
5 | cloudy, fog, rainy, snowy, snowy-rainy, hail, exceptional, tornado
10 | lightning, lightning-rainy, pouring, snowy-heavy

A cloud coverage percentage gives a divisor of 10<sup>coverage ÷ 100</sup>: 1 when it's clear, about 3.2 at 50%, and 10 when it's overcast.
If a weather entity reports both, the larger divisor is used, so the value reflects whichever indicates it's darker.

Without weather data, or with a condition the integration doesn't know and no cloud coverage, the illuminance divider option is used instead.

## How the value updates

The sensor recalculates its value every update period (5 minutes by default), and straight away whenever its weather data source changes condition or cloud coverage.
It needs no internet connection of its own: the sun's position is calculated from Home Assistant's home location, and the weather comes from the weather data source, which updates as often as its own integration does.

## Examples

Turn on the porch light when it's been darker than 1,000 lx for 5 minutes, and off when it's been brighter than 2,000 lx for 5 minutes. The gap between the two stops the light switching on and off when the value hovers around one level.

Make two automations, pasting each into the automation editor with **Edit in YAML** from its menu, or build them in the visual editor with a **Numeric state** trigger.

```yaml
alias: Porch light on when it's dark
triggers:
  - trigger: numeric_state
    entity_id: sensor.solar_illuminance
    below: 1000
    for:
      minutes: 5
actions:
  - action: light.turn_on
    target:
      entity_id: light.porch
```

```yaml
alias: Porch light off when it's bright
triggers:
  - trigger: numeric_state
    entity_id: sensor.solar_illuminance
    above: 2000
    for:
      minutes: 5
actions:
  - action: light.turn_off
    target:
      entity_id: light.porch
```

A clear day reaches about 150,000 lx, and the weather divides that, so pick levels by watching the sensor's history for a few days.

## Known limitations

- The value is an estimate of the light outdoors in the open, not a measurement. It doesn't take into account shade, the direction a window faces, or the moon.
- The irradiance is the illuminance divided by 120 lx per W/m², a rough average for sunlight. For solar power, use a solar forecast integration instead.
- All sensors use Home Assistant's home location.
- Weather conditions only give a few levels of brightness. A weather data source that also reports cloud coverage gives a smoother value.
- The value can only be as current as the weather data source, which may update only every hour or so.

## Troubleshooting

- **The value doesn't change with the weather.** Check the weather data source's state in **Tools** -> **States** (**Developer tools** before Home Assistant 2026.8). If it's unavailable, the sensor uses the illuminance divider instead. If it has had no weather data for an hour, or no longer exists, Home Assistant shows a repair in **Settings** -> **Repairs**.
- **The log says "Unexpected current condition".** The weather data source reported a condition the integration doesn't know. The sensor uses the source's cloud coverage if it has one, or the illuminance divider if not. Please [open an issue](https://github.com/sibartlett/ha-solar-illuminance/issues) with the condition and the weather integration.
- **The value seems wrong.** Download the sensor's diagnostics from its entry's menu, in **Settings** -> **Devices & services** -> **Solar Illuminance**. They show the weather used and the divisor. To see each update in the log, enable debug logging from the menu at the top of that page. Include both when reporting a problem.

## Moving from Illuminance

Solar Illuminance doesn't take over Illuminance's sensors. To move to it:

1. Install Solar Illuminance, and add your sensors again with the same options. There are no modes: the value always follows the sun's elevation, as in Illuminance's normal mode. If you used simple mode, its values were different, so check the levels your automations use. If you used irradiance mode, enable the irradiance sensor.
1. Point your automations, scripts and dashboards at the new sensors' entity IDs.
1. Remove Illuminance.

Or, to keep an entity ID, remove the Illuminance sensor first, then give the new sensor its entity ID in the sensor's settings. Automations, scripts and dashboards then carry on using it.

## Removal

1. Go to **Settings** -> **Devices & services** -> **Solar Illuminance**, and delete each entry from its menu.
1. If you installed it with HACS, remove it in HACS. Otherwise, delete `<config>/custom_components/solar_illuminance`.
1. Restart Home Assistant.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
