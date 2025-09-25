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
                            except json.JSONDecodeError:
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
                            except json.JSONDecodeError:
                                continue
                initial_size = current_size
            time.sleep(0.05)
        except KeyboardInterrupt:
            break
        except Exception:
            break
    return collected_data

mcp = FastMCP(
    "KY026",
    description="KY026 IR flame sensor module via MCP. Supports raw ADC, voltage and detected status readings."
)

@mcp.tool()
async def read_raw(
    Real_time: bool = False
) -> Optional[Dict[Any, Any]]:
    """
    Read raw ADC value from the KY026 sensor.

    Parameters:
    - Real_time: if True, collect all valid raw readings within 10 seconds and return as list.

    Returns:
    A raw ADC reading with timestamp, or list of readings if Real_time is True.
    """
    cmd = {"sensor": "KY026", "command": "read_raw"}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f"Web Error {response.status_code}"}
    data = response.json()
    id = data.get("id")
    if Real_time:
        collected = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": collected, "count": len(collected or [])}
    else:
        return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_voltage(
    Real_time: bool = False
) -> Optional[Dict[Any, Any]]:
    """
    Read voltage (AO) from the KY026 sensor.

    Parameters:
    - Real_time: if True, collect all voltage readings within 10 seconds and return as list.

    Returns:
    A voltage reading with timestamp, or list of readings if Real_time is True.
    """
    cmd = {"sensor": "KY026", "command": "read_voltage"}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f"Web Error {response.status_code}"}
    data = response.json()
    id = data.get("id")
    if Real_time:
        collected = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": collected, "count": len(collected or [])}
    else:
        return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_detected(
    Real_time: bool = False
) -> Optional[Dict[Any, Any]]:
    """
    Read digital detected status from the KY026 sensor.

    Parameters:
    - Real_time: if True, collect all status readings within 10 seconds and return as list.

    Returns:
    A detected status with timestamp, or list of readings if Real_time is True.
    """
    cmd = {"sensor": "KY026", "command": "read_detected"}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f"Web Error {response.status_code}"}
    data = response.json()
    id = data.get("id")
    if Real_time:
        collected = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": collected, "count": len(collected or [])}
    else:
        return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_all(
    Real_time: bool = False
) -> Optional[Dict[Any, Any]]:
    """
    Read full report (raw, voltage, detected) from the KY026 sensor.

    Parameters:
    - Real_time: if True, collect all full reports within 10 seconds and return as list.

    Returns:
    A full sensor report with timestamp, or list of reports if Real_time is True.
    """
    cmd = {"sensor": "KY026", "command": "read_all"}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f"Web Error {response.status_code}"}
    data = response.json()
    id = data.get("id")
    if Real_time:
        collected = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": collected, "count": len(collected or [])}
    else:
        return monitor(DATA_PATH, DATA_FILE, id)

if __name__ == '__main__':
    sess = requests.Session()
    sess.head("http://localhost:8000/send_cmd")
    mcp.run()