# Security

Please report security problems privately, not in a public issue: use
**Report a vulnerability** on this repository's
[Security tab](https://github.com/sibartlett/ha-solar-illuminance/security).
I'll reply there, and publish a fix and an advisory once it's resolved.

Security fixes go into the latest version.

The integration only calculates a sensor value from the sun's position and
another entity's state: it doesn't connect to any service or store any
credentials.
