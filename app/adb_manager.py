import subprocess
import os
import shutil
import logging
import re
import json
from typing import List, Dict, Optional, Tuple, Any
from app.config import ADB_PATH, ADB_TIMEOUT_SECONDS

logger = logging.getLogger("adb_manager")
logger.setLevel(logging.INFO)

class ADBManager:
    def __init__(self, custom_adb_path: Optional[str] = None):
        self.adb_bin = self._resolve_adb_path(custom_adb_path or ADB_PATH)
        self.selected_device: Optional[str] = None

    def _resolve_adb_path(self, path_candidate: str) -> str:
        if path_candidate and os.path.isfile(path_candidate):
            return os.path.abspath(path_candidate)
        found = shutil.which(path_candidate)
        if found:
            return found
        found_in_path = shutil.which("adb")
        if found_in_path:
            return found_in_path
        return path_candidate

    def execute_command(self, args: List[str], timeout: Optional[int] = None, use_device_flag: bool = True) -> Tuple[int, str, str]:
        cmd = [self.adb_bin]
        if use_device_flag and self.selected_device and (not args or args[0] not in ["devices", "version", "start-server", "kill-server", "pair", "connect", "disconnect", "mdns"]):
            cmd.extend(["-s", self.selected_device])
        cmd.extend(args)
        
        timeout_val = timeout or ADB_TIMEOUT_SECONDS
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_val,
                shell=False
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", f"ADB Command timed out after {timeout_val}s: {' '.join(cmd)}"
        except FileNotFoundError:
            return -1, "", f"ADB executable not found at '{self.adb_bin}'"
        except Exception as e:
            return -1, "", str(e)

    def get_version(self) -> str:
        code, out, err = self.execute_command(["version"], use_device_flag=False)
        if code == 0:
            return out
        return f"Error: {err}"

    def get_devices(self) -> List[Dict[str, str]]:
        # Use adb devices -l to capture detailed model/product attributes
        code, out, err = self.execute_command(["devices", "-l"], use_device_flag=False)
        devices = []
        if code != 0:
            return devices
        lines = out.splitlines()
        for line in lines[1:]:
            parts = line.strip().split()
            if len(parts) >= 2:
                serial, state = parts[0], parts[1]
                conn_type = "wireless" if ":" in serial else "usb"
                
                # Parse additional properties like model:XYZ
                model_name = None
                for p in parts[2:]:
                    if p.startswith("model:"):
                        model_name = p.split(":", 1)[1]
                        break

                devices.append({
                    "serial": serial,
                    "state": state,
                    "type": conn_type,
                    "model": model_name
                })
        return devices

    def set_selected_device(self, serial: str) -> bool:
        self.selected_device = serial if serial else None
        return True

    def check_connection_status(self) -> Dict[str, Any]:
        devices = self.get_devices()
        if not devices:
            self.selected_device = None
            return {
                "connected": False,
                "status": "No Android device connected. Connect via USB or pair/connect using Wireless ADB.",
                "model": None,
                "serial": None,
                "connection_type": "unknown",
                "available_devices": []
            }

        # If a device was previously selected, see if it is still present and ready
        active_device = None
        if self.selected_device:
            for d in devices:
                if d["serial"] == self.selected_device:
                    active_device = d
                    break

        # If selected device is not set or not online, auto-select the first online 'device'
        if not active_device or active_device["state"] != "device":
            for d in devices:
                if d["state"] == "device":
                    active_device = d
                    self.selected_device = d["serial"]
                    break

        # If no online device, default to first available
        if not active_device:
            active_device = devices[0]
            self.selected_device = active_device["serial"]

        # Check states
        if active_device["state"] == "unauthorized":
            return {
                "connected": False,
                "status": f"Device {active_device['serial']} unauthorized. Accept USB/Wireless prompt on phone.",
                "model": active_device.get("model"),
                "serial": active_device["serial"],
                "connection_type": active_device["type"],
                "available_devices": devices
            }
        elif active_device["state"] == "offline":
            return {
                "connected": False,
                "status": f"Device {active_device['serial']} is offline. Check Wi-Fi or reconnect.",
                "model": active_device.get("model"),
                "serial": active_device["serial"],
                "connection_type": active_device["type"],
                "available_devices": devices
            }
        elif active_device["state"] == "device":
            model = active_device.get("model") or self.get_device_model()
            return {
                "connected": True,
                "status": "Connected",
                "model": model,
                "serial": active_device["serial"],
                "connection_type": active_device["type"],
                "available_devices": devices
            }

        return {
            "connected": False,
            "status": f"Device {active_device['serial']} state: {active_device['state']}",
            "model": active_device.get("model"),
            "serial": active_device["serial"],
            "connection_type": active_device["type"],
            "available_devices": devices
        }

    def pair_device(self, ip: str, port: int, code: str) -> Tuple[bool, str]:
        """
        Executes: adb pair IP:PORT PAIRING_CODE
        If an ADB device with this IP is already connected, avoid redundant pairing.
        """
        ip = ip.strip()
        code = str(code).strip()
        target = f"{ip}:{port}"
        
        # Check if already connected on this IP
        devices = self.get_devices()
        for d in devices:
            if d["state"] == "device" and (d["serial"] == target or d["serial"].startswith(f"{ip}:")):
                self.selected_device = d["serial"]
                return True, f"Device {d['serial']} is already connected and ready."

        logger.info(f"Pairing with {target}...")
        returncode, out, err = self.execute_command(["pair", target, code], timeout=25, use_device_flag=False)
        output = (out + "\n" + err).strip()
        
        if returncode == 0 and ("successfully paired" in output.lower() or "already paired" in output.lower()):
            return True, output or f"Successfully paired to {target}"
        
        if "failed" in output.lower() or "error" in output.lower():
            return False, output or "Pairing failed. Please check IP, port, and code."
        
        if returncode == 0:
            return True, output or "Pair command finished successfully."
            
        return False, output or f"Pairing returned code {returncode}"

    def get_mdns_services(self) -> List[Dict[str, str]]:
        code, out, _ = self.execute_command(["mdns", "services"], timeout=10, use_device_flag=False)
        services = []
        if code != 0 or not out:
            return services
        for line in out.splitlines():
            line = line.strip()
            if not line or line.startswith("List of"):
                continue
            parts = line.split()
            if len(parts) >= 3:
                name, s_type, address = parts[0], parts[1], parts[2]
                services.append({"name": name, "type": s_type, "address": address})
        return services

    def parse_qr_payload(self, raw_payload: str, fallback_ip: Optional[str] = None) -> Dict[str, Any]:
        payload = raw_payload.strip()

        # Format 1: WIFI:T:ADB;S:...;P:...;;
        if payload.startswith("WIFI:T:ADB;") or "T:ADB;" in payload:
            s_match = re.search(r"[;:]S:([^;]+);", payload)
            p_match = re.search(r"[;:]P:([^;]+);", payload)
            service_name = s_match.group(1) if s_match else None
            password = p_match.group(1) if p_match else None
            
            ip = fallback_ip
            port = None
            if service_name:
                mdns_list = self.get_mdns_services()
                for s in mdns_list:
                    if service_name in s["name"] or s["name"] in service_name:
                        if ":" in s["address"]:
                            addr_ip, addr_port = s["address"].split(":", 1)
                            ip = addr_ip
                            port = int(addr_port)
                            break

            return {
                "type": "android_wifi_adb",
                "service_name": service_name,
                "password": password,
                "ip": ip,
                "port": port
            }

        # Format 4: JSON payload
        if payload.startswith("{") and payload.endswith("}"):
            try:
                data = json.loads(payload)
                return {
                    "type": "json",
                    "ip": data.get("ip") or fallback_ip,
                    "port": int(data.get("port") or data.get("pair_port") or 0) or None,
                    "password": str(data.get("code") or data.get("password") or ""),
                    "connect_port": int(data.get("connect_port") or 0) or None
                }
            except Exception:
                pass

        # Format 3: adb://IP:PORT?code=...
        url_match = re.match(r"adb://([^:/]+):(\d+)(?:\?.*code=([^&]+))?", payload)
        if url_match:
            return {
                "type": "adb_url",
                "ip": url_match.group(1),
                "port": int(url_match.group(2)),
                "password": url_match.group(3) or ""
            }

        # Format 2: IP:PORT:CODE or IP:PORT
        tokens = payload.split(":")
        if len(tokens) >= 3 and tokens[1].isdigit():
            return {
                "type": "colon_separated",
                "ip": tokens[0].strip(),
                "port": int(tokens[1]),
                "password": tokens[2].strip()
            }
        elif len(tokens) == 2 and tokens[1].isdigit():
            return {
                "type": "ip_port_only",
                "ip": tokens[0].strip(),
                "port": int(tokens[1]),
                "password": None
            }

        return {
            "type": "raw",
            "raw": payload,
            "ip": fallback_ip,
            "port": None,
            "password": None
        }

    def pair_with_qr(self, raw_payload: str, fallback_ip: Optional[str] = None) -> Tuple[bool, str, Optional[str], Optional[int]]:
        parsed = self.parse_qr_payload(raw_payload, fallback_ip)
        password = parsed.get("password")
        ip = parsed.get("ip") or fallback_ip
        port = parsed.get("port")
        service_name = parsed.get("service_name")

        if not ip or not port:
            mdns_services = self.get_mdns_services()
            for s in mdns_services:
                if "_adb-tls-pairing._tcp" in s["type"] or (service_name and service_name in s["name"]):
                    if ":" in s["address"]:
                        addr_ip, addr_port = s["address"].split(":", 1)
                        ip = ip or addr_ip
                        port = int(addr_port)
                        break

            if not ip:
                for s in mdns_services:
                    if ":" in s["address"]:
                        ip = s["address"].split(":")[0]
                        break

        if not ip or not port or not password:
            missing = []
            if not ip: missing.append("Phone IP")
            if not port: missing.append("Pairing Port")
            if not password: missing.append("Pairing Password")
            
            msg = f"QR Code parsed ({parsed.get('type')}), but missing: {', '.join(missing)}. "
            if service_name and not port:
                msg += f"Phone mDNS service '{service_name}' not discovered yet. Ensure phone & PC are on the same Wi-Fi/Hotspot."
            return False, msg, ip, port

        success, message = self.pair_device(ip, port, password)
        return success, message, ip, port

    def connect_device(self, ip: str, port: int) -> Tuple[bool, str]:
        ip = ip.strip()
        target = f"{ip}:{port}"
        
        # Check if already connected
        devices = self.get_devices()
        for d in devices:
            if d["serial"] == target and d["state"] == "device":
                self.selected_device = target
                return True, f"Device {target} is already connected."

        logger.info(f"Connecting to {target}...")
        returncode, out, err = self.execute_command(["connect", target], timeout=20, use_device_flag=False)
        output = (out + "\n" + err).strip()
        
        if "connected to" in output.lower() and "cannot" not in output.lower() and "failed" not in output.lower():
            self.selected_device = target
            return True, output or f"Connected to {target}"
        
        if "already connected to" in output.lower():
            self.selected_device = target
            return True, output or f"Already connected to {target}"
            
        return False, output or f"Failed to connect to {target}. Check connection port."

    def disconnect_device(self, target: Optional[str] = None) -> Tuple[bool, str]:
        args = ["disconnect"]
        if target:
            args.append(target.strip())
        elif self.selected_device and ":" in self.selected_device:
            args.append(self.selected_device)
            
        returncode, out, err = self.execute_command(args, timeout=15, use_device_flag=False)
        output = (out + "\n" + err).strip()
        
        if target and self.selected_device == target:
            self.selected_device = None
        elif not target:
            self.selected_device = None
            
        return returncode == 0, output or "Disconnected"

    def get_device_model(self) -> str:
        code, out, _ = self.execute_command(["shell", "getprop", "ro.product.model"])
        if code == 0 and out:
            return out
        return "Unknown Model"

    def get_current_app(self) -> str:
        code, out, _ = self.execute_command(["shell", "dumpsys", "activity", "activities"])
        if code == 0:
            for line in out.splitlines():
                if "mResumedActivity" in line or "topResumedActivity" in line:
                    return line.strip()
        code2, out2, _ = self.execute_command(["shell", "dumpsys", "window", "windows"])
        if code2 == 0:
            for line in out2.splitlines():
                if "mCurrentFocus" in line:
                    return line.strip()
        return "Unknown"

    def get_screen_size(self) -> Tuple[int, int]:
        code, out, _ = self.execute_command(["shell", "wm", "size"])
        if code == 0 and out:
            # Physical size: 1080x2400 or Override size: ...
            match = re.search(r"(\d+)x(\d+)", out)
            if match:
                return int(match.group(1)), int(match.group(2))
        return 1080, 2400

    def tap(self, x: int, y: int) -> bool:
        code, _, _ = self.execute_command(["shell", "input", "tap", str(x), str(y)])
        return code == 0

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        code, _, _ = self.execute_command(["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)])
        return code == 0

    def type_text(self, text: str) -> bool:
        escaped = text.replace(" ", "%s")
        for char in ['"', "'", "&", "|", ";", "$", "`", "<", ">", "\\", "(", ")"]:
            escaped = escaped.replace(char, f"\\{char}")
        code, _, _ = self.execute_command(["shell", "input", "text", escaped])
        return code == 0

    def keyevent(self, keycode: int) -> bool:
        code, _, _ = self.execute_command(["shell", "input", "keyevent", str(keycode)])
        return code == 0

    def press_enter(self) -> bool:
        # 66 = KEYCODE_ENTER
        return self.keyevent(66)

    def open_app(self, package_name: str) -> bool:
        code, _, _ = self.execute_command([
            "shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"
        ])
        return code == 0

    def take_screenshot(self, local_path: str) -> bool:
        remote_path = "/sdcard/screen_temp.png"
        code, _, _ = self.execute_command(["shell", "screencap", "-p", remote_path])
        if code != 0:
            return False
        code, _, _ = self.execute_command(["pull", remote_path, local_path])
        self.execute_command(["shell", "rm", remote_path])
        return code == 0

    def dump_hierarchy(self, local_path: str) -> bool:
        remote_path = "/sdcard/window_dump.xml"
        code, _, _ = self.execute_command(["shell", "uiautomator", "dump", remote_path])
        if code != 0:
            # Retry once after short sleep in case device was animating
            import time
            time.sleep(0.5)
            code, _, _ = self.execute_command(["shell", "uiautomator", "dump", remote_path])
            if code != 0:
                return False
        code, _, _ = self.execute_command(["pull", remote_path, local_path])
        self.execute_command(["shell", "rm", remote_path])
        return code == 0
