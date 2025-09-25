import asyncio
import json
import os
import time
from typing import List, Dict
import requests
import serial
import serial.tools.list_ports
from mcp.server.fastmcp import FastMCP

TCP_HOST = '0.0.0.0'
TCP_PORT = 8000
DATA_PATH = '../data/'
DATA_FILE = 'all.jsonl'

import os
import json
import time
from typing import Generator, Dict, Any, Optional

def monitor(directory: str, filename: str, para: str) -> Optional[Dict[Any, Any]]:
    file_path = os.path.join(directory, filename)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File dont exist: {file_path}")
    
    initial_size = os.path.getsize(file_path)
    
    while True:
        try:
            current_size = os.path.getsize(file_path)
            
            if current_size > initial_size:
                initial_size = current_size
                with open(file_path, 'r', encoding='utf-8') as f:
                    f.seek(initial_size)
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                json_obj = json.loads(line)
                                
                                if para == 'all':
                                    if "temperature" in json_obj:
                                        return json_obj
                                else:
                                    if para in json_obj:
                                        return json_obj
                            except json.JSONDecodeError as e:
                                print(f"JSON Parsing Error: {e}")
                                continue
            
            time.sleep(0.05)
            
        except KeyboardInterrupt:
            return None
        except Exception as e:
            return None

mcp = FastMCP(
    "TMP36",
    description="TMP36 PC data monitoring via MCP. Supports precise temperature reading."
)

@mcp.tool()
async def read_temperature(
    interval: float = 0.0,
    duration: float = 0.0,
) -> List[float]:
    """
    Read temperature values from the TMP36 analog temperature sensor.

    Parameters:
    - interval: time between readings in seconds. Default 0.0 returns a single reading.
    - duration: total duration in seconds for continuous readings (0.0 => single reading;
      >0.0 => readings over duration; <0.0 => continuous until stopped).

    Returns:
    A temperature with time stamp.
    """
    cmd = {"sensor": "TMP36","command": "read_temp", "interval": interval, "duration": duration}
    requests.post("http://localhost:8000/send_cmd", json=cmd)
    
    return monitor(DATA_PATH,DATA_FILE,"temperature")


if __name__ == '__main__':
    mcp.run()