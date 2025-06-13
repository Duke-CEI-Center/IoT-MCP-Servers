# IoT MCP Server

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

A comprehensive Model Context Protocol (MCP) server that provides Internet of Things (IoT) device integration for AI assistants like Claude Desktop and Cursor IDE. This server enables AI to read sensor data from IoT devices and dispatch data collection tasks to IoT devices through a unified interface.

## Demo

[DEMO_URL]

*IoT MCP Server demonstration showing sensor data reading, device task assignment, and real-time monitoring*

## Features

- **Sensor Data Reading**: Read real-time data from various IoT sensors (temperature, humidity, pressure, motion, etc.)
- **Device Task Management**: Dispatch data collection tasks to IoT devices with configurable intervals and parameters
- **Multi-Protocol Support**: Connect to devices via MQTT, HTTP REST API, CoAP, and custom protocols
- **Real-time Monitoring**: Stream live sensor data and device status updates
- **Device Discovery**: Automatically discover and register IoT devices on the network
- **Data Filtering**: Apply filters and transformations to sensor data before processing
- **Alert System**: Configure alerts based on sensor thresholds and device status

## Prerequisites

Before using this MCP server, you need to install the following components:
1. Python 3.8+
The IoT MCP server is built with Python and requires Python 3.8 or higher.
Check if Python is installed:
```bash
bashpython --version
# or
python3 --version
```

Installation:

Windows: Download from python.org
macOS: Download from python.org or use Homebrew: brew install python
Linux: Usually pre-installed, or install via package manager: sudo apt install python3 python3-pip

2. uv (Python Package Manager)
This project uses uv for fast and reliable Python package management.
Installation:
macOS and Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Windows:
```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
Alternative Installation Methods:

```bash
# Using pip
pip install uv

# Using Homebrew (macOS)
brew install uv

# Using cargo (if you have Rust installed)
cargo install --git https://github.com/astral-sh/uv uv
Verify Installation:
bashuv --version
```

## Installation

### Clone the Repository

```bash
git clone [PLACEHOLDER_REPOSITORY_URL]
cd iot-mcp-server
```

That's it! The project uses `uv` for dependency management, which will automatically handle all Python dependencies when the server runs.

## Configuration

### 1. Hardware Setup

**Connect MCU and Sensors:**
- Properly connect your MCU (microcontroller) with the sensors according to your sensor's wiring diagram
- Ensure stable power supply and correct pin connections

**Network/Serial Connection:**
- **Network Option:** Ensure your MCU and your computer are on the same network (WiFi/Ethernet)
- **Serial Option:** Connect MCU to your computer via USB/Serial cable

### 2. Sensor Configuration

**Navigate to Sensor Directory:**
```bash
# Example for MPU6050 sensor
cd sensors/MPU6050
```

**Run Sensor Configuration:**
```bash
python config.py
```

This will configure the sensor parameters and generate the necessary configuration files.

### 3. MCU Programming

**Upload Main Script to MCU:**
```bash
# Use mpremote to transfer main.py to your MCU
mpremote connect [PORT] cp main.py :
```

Replace `[PORT]` with your MCU's serial port (e.g., `/dev/ttyUSB0` on Linux, `COM3` on Windows, `/dev/tty.usbserial-*` on macOS).

**Alternative upload methods:**
```bash
# For ESP32/ESP8266
mpremote connect /dev/ttyUSB0 cp main.py :

# For Raspberry Pi Pico
mpremote connect /dev/ttyACM0 cp main.py :
```

### 4. MCP Server Setup

**Initialize and Configure MCP Server:**
```bash
# Initialize uv project (if not already done)
uv init .

# Add MCP dependencies
uv add "mcp[cli]"
```

This will set up the MCP server with all necessary dependencies.
## Usage Examples

### 1. Reading Sensor Data

```
Ask Claude: "Read the current temperature and humidity from all sensors in the living room"
```

**Expected Response:**
- Current temperature: 22.5°C
- Current humidity: 45%
- Timestamp: [CURRENT_TIMESTAMP]
- Device status: Online

### 2. Dispatching Data Collection Tasks

```
Ask Claude: "Set up a task to collect temperature data every 5 minutes from sensor_001 for the next 2 hours"
```

**Task Configuration:**
- Device: sensor_001
- Data type: temperature
- Interval: 5 minutes
- Duration: 2 hours
- Storage: Local buffer + cloud sync

### 3. Real-time Monitoring

```
Ask Claude: "Start monitoring all motion sensors and alert me if any detect movement"
```

**Monitoring Setup:**
- Real-time data streaming
- Threshold-based alerts
- Device health monitoring

### Common Issues

1. **MCP Server Not Detected:**
   - Verify the absolute path in configuration
   - Check that Node.js is installed and accessible
   - Restart Claude Desktop/Cursor after configuration changes

2. **Device Connection Failures:**
   - Verify device IP addresses and network connectivity
   - Check protocol-specific configuration (MQTT broker, HTTP endpoints)
   - Ensure device authentication credentials are correct

3. **MQTT Connection Issues:**
   ```bash
   # Test MQTT connection manually
   mosquitto_pub -h localhost -t test/topic -m "test message"
   mosquitto_sub -h localhost -t test/topic
   ```

4. **Permission Errors:**
   - Check file permissions for configuration files
   - Ensure network access permissions for device communication
   - Verify user permissions for required system resources

5. **Data Reading Timeouts:**
   - Check device responsiveness
   - Verify network stability
   - Adjust timeout parameters in configuration

### Debugging

1. **Check MCP Server Logs:**
   - **Claude Desktop:** `~/Library/Logs/Claude/mcp*.log` (macOS)
   - **Cursor:** Check the MCP settings panel for error messages

2. **Test Device Connectivity:**
   ```bash
   # HTTP devices
   curl -X GET http://[DEVICE_IP]/status
   
   # MQTT devices
   mosquitto_sub -h [BROKER_IP] -t [DEVICE_TOPIC]
   
   # Ping test
   ping [DEVICE_IP]
   ```

3. **Verify Configuration:**
   ```bash
   # Validate JSON configuration files
   node -e "console.log(JSON.parse(require('fs').readFileSync('config/devices.json')))"
   ```

4. **Check Environment Variables:**
   ```bash
   echo $IOT_CONFIG_PATH
   echo $PATH
   ```

## Supported Devices

### Currently Supported Device Types
- [ESP32 s3]


## Security Considerations

- **Device Authentication:** All device communications should use proper authentication
- **Network Security:** Ensure IoT devices are on secure networks
- **Data Encryption:** Use encrypted protocols where possible
- **Access Control:** Implement proper access controls for device management
- **Regular Updates:** Keep device firmware and server dependen

## License

This work is licensed under a [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-nc-sa/4.0/).
