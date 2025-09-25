import requests, argparse
from datetime import datetime
import time
import asyncio


DEFAULT_SENSOR = "KY035"
DEFAULT_COMMAND = "read_all"
DEFAULT_INTERVAL = 0
DEFAULT_DURATION = 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="None")
    parser.add_argument("--sensor", type=str, default=DEFAULT_SENSOR, help="")
    parser.add_argument("--command", default=DEFAULT_COMMAND,
                        choices=["read_temp", "read_accel", "read_gyro", "read_tilt", "read_all"],help="")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="")
    parser.add_argument("--duration", type=float, default=DEFAULT_DURATION, help="")

    args = parser.parse_args()

    KY035 = {
        "sensor": "KY035",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }

    MPU6050 = {
        "sensor": "MPU6050",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }
    DHT11 = {
        "sensor": "DHT11",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }
    DS18X20 = {
        "sensor": "DS18X20",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }
    cmd5 = {
        "sensor": "KY026",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }
    LM35 = {
        "sensor": "LM35",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }
    CMD = {
        "start": "2025-06-30 15:47:30",
        "end": "2025-06-30 15:47:40",
        "interval": 1,
        "request":KY035,
    }



    cmd7 = {
        "sensor": "KY038",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }

    cmd8 = {
        "sensor": "KY021",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }

    cmd9 = {
        "sensor": "KY023",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }

    cmd10 = {
        "sensor": "KY037",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }

    KY020 = {
        "sensor": "KY020",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }

    KY004 = {
        "sensor": "KY004",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }

    cmd13 = {
        "sensor": "HC_SR04",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }


    cmd14 = {
        "sensor": "KY010",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }



    cmd15 = {
        "sensor": "KY036",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }

    cmd16 = {
        "sensor": "SW420",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }

    GY302 = {
        "sensor": "GY302",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }

    WaterSensor = {
        "sensor": "WaterSensor",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }

    KY018 = {
        "sensor": "KY018",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }

    TTP223 = {
        "sensor": "TTP223",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }

    HC_SR501 = {
        "sensor": "HC_SR501",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }

    LTR390 = {
        "sensor": "LTR390",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }

    HW080 = {
        "sensor": "HW080",
        "command": args.command,
        "interval": args.interval,
        "duration": args.duration
    }
    
    sess = requests.Session()
    sess.head("http://localhost:8000/send_cmd")
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=KY035)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=MPU6050)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=DHT11)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=DS18X20)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=cmd5)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=LM35)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=cmd7)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=cmd8)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=cmd9)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=cmd10)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=KY020)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=KY004)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=cmd13)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=cmd14)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=cmd15)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=cmd16)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=GY302)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=WaterSensor)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=KY018)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=TTP223)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=HC_SR501)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=HW080)
    print(response.text)
    time.sleep(1)
    print(datetime.now())
    response = sess.post("http://localhost:8000/send_cmd", json=LTR390)
    print(response.text)


    #response3 = sess.post("http://localhost:8000/send_cmd", json=cmds3)

    #print(response3.text)