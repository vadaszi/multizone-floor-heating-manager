# Security policy

## Reporting a vulnerability

Please report security problems **privately**, not in a public issue: on GitHub, open the repository's **Security** tab and choose **Report a vulnerability**. Describe what you found, how to reproduce it and what an attacker could do with it. You will get an answer as soon as possible; a fix is published with a release and a note in the [changelog](CHANGELOG.md).

## Scope

- The integration (`custom_components/multizone_floor_heating_manager/`).
- The Shelly watchdog scripts (`shelly_scripts/`).

Only the latest release gets fixes.

## Known limits by design

- The Shelly scripts answer on the local network over plain HTTP. Without device authentication, anyone who can reach a Shelly can send it heartbeats or switch its outputs directly. Enable authentication on the Shellys if your network is not trusted, and never expose them to the internet: [Heartbeat protocol → Authentication and security](docs/heartbeat-protocol.md#authentication-and-security).
- Passwords and the watchdog ping URL belong in Home Assistant's `secrets.yaml`; the integration never logs them.
