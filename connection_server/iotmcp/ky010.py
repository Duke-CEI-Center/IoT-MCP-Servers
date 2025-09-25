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
            if (time.time() - start_time > 10.0):
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
    collected_data = []
    
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
    "KY010",
    description="KY010 photo interrupter PC data monitoring via MCP. Supports raw digital and blocked status readings."
)

@mcp.tool()
async def read_state(
    Real_time: bool = False,
) -> Optional[Dict[Any, Any]]:
    """
    Read raw digital value from the KY010 sensor.

    Parameters:
    - Real_time: if True, collect all valid data within 10 seconds and return as list.

    Returns:
    A dict with timestamp and raw value, or list of readings if Real_time is True.
    """
    cmd = {"sensor": "KY010", "command": "read_state"}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f'Web Error {response.status_code}'}
    data = response.json()
    id = data.get("id")
    
    if Real_time:
        collected_data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": collected_data, "count": len(collected_data)}
    else:
        return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def is_blocked(
    Real_time: bool = False,
) -> Optional[Dict[Any, Any]]:
    """
    Read blocked status from the KY010 sensor.

    Parameters:
    - Real_time: if True, collect all valid data within 10 seconds and return as list.

    Returns:
    A dict with timestamp and blocked boolean, or list of readings if Real_time is True.
    """
    cmd = {"sensor": "KY010", "command": "is_blocked"}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f'Web Error {response.status_code}'}
    data = response.json()
    id = data.get("id")
    
    if Real_time:
        collected_data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": collected_data, "count": len(collected_data)}
    else:
        return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_all(
    Real_time: bool = False,
) -> Optional[Dict[Any, Any]]:
    """
    Read full report from the KY010 sensor (timestamp, raw, blocked).

    Parameters:
    - Real_time: if True, collect all valid data within 10 seconds and return as list.

    Returns:
    A dict with timestamp, raw, blocked or list of such reports if Real_time is True.
    """
    cmd = {"sensor": "KY010", "command": "read_all"}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f'Web Error {response.status_code}'}
    data = response.json()
    id = data.get("id")
    
    if Real_time:
        collected_data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": collected_data, "count": len(collected_data)}
    else:
        return monitor(DATA_PATH, DATA_FILE, id)

if __name__ == '__main__':
    sess = requests.Session()
    sess.head("http://localhost:8000/send_cmd")
    mcp.run()