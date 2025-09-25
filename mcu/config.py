"""
config.py

Utility module for detecting the current network environment and injecting
Wi-Fi credentials and network settings into the main application.

Functions:
  - _get_ssid_windows():   Retrieve the active Wi-Fi SSID on Windows.
  - _get_ssid_linux():     Retrieve the active Wi-Fi SSID on Linux (via nmcli or iwgetid).
  - _get_ssid_mac():       Retrieve the active Wi-Fi SSID on macOS (using the airport tool).
  - get_local_ip():        Determine the local IPv4 address by creating a UDP socket.
  - get_wifi_password():   Fetch the saved Wi-Fi password for a given SSID (supports Windows, macOS, and Linux).
  - get_network_info():    Aggregate SSID, local IP, and password into a dictionary.

When run as a script, this module will:
  1. Query the current network SSID, local IP, and Wi-Fi password.
  2. Read main.py and replace placeholder values for SSID, PASSWORD, SERVER_IP, and PORT.
  3. Write the updated configuration back to main.py.
"""

import platform, subprocess, re, socket

# Set your desired port here
port = 9000

# Get current Wi-Fi SSID on Windows

def _get_ssid_windows():
    output = subprocess.check_output(["netsh", "wlan", "show", "interfaces"], encoding="utf-8")
    m = re.search(r"^\s*SSID\s*:\s*(.+)$", output, re.MULTILINE)
    return m.group(1).strip() if m else None

# Get SSID on Linux

def _get_ssid_linux():
    try:
        output = subprocess.check_output(["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"], encoding="utf-8")
        for line in output.splitlines():
            active, ssid = line.split(':', 1)
            if active == 'yes':
                return ssid
    except Exception:
        pass
    try:
        return subprocess.check_output(["iwgetid", "-r"], encoding="utf-8").strip() or None
    except Exception:
        return None

# Get SSID on macOS

def _get_ssid_mac():
    airport = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
    try:
        output = subprocess.check_output([airport, '-I'], encoding='utf-8')
        m = re.search(r"^\s*SSID:\s*(.+)$", output, re.MULTILINE)
        return m.group(1).strip() if m else None
    except Exception:
        return None

# Get local IPv4 address

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except Exception:
        return socket.gethostbyname(socket.gethostname())
    finally:
        s.close()

# Get Wi-Fi password for SSID

def get_wifi_password(ssid):
    system = platform.system()
    if system == 'Windows':
        try:
            output = subprocess.check_output(
                ['netsh', 'wlan', 'show', 'profile', f'name={ssid}', 'key=clear'],
                encoding='utf-8', errors='ignore'
            )
            m = re.search(r"Key Content\s*:\s*(.+)", output)
            return m.group(1).strip() if m else None
        except subprocess.CalledProcessError:
            return None
    elif system == 'Darwin':
        try:
            return subprocess.check_output(
                ['security', 'find-generic-password', '-D', 'AirPort network password', '-a', ssid, '-w'],
                encoding='utf-8'
            ).strip() or None
        except subprocess.CalledProcessError:
            return None
    else:
        try:
            pwd = subprocess.check_output(
                ['nmcli', '-s', '-g', '802-11-wireless-security.psk', 'connection', 'show', ssid],
                encoding='utf-8'
            ).strip()
            return pwd or None
        except subprocess.CalledProcessError:
            # Fallback to reading NM connection file (may require sudo)
            path = f"/etc/NetworkManager/system-connections/{ssid}.nmconnection"
            try:
                with open(path) as f:
                    for line in f:
                        if line.strip().startswith('psk='):
                            return line.strip().split('=',1)[1]
            except Exception:
                pass
        return None

# Compose network info dictionary

def get_network_info():
    system = platform.system()
    if system == 'Windows':
        ssid = _get_ssid_windows()
    elif system == 'Darwin':
        ssid = _get_ssid_mac()
    else:
        ssid = _get_ssid_linux()

    ip = get_local_ip()
    pwd = get_wifi_password(ssid) if ssid else None

    return {
        'network_name': ssid or 'Unknown',
        'local_ipv4': ip,
        'wifi_password': pwd or 'Unavailable'
    }

# Main: update main.py
if __name__ == '__main__':
    info = get_network_info()
    network_name = info['network_name']
    server_ipv4 = info['local_ipv4']
    wifi_password = info['wifi_password'] if info['wifi_password'] != "Unavailable"  else ""

    # 1. Read main.py
    with open("main.py", "r", encoding="utf-8") as f:
        content = f.read()

    # 2. Use regex to replace the four placeholder variables

    content = re.sub(
        r'SSID\s*=\s*".*?"',
        f'SSID = "{network_name}"',
        content
    )
    content = re.sub(
        r'PASSWORD\s*=\s*".*?"',
        f'PASSWORD = "{wifi_password}"',
        content
    )
    content = re.sub(
        r'SERVER_IP\s*=\s*".*?"',
        f'SERVER_IP = "{server_ipv4}"',
        content
    )
    content = re.sub(
        r'PORT\s*=\s*".*?"',
        f'PORT = "{port}"',
        content
    )

    # 3. Write the updated content back to main.py
    with open("main.py", "w", encoding="utf-8") as f:
        f.write(content)

    print("SSID, PASSWORD, SERVER_IP and PORT have been updated in main.py")


