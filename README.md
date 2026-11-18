# Aero Connect

Aero Connect is a disaster-response UAV communications dashboard. It combines a live React dashboard, a FastAPI state service, a deterministic simulation, and optional telemetry bridges for Raspberry Pi and Pixhawk hardware.

> **Current status:** The dashboard runs without hardware using a built-in simulation. Hardware support is partial and opt-in: telemetry is received over HTTP from agents or external collectors. The application does not control a real aircraft, configure radios, or provide a live camera stream.

## What it does

- Displays UAV mission state, a map, network metrics, RF activity, system health, events, and discovered client devices.
- Streams the server-owned state to the browser over WebSocket (`/ws`) and serves snapshots through REST (`/api/state`).
- Provides Deploy, Return, and Reset controls for the simulated UAV.
- Overlays fresh Pi, Pixhawk, backhaul, and RF reports on the simulation. Hardware reports expire after 15 seconds; expired fields fall back to simulation.
- Labels source-aware fields as `hardware` or `simulated` so live reports are distinguishable from generated values.

## Hardware components and current implementation

The following describes the project's intended field setup and the code that exists today. Hardware is optional; the dashboard starts in simulation mode.

| Component | Role in a field setup | Current implementation |
| --- | --- | --- |
| Raspberry Pi edge computer | Runs telemetry agents and forwards reports to the Aero Connect backend over IP. | Agents are provided for Wi-Fi client discovery, Pixhawk forwarding, and backhaul probing. Pi CPU, memory, temperature, uptime, storage, and interface metrics can be posted to an endpoint, but a system-metrics collection agent is not included. |
| Pixhawk-compatible flight controller | Supplies flight mode, armed state, GPS, position, speed, attitude, and battery readings over MAVLink serial. | `pi/pixhawk_agent.py` reads MAVLink using `pymavlink` and posts to `/api/telemetry/pixhawk`. The dashboard uses fresh position, altitude, speed, heading, battery, GPS fix, satellites, and armed state where available. This is telemetry ingestion; no flight commands are sent to the controller. |
| RTL-SDR receiver (optional) | Can be used by an operator's RF scanner to summarize activity in a selected frequency range. | `/api/telemetry/rf` accepts scan summaries and displays them while fresh. No RTL-SDR capture/scanner agent is included; an external collector must produce the documented JSON payload. |
| Ubiquiti NanoStation or other IP backhaul (optional) | Provides a point-to-point network path between the field network and the backend. | `pi/backhaul_agent.py` probes an HTTP endpoint and reports reachability, median round-trip time, and failed-probe percentage. It does not configure, monitor, or read radio-specific NanoStation statistics. |
| Wi-Fi access point / client-facing interface | Provides the local network on which responder devices connect. | `pi/clients_agent.py` discovers neighbour entries on Wi-Fi interfaces and posts client IP, MAC, optional hostname, interface, and status. It reads dnsmasq leases or reverse DNS only when available. It does not scan the backhaul interface unless explicitly configured. |
| UAV camera | Would provide imagery or video from the aircraft. | The dashboard currently shows camera status and simulated detections only. There is no camera capture, video transport, or computer-vision integration. |
| Ground station / operator laptop | Runs the backend and dashboard and connects to the field network. | FastAPI serves the API and WebSocket; the Vite development server serves the frontend. The configured map scenario uses fixed sample coordinates and users. |

### Data behavior

The simulation is the default state source. It advances once per second, moves a virtual UAV between a base and a fixed incident zone, and derives network, RF, camera, and system values from that scenario. It has no random generator.

Fresh hardware reports selectively replace simulation fields:

- **Pixhawk:** UAV telemetry and GPS provenance; valid, fresh GPS coordinates replace the simulated map position. Invalid or stale GPS is not presented as a valid fix.
- **Raspberry Pi system report:** system health values.
- **RTL-SDR report:** RF scan range, peak, noise floor, occupancy, and occupied bands.
- **Backhaul probe:** network and base-station backhaul status, latency, packet loss, and target.
- **Pi client scan:** a separate `live_clients` list; it does not replace the simulation's sample `users`.

Each telemetry store is in memory and holds only the latest report. Reports are unauthenticated and expire after 15 seconds. Restarting the backend clears them.

## Architecture

- `frontend/`: React 19, TypeScript, Vite, Tailwind CSS, and React Leaflet dashboard.
- `backend/`: FastAPI, Pydantic validation, deterministic simulation engine, in-memory telemetry stores, REST API, and WebSocket broadcast.
- `pi/`: standalone Linux-side Python agents for Pixhawk, backhaul, and Wi-Fi client discovery.

## Run locally

### Backend

From the project root in PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The frontend uses the local backend at port 8000. The backend CORS allowlist currently includes localhost and 127.0.0.1 on port 5173.

## Raspberry Pi agents

The agents run on Linux and use the Python standard library, except the Pixhawk agent, which also needs `pymavlink`:

```sh
python3 -m pip install pymavlink
```

Adjust the example backend address (`192.168.1.10`) to the address reachable from your field network. Use `--help` on each script to see options.

### Pixhawk MAVLink bridge

Connect the flight controller to the Pi's serial/USB device, confirm the device path and baud rate, then run:

```sh
python3 pi/pixhawk_agent.py --device /dev/ttyACM0 --baud 115200 \
  --endpoint http://192.168.1.10:8000/api/telemetry/pixhawk
```

The agent waits for a heartbeat, requests selected MAVLink messages, and posts a report about every two seconds. It reconnects after a lost heartbeat or connection error. Configure the serial device and baud rate for your flight controller.

### Backhaul probe

```sh
python3 pi/backhaul_agent.py \
  --target 192.168.1.10 \
  --probe-url http://192.168.1.10:8000/api/state \
  --endpoint http://192.168.1.10:8000/api/telemetry/backhaul
```

The default is five HTTP probes every five seconds. The reported packet-loss percentage is based on failed probes; latency is the median successful HTTP round trip.

### Wi-Fi client discovery

Inspect the Pi's interfaces and neighbours first:

```sh
ip addr
ip neigh
iw dev
ip route
```

The agent discovers wireless interface names with `iw dev` by default and scans only those interfaces. To select an interface explicitly:

```sh
python3 pi/clients_agent.py \
  --interface <client-facing-interface> \
  --endpoint http://192.168.1.10:8000/api/clients
```

It sends a scan every three seconds by default. The supplied systemd unit is `pi/systemd/aeraconnect-clients.service`; inspect and adjust its paths and endpoint before installing it on a Pi.

### Other telemetry producers

There is no bundled agent for Pi system metrics or RTL-SDR scanning. A collector can POST JSON to the endpoints below. The API schema is validated by Pydantic; see `backend/app/telemetry/models.py` for accepted fields and constraints. For example, a Pi system report is:

```json
{
  "cpu_usage": 31.7,
  "memory_usage": 48.2,
  "temperature": 53.4,
  "uptime": 123456,
  "storage_usage": 36.1,
  "network_interface_status": "up",
  "ip_address": "192.168.1.23"
}
```

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Backend liveness |
| `GET` | `/api/state` | Current full state snapshot |
| `WS` | `/ws` | Full state stream, broadcast about once per second |
| `POST` | `/api/simulation/deploy` | Deploy the simulated UAV |
| `POST` | `/api/simulation/return` | Return the simulated UAV |
| `POST` | `/api/simulation/reset` | Reset the scenario |
| `POST` | `/api/telemetry/pi` | Accept Pi system telemetry |
| `POST` | `/api/telemetry/pixhawk` | Accept Pixhawk MAVLink telemetry |
| `POST` | `/api/telemetry/rf` | Accept RF scan summary |
| `POST` | `/api/telemetry/backhaul` | Accept Pi-to-backend probe results |
| `POST` | `/api/clients` | Accept a Pi client-discovery scan |

Interactive API documentation is available at <http://localhost:8000/docs> while the backend is running.

## Requirements

- Python 3.10 or newer for the backend.
- Node.js and npm for the frontend.
- Linux and Python 3 for the optional Pi agents.
- `pymavlink` on the Pi only when using the Pixhawk bridge.
- Network reachability from telemetry producers to the backend.

No radio, aircraft, SDR, Pi, or camera is required to run the local simulation.

## Security and operational limits

- Telemetry endpoints currently have no authentication or authorization. Run the backend only on a trusted network until access controls are added.
- The included backhaul and sample agent URLs use plain HTTP. Use a protected network or add TLS and authentication before exposing telemetry over an untrusted network.
- The backend stores telemetry in memory; it does not persist data across restarts.
- The dashboard is for monitoring and simulation. It does not implement flight control, fail-safe logic, RF transmission, or camera streaming.

## License

No license has been selected yet. Until one is added, the project is published without an explicit open-source license.
