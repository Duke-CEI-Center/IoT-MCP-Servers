import asyncio
import json
import os
import time
from typing import List, Dict, Any, Optional
import requests
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
            if time.time() - start_time > 10.0:
                return "Monitor Timeout"
        except KeyboardInterrupt:
            return None
        except Exception:
            return None

def monitor_realtime(directory: str, filename: str, id: str, max_duration: float = 10.0) -> Optional[List[Dict[Any, Any]]]:
    file_path = os.path.join(directory, filename)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File dont exist: {file_path}")
    
    start_time = time.time()
    initial_size = os.path.getsize(file_path)
    collected_data: List[Dict[Any, Any]] = []
    
    while True:
        try:
            current_time = time.time()
            elapsed_time = current_time - start_time
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
    "KY023",
    description="KY023 joystick module data monitoring via MCP. Supports raw and voltage readings, and button state."
)

@mcp.tool()
async def read_x(
    interval: float = 0.0,
    duration: float = 0.0,
    Real_time: bool = False,
) -> Optional[Any]:
    """
    Read X-axis voltage from the KY023 joystick.

    Parameters:
    - interval: time between readings in seconds.
    - duration: total duration in seconds.
    - Real_time: if True, return list of readings within 10 seconds.

    Returns:
    A voltage reading or list of readings if Real_time is True.
    """
    cmd = {"sensor": "KY023", "command": "read_x", "interval": interval, "duration": duration}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f'Web Error {response.status_code}'}
    id = response.json().get("id")
    if Real_time:
        data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": data, "count": len(data)}
    return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_y(
    interval: float = 0.0,
    duration: float = 0.0,
    Real_time: bool = False,
) -> Optional[Any]:
    """
    Read Y-axis voltage from the KY023 joystick.

    Parameters:
    - interval: time between readings in seconds.
    - duration: total duration in seconds.
    - Real_time: if True, return list of readings within 10 seconds.

    Returns:
    A voltage reading or list of readings if Real_time is True.
    """
    cmd = {"sensor": "KY023", "command": "read_y", "interval": interval, "duration": duration}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f'Web Error {response.status_code}'}
    id = response.json().get("id")
    if Real_time:
        data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": data, "count": len(data)}
    return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_raw(
    interval: float = 0.0,
    duration: float = 0.0,
    Real_time: bool = False,
) -> Optional[Any]:
    """
    Read raw ADC values for X and Y axes from the KY023 joystick.

    Parameters:
    - interval: time between readings in seconds.
    - duration: total duration in seconds.
    - Real_time: if True, return list of readings within 10 seconds.

    Returns:
    A raw reading dict or list of readings if Real_time is True.
    """
    cmd = {"sensor": "KY023", "command": "read_raw", "interval": interval, "duration": duration}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f'Web Error {response.status_code}'}
    id = response.json().get("id")
    if Real_time:
        data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": data, "count": len(data)}
    return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_switch(
    interval: float = 0.0,
    duration: float = 0.0,
    Real_time: bool = False,
) -> Optional[Any]:
    """
    Read button pressed state from the KY023 joystick.

    Parameters:
    - interval: time between readings in seconds.
    - duration: total duration in seconds.
    - Real_time: if True, return list of readings within 10 seconds.

    Returns:
    A pressed state or list of readings if Real_time is True.
    """
    cmd = {"sensor": "KY023", "command": "read_switch", "interval": interval, "duration": duration}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f'Web Error {response.status_code}'}
    id = response.json().get("id")
    if Real_time:
        data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": data, "count": len(data)}
    return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_all(
    interval: float = 0.0,
    duration: float = 0.0,
    Real_time: bool = False,
) -> Optional[Any]:
    """
    Read full report from the KY023 joystick: raw, voltage, and button state.

    Parameters:
    - interval: time between readings in seconds.
    - duration: total duration in seconds.
    - Real_time: if True, return list of readings within 10 seconds.

    Returns:
    A full report dict or list of readings if Real_time is True.
    """
    cmd = {"sensor": "KY023", "command": "read_all", "interval": interval, "duration": duration}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f'Web Error {response.status_code}'}
    id = response.json().get("id")
    if Real_time:
        data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": data, "count": len(data)}
    return monitor(DATA_PATH, DATA_FILE, id)

if __name__ == '__main__':
    sess = requests.Session()
    sess.head("http://localhost:8000/send_cmd")
    mcp.run()