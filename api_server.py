#!/usr/bin/env python3
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import psutil
import subprocess
import os
import logging
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Setup request logging
logging.basicConfig(
    filename=os.path.join(os.path.dirname(__file__), 'access.log'),
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

@app.before_request
def log_request():
    logging.info(f"{request.remote_addr} - {request.method} {request.path}")

def read_log_tail(filepath, lines=30):
    try:
        result = subprocess.run(['sudo', 'tail', f'-{lines}', filepath],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip().split('\n')
        else:
            return [f"Error reading log: {result.stderr}"]
    except Exception as e:
        return [f"Error reading log: {str(e)}"]

@app.route('/')
def serve_index():
    return send_from_directory(os.path.dirname(__file__), 'index.html')

# === Page 1: Pi System Stats (Optional but included) ===
@app.route('/api/system')
def api_system():
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = float(f.read()) / 1000.0
    except:
        temp = None

    processes = []
    for proc in sorted(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']),
                      key=lambda p: p.info['cpu_percent'] or 0, reverse=True)[:5]:
        try:
            processes.append({
                'name': proc.info['name'][:20],
                'cpu': round(proc.info['cpu_percent'] or 0, 1),
                'memory': round(proc.info['memory_percent'] or 0, 1)
            })
        except:
            continue

    return {
        'cpu': cpu_percent,
        'memory': {
            'percent': memory.percent,
            'used': round(memory.used / (1024**3), 2),
            'total': round(memory.total / (1024**3), 2)
        },
        'disk': {
            'percent': disk.percent,
            'used': round(disk.used / (1024**3), 2),
            'total': round(disk.total / (1024**3), 2)
        },
        'temperature': temp,
        'processes': processes,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

# === Page 2: ThinkCentre Logs (Most Important) ===
@app.route('/api/thinkcentre')
def api_thinkcentre():
    logs = []
    base_dir = '/var/log/remote/engine-uity'
    if os.path.exists(base_dir):
        # Priority logs: security + critical services
        priority_files = [
            'auth.log', 'sshd.log', 'sudo.log', 'fail2ban-server.log',
            'kernel.log', 'dockerd.log', 'tor.log', 'auditd.log'
        ]
        for filename in priority_files:
            path = os.path.join(base_dir, filename)
            if os.path.exists(path):
                logs.extend(read_log_tail(path, 8))
    return jsonify({'logs': logs[-30:], 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

# === Page 3: Pi Logs (Most Important) ===
@app.route('/api/pi')
def api_pi():
    logs = []
    base_dir = '/var/log/remote/raspberrypi'
    if os.path.exists(base_dir):
        priority_files = [
            'pihole.log', 'Tor.log', 'fail2ban.log', 'auth.log', 'ufw.log'
        ]
        for filename in priority_files:
            path = os.path.join(base_dir, filename)
            if os.path.exists(path):
                logs.extend(read_log_tail(path, 8))
    return jsonify({'logs': logs[-30:], 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

# === Page 4: Switch Logs ===
@app.route('/api/switch')
def api_switch():
    logs = []
    base_dir = '/var/log/remote/switchc73365'
    if os.path.exists(base_dir):
        for filename in sorted(os.listdir(base_dir)):
            if filename.endswith('.log'):
                logs.extend(read_log_tail(os.path.join(base_dir, filename), 5))
    return jsonify({'logs': logs[-30:], 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

# === Page 5: All Logs Browser ===
@app.route('/api/all-logs')
def api_all_logs():
    logs = []
    base_dirs = [
        ('ThinkCentre', '/var/log/remote/engine-uity'),
        ('Pi', '/var/log/remote/raspberrypi'),
        ('Switch', '/var/log/remote/switchc73365')
    ]

    for host, base_dir in base_dirs:
        if os.path.exists(base_dir):
            for filename in sorted(os.listdir(base_dir)):
                if filename.endswith('.log'):
                    filepath = os.path.join(base_dir, filename)
                    try:
                        size = os.path.getsize(filepath)
                        logs.append({
                            'name': f"{host}/{filename}",
                            'path': filepath,
                            'size': f"{size // 1024} KB"
                        })
                    except OSError:
                        continue
    return jsonify({'logs': logs})

# === View Any Log File ===
@app.route('/api/log')
def api_log():
    path = request.args.get('path')
    if not path or not path.startswith('/var/log/remote/'):
        return jsonify({'error': 'Invalid or unsafe path'}), 400

    try:
        lines = read_log_tail(path, 50)
        return jsonify({
            'logs': lines,
            'path': path,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }), 500

# Health check
@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

if __name__ == '__main__':
    print("="*50)
    print("Car Thing API Server Starting...")
    print("="*50)
    app.run(host='0.0.0.0', port=5000, debug=False)
