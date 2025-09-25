import asyncio
import json
import os
import time
from typing import Dict, Any, Optional, List
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
                        if not line:
                            continue
                        try:
                            json_obj = json.loads(line)
                            if json_obj.get("id") == id:
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
    collected: List[Dict[Any, Any]] = []
    while True:
        try:
            if time.time() - start_time > max_duration:
                break
            current_size = os.path.getsize(file_path)
            if current_size > initial_size:
                with open(file_path, 'r', encoding='utf-8') as f:
                    f.seek(initial_size)
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            json_obj = json.loads(line)
                            if json_obj.get("id") == id:
                                collected.append(json_obj)
                        except json.JSONDecodeError:
                            continue
                initial_size = current_size
            time.sleep(0.05)
        except KeyboardInterrupt:
            break
        except Exception:
            break
    return collected

mcp = FastMCP(
    "NRF24L01P",
    description="nRF24L01+ diagnostics and payload via MCP. Supports status, config, payload, and full report."
)

@mcp.tool()
async def read_status(
    Real_time: bool = False,
) -> Optional[Any]:
    """
    Read STATUS register value from NRF24L01+.
    """
    cmd = {"sensor": "NRF24L01P", "command": "read_status"}
    response = sess.post(f"http://localhost:{TCP_PORT}/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f'Web Error {response.status_code}'}
    id = response.json().get("id")
    if Real_time:
        data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": data, "count": len(data)}
    return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_config(
    Real_time: bool = False,
) -> Optional[Any]:
    """
    Read CONFIG, RF_SETUP, EN_AA registers from NRF24L01+.
    """
    cmd = {"sensor": "NRF24L01P", "command": "read_config"}
    response = sess.post(f"http://localhost:{TCP_PORT}/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f'Web Error {response.status_code}'}
    id = response.json().get("id")
    if Real_time:
        data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": data, "count": len(data)}
    return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_payload(
    Real_time: bool = False,
) -> Optional[Any]:
    """
    Read next RX payload from NRF24L01+ (hex string or None).
    """
    cmd = {"sensor": "NRF24L01P", "command": "rx_payload"}
    response = sess.post(f"http://localhost:{TCP_PORT}/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f'Web Error {response.status_code}'}
    id = response.json().get("id")
    if Real_time:
        data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": data, "count": len(data)}
    return monitor(DATA_PATH, DATA_FILE, id)

@mcp.tool()
async def read_all(
    Real_time: bool = False,
) -> Optional[Any]:
    """
    Get full diagnostic report: status, config, rf_setup, rx_empty.
    """
    cmd = {"sensor": "NRF24L01P", "command": "read_all"}
    response = sess.post(f"http://localhost:{TCP_PORT}/send_cmd", json=cmd)
    if response.status_code != 200:
        return {"status": f'Web Error {response.status_code}'}
    id = response.json().get("id")
    if Real_time:
        data = monitor_realtime(DATA_PATH, DATA_FILE, id)
        return {"status": "success", "data": data, "count": len(data)}
    return monitor(DATA_PATH, DATA_FILE, id)

if __name__ == '__main__':
    sess = requests.Session()
    sess.head(f"http://localhost:{TCP_PORT}/send_cmd")
    mcp.run()