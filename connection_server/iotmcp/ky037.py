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
            if (time.time() - start_time) > 10.0:
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
            if (current_time - start_time) > max_duration:
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
    "KY037",
    description="KY037 sound sensor monitoring via MCP. Supports raw, voltage, trigger state and full report."
)

@mcp.tool()
async def read_raw(
    Real_time: bool = False,
) -> Optional[Any]:
    """
    Read raw ADC value from KY037.

    Parameters:
    - Real_time: if True, collect all reports within 10 seconds and return as list.

    Returns:
    A single raw reading, or list of readings if Real_time is True.
    """
    cmd = {"sensor": "KY037", "command": "read_raw"}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f'Web Error {response.status_code}'}
    id = response.json().get("id")
    if Real_time:
        data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": data, "count": len(data)}
    else:
        return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_voltage(
    Real_time: bool = False,
) -> Optional[Any]:
    """
    Read voltage value from KY037.

    Parameters:
    - Real_time: if True, collect all reports within 10 seconds and return as list.

    Returns:
    A single voltage reading, or list of readings if Real_time is True.
    """
    cmd = {"sensor": "KY037", "command": "read_voltage"}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f'Web Error {response.status_code}'}
    id = response.json().get("id")
    if Real_time:
        data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": data, "count": len(data)}
    else:
        return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_trigger(
    Real_time: bool = False,
) -> Optional[Any]:
    """
    Read digital trigger state from KY037.

    Parameters:
    - Real_time: if True, collect all reports within 10 seconds and return as list.

    Returns:
    A single trigger state, or list of states if Real_time is True.
    """
    cmd = {"sensor": "KY037", "command": "read_trigger"}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f'Web Error {response.status_code}'}
    id = response.json().get("id")
    if Real_time:
        data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": data, "count": len(data)}
    else:
        return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_all(
    Real_time: bool = False,
) -> Optional[Any]:
    """
    Read full report from KY037 (raw, voltage, triggered, timestamp).

    Parameters:
    - Real_time: if True, collect all reports within 10 seconds and return as list.

    Returns:
    A full report, or list of reports if Real_time is True.
    """
    cmd = {"sensor": "KY037", "command": None}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f'Web Error {response.status_code}'}
    id = response.json().get("id")
    if Real_time:
        data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": data, "count": len(data)}
    else:
        return monitor(DATA_PATH, DATA_FILE, id)

if __name__ == '__main__':
    sess = requests.Session()
    sess.head("http://localhost:8000/send_cmd")
    mcp.run()