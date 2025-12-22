#!/usr/bin/env python3
"""
Car Thing Homelab Monitor - API Server
Serves the dashboard HTML and provides system stats/log access
"""

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import psutil
import subprocess
import os
import logging
from datetime import datetime

app = Flask(__name__)
CORS(app)

# =============================================================================
# REQUEST LOGGING
# =============================================================================

logging.basicConfig(
    filename=os.path.join(os.path.dirname(__file__), 'access.log'),
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

@app.before_request
def log_request():
    """Log all API requests for security monitoring"""
    logging.info(f"{request.remote_addr} - {request.method} {request.path}")

# =============================================================================
# CONFIGURATION - Update these paths for your setup
# =============================================================================

SWITCH_LOG_PATH = '/var/log/switch/switch.log'      # Path to your switch logs
UFW_LOG_PATH = '/var/log/ufw.log'                   # Path to UFW firewall logs
SECURITY_SCRIPT = '/home/user/scripts/security.sh'  # Optional: custom security script

# =============================================================================
# SYSTEM STATS
# =============================================================================

def get_system_stats():
    """Gather real-time system statistics"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Get temperature (Raspberry Pi specific)
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = float(f.read()) / 1000.0
    except:
        temp = None
    
    # Get top 5 processes by CPU usage
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
    
    # Get Docker container status
    try:
        docker_output = subprocess.check_output(
            ['docker', 'ps', '--format', '{{.Names}}:{{.Status}}'], 
            text=True, 
            stderr=subprocess.DEVNULL
        )
        containers = []
        for line in docker_output.strip().split('\n'):
            if line:
                name, status = line.split(':', 1)
                containers.append({'name': name, 'status': status})
    except:
        containers = []
    
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
        'containers': containers,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

# =============================================================================
# LOG READING
# =============================================================================

def read_log_tail(filepath, lines=30):
    """Read last N lines from a log file"""
    try:
        result = subprocess.run(
            ['sudo', 'tail', f'-{lines}', filepath], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip().split('\n')
        else:
            return [f"Error reading log: Permission denied"]
    except subprocess.TimeoutExpired:
        return [f"Error reading log: Timeout"]
    except Exception as e:
        return [f"Error reading log: {str(e)}"]

def run_security_monitor():
    """Execute custom security monitoring script"""
    try:
        result = subprocess.run(
            ['bash', SECURITY_SCRIPT], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode == 0:
            output = result.stdout
            return {
                'success': True,
                'output': output,
                'lines': output.split('\n'),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        else:
            return {
                'success': False,
                'error': 'Script execution failed',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Script timeout',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        return {
            'success': False,
            'error': 'Script error',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

# =============================================================================
# ROUTES
# =============================================================================

@app.route('/')
def serve_index():
    """Serve the main dashboard HTML"""
    return send_from_directory(os.path.dirname(__file__), 'index.html')

@app.route('/api/system')
def api_system():
    """System statistics endpoint"""
    return jsonify(get_system_stats())

@app.route('/api/switch')
def api_switch():
    """Switch/network logs endpoint"""
    logs = read_log_tail(SWITCH_LOG_PATH, 30)
    return jsonify({
        'logs': logs,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/security')
def api_security():
    """Firewall logs endpoint"""
    logs = read_log_tail(UFW_LOG_PATH, 30)
    # Filter for BLOCK entries
    block_logs = [line for line in logs if '[UFW BLOCK]' in line]
    return jsonify({
        'logs': block_logs if block_logs else logs,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/security-monitor')
def api_security_monitor():
    """Run full security monitoring script"""
    result = run_security_monitor()
    return jsonify(result)

@app.route('/api/ssh-logs')
def api_ssh_logs():
    """SSH authentication logs from journalctl"""
    try:
        result = subprocess.run(
            ['sudo', 'journalctl', '-u', 'ssh', '--since', '24 hours ago', '-n', '30'], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        logs = result.stdout.strip().split('\n') if result.returncode == 0 else ['Error reading SSH logs']
        return jsonify({
            'logs': logs,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({
            'logs': [f"Error: {str(e)}"],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok', 
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("="*50)
    print("Car Thing API Server Starting...")
    print("="*50)
    print(f"Switch logs: {SWITCH_LOG_PATH}")
    print(f"UFW logs: {UFW_LOG_PATH}")
    print(f"Security script: {SECURITY_SCRIPT}")
    print("="*50)
    print("Server running on http://0.0.0.0:5000")
    print("="*50)
    
    # Run server with debug disabled for security
    app.run(host='0.0.0.0', port=5000, debug=False)
