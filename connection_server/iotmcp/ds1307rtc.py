import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional
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
            if time.time() - start_time > 10.0:
                return "Monitor Timeout"
        except KeyboardInterrupt:
            return None
        except Exception:
            return None

def monitor_realtime(directory: str, filename: str, id: str, max_duration: float = 10.0) -> List[Dict[Any, Any]]:
    file_path = os.path.join(directory, filename)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File dont exist: {file_path}")
    start_time = time.time()
    initial_size = os.path.getsize(file_path)
    collected_data: List[Dict[Any, Any]] = []
    while True:
        try:
            elapsed = time.time() - start_time
            if elapsed > max_duration:
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
    "DS1307RTC",
    description="DS1307RTC I2C RTC module. Supports reading datetime, date, time, SQW status and full report."
)

@mcp.tool()
async def read_datetime(
    Real_time: bool = False
) -> Optional[Any]:
    """
    Read full datetime tuple from DS1307RTC.
    """
    cmd = {"sensor": "DS1307RTC", "command": "read_datetime"}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f"Web Error {response.status_code}"}
    id = response.json().get("id")
    if Real_time:
        data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": data, "count": len(data)}
    else:
        return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_date(
    Real_time: bool = False
) -> Optional[Any]:
    """
    Read date dict from DS1307RTC.
    """
    cmd = {"sensor": "DS1307RTC", "command": "read_date"}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f"Web Error {response.status_code}"}
    id = response.json().get("id")
    if Real_time:
        data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": data, "count": len(data)}
    else:
        return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_time(
    Real_time: bool = False
) -> Optional[Any]:
    """
    Read time dict from DS1307RTC.
    """
    cmd = {"sensor": "DS1307RTC", "command": "read_time"}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f"Web Error {response.status_code}"}
    id = response.json().get("id")
    if Real_time:
        data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": data, "count": len(data)}
    else:
        return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_sqw(
    Real_time: bool = False
) -> Optional[Any]:
    """
    Read SQW pin status from DS1307RTC.
    """
    cmd = {"sensor": "DS1307RTC", "command": "read_sqw"}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f"Web Error {response.status_code}"}
    id = response.json().get("id")
    if Real_time:
        data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": data, "count": len(data)}
    else:
        return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_all(
    Real_time: bool = False
) -> Optional[Any]:
    """
    Read full report from DS1307RTC (datetime, date, time, and SQW).
    """
    cmd = {"sensor": "DS1307RTC", "command": None}
    response = sess.post("http://localhost:8000/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f"Web Error {response.status_code}"}
    id = response.json().get("id")
    if Real_time:
        data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": data, "count": len(data)}
    else:
        return monitor(DATA_PATH, DATA_FILE, id)

@if __name__ == '__main__':
    sess = requests.Session()
    sess.head("http://localhost:8000/send_cmd")
    mcp.run()