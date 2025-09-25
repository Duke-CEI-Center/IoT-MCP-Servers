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
            if(time.time() - start_time > 10.0):
                return "Monitor Timeout"
            
        except KeyboardInterrupt:
            return None
        except Exception as e:
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
    "KY020",
    description="KY-020 tilt switch sensor monitoring via MCP. Supports raw digital reading and tilted state."
)

@mcp.tool()
async def read_raw(
    Real_time: bool = False,
) -> Optional[Dict[Any, Any]]:
    """
    Read raw digital value (0 or 1) from the KY-020 tilt switch.

    Parameters:
    - Real_time: if True, collect all valid data within 10 seconds and return as list.

    Returns:
    Raw digital reading with timestamp, or list of readings if Real_time is True.
    """
    cmd = {"sensor": "KY020", "command": "read_raw"}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f'Web Error {response.status_code}'}
    data = response.json()
    id = data.get("id")
    
    if Real_time:
        collected = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": collected, "count": len(collected or [])}
    else:
        return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_tilted(
    Real_time: bool = False,
) -> Optional[Dict[Any, Any]]:
    """
    Read tilted state (True if tilted) from the KY-020 tilt switch.

    Parameters:
    - Real_time: if True, collect all valid data within 10 seconds and return as list.

    Returns:
    Tilted state with timestamp, or list of readings if Real_time is True.
    """
    cmd = {"sensor": "KY020", "command": "read_tilted"}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f'Web Error {response.status_code}'}
    data = response.json()
    id = data.get("id")
    
    if Real_time:
        collected = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": collected, "count": len(collected or [])}
    else:
        return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_all(
    Real_time: bool = False,
) -> Optional[Dict[Any, Any]]:
    """
    Read both raw digital value and tilted state from the KY-020 tilt switch.

    Parameters:
    - Real_time: if True, collect all valid data within 10 seconds and return as list.

    Returns:
    JSON with raw and tilted fields plus timestamp, or list of readings if Real_time is True.
    """
    cmd = {"sensor": "KY020", "command": "read_all"}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f'Web Error {response.status_code}'}
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