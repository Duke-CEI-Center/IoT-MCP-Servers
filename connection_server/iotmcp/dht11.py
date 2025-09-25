import asyncio
import json
import os
import time
from typing import List, Dict, Any, Optional
import requests
import serial
import serial.tools.list_ports
from mcp.server.fastmcp import FastMCP

TCP_HOST = '0.0.0.0'
TCP_PORT = 8000
DATA_PATH = '../data/'
DATA_FILE = 'all.jsonl'

def monitor(directory: str, filename: str, id: str) -> Optional[Dict[Any, Any]]:
    file_path = os.path.join(directory, filename)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File dont exist: {file_path}")
    start_time = time.time()
    initial_size = os.path.getsize(file_path)
    
    while True:
        try:
            current_size = os.path.getsize(file_path)
            
            if current_size > initial_size:
                with open(file_path, 'r', encoding='utf-8') as f:
                    f.seek(initial_size)
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                json_obj = json.loads(line)
                                
                                if json_obj["id"] == id:
                                    return json_obj
                            except json.JSONDecodeError as e:
                                print(f"JSON Parsing Error: {e}")
                                continue
                initial_size = current_size
            time.sleep(0.05)
            if(time.time() - start_time > 10.0):
                return "Monitor Timeout"
            
        except KeyboardInterrupt:
            return None
        except Exception as e:
            return None

def monitor_realtime(directory: str, filename: str, id: str, max_duration: float = 10.0) -> Optional[Dict[Any, Any]]:
    """
    Monitor file for real-time data collection within specified duration.
    
    Parameters:
    - directory: Directory path of the file
    - filename: Name of the file to monitor
    - id: ID to match in the JSON objects
    - max_duration: Maximum duration to monitor in seconds (default: 10.0)
    
    Returns:
    List of all valid JSON objects with matching ID found within the duration
    """
    file_path = os.path.join(directory, filename)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File dont exist: {file_path}")
    
    start_time = time.time()
    initial_size = os.path.getsize(file_path)
    collected_data = []
    
    while True:
        try:
            current_time = time.time()
            elapsed_time = current_time - start_time
            
            # Check if max duration exceeded
            if elapsed_time > max_duration:
                break
            
            current_size = os.path.getsize(file_path)
            
            if current_size > initial_size:
                with open(file_path, 'r', encoding='utf-8') as f:
                    f.seek(initial_size)
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                json_obj = json.loads(line)
                                
                                if json_obj["id"] == id:
                                    collected_data.append(json_obj)
                            except json.JSONDecodeError as e:
                                print(f"JSON Parsing Error: {e}")
                                continue
                initial_size = current_size
            
            time.sleep(0.05)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error during real-time monitoring: {e}")
            break
    
    return collected_data

mcp = FastMCP(
    "DHT11",
    description="DHT11 PC data monitoring via MCP. Supports general_accuracy temperature and humidity reading."
)

@mcp.tool()
async def read_temperature(
    interval: float = 0.0,
    duration: float = 0.0,
    Real_time: bool = False,
) -> Optional[Dict[Any, Any]]:
    """
    Read temperature values from the DHT11 sensor.

    Parameters:
    - interval: time between readings in seconds. Default 0.0 returns a single reading.
    - duration: total duration in seconds for continuous readings (0.0 => single reading;
      >0.0 => readings over duration; <0.0 => continuous until stopped).
    - Real_time: if True, collect all valid data within 10 seconds and return as list.

    Returns:
    A temperature with time stamp, or list of temperatures if Real_time is True.
    """
    cmd = {"sensor": "DHT11","command": "read_temp", "interval": interval, "duration": duration}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    id = None
    if response.status_code == 200:
        data = response.json()
        id = data["id"]
    else:
        return {"status": f'Web Error {response.status_code}'}
    
    if Real_time:
        collected_data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": collected_data, "count": len(collected_data)}
    else:
        return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_humidity(
    interval: float = 0.0,
    duration: float = 0.0,
    Real_time: bool = False,
) -> Optional[Dict[Any, Any]]:
    """
    Read humidity values from the DHT11 sensor.

    Parameters:
    - interval: time between readings in seconds. Default 0.0 returns a single reading.
    - duration: total duration in seconds for continuous readings (0.0 => single reading;
      >0.0 => readings over duration; <0.0 => continuous until stopped).
    - Real_time: if True, collect all valid data within 10 seconds and return as list.

    Returns:
    A humidity with time stamp, or list of humidity readings if Real_time is True.
    """
    cmd = {"sensor": "DHT11","command": "read_hum", "interval": interval, "duration": duration}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    id = None
    if response.status_code == 200:
        data = response.json()
        id = data["id"]
    else:
        return {"status": f'Web Error {response.status_code}'}
    
    if Real_time:
        collected_data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": collected_data, "count": len(collected_data)}
    else:
        return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_all(
    interval: float = 0.0,
    duration: float = 0.0,
    Real_time: bool = False,
) -> Optional[Dict[Any, Any]]:
    """
    Read temperature & humidity values from the DHT11 sensor.

    Parameters:
    - interval: time between readings in seconds. Default 0.0 returns a single reading.
    - duration: total duration in seconds for continuous readings (0.0 => single reading;
      >0.0 => readings over duration; <0.0 => continuous until stopped).
    - Real_time: if True, collect all valid data within 10 seconds and return as list.

    Returns:
    A json-format data of temperature & humidity with time stamp, or list of readings if Real_time is True.
    """
    cmd = {"sensor": "DHT11","command": "read_all", "interval": interval, "duration": duration}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    id = None
    if response.status_code == 200:
        data = response.json()
        id = data["id"]
    else:
        return {"status": f'Web Error {response.status_code}'}
    
    if Real_time:
        collected_data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": collected_data, "count": len(collected_data)}
    else:
        return monitor(DATA_PATH, DATA_FILE, id)

if __name__ == '__main__':
    sess = requests.Session()
    sess.head("http://localhost:8000/send_cmd")
    mcp.run()