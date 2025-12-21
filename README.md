# Car Thing Homelab Monitor

Turn your discontinued Spotify Car Thing into a live monitoring dashboard for your homelab. No cloud services, no subscriptions—just a USB cable and some Python.

## What This Does

Your Car Thing becomes a 4-page monitoring display showing:
- **System Stats** - CPU, RAM, disk usage, temperature, top processes
- **Network Logs** - Live switch/router logs
- **Firewall Activity** - Blocked connections and security events  
- **Custom Scripts** - Run security audits or any bash script on-demand

Everything updates in real-time. The Car Thing connects directly to your Pi via USB—no network configuration needed.

## Why I Built This

I had a Car Thing collecting dust after Spotify bricked it. I wanted a dedicated display for my homelab but didn't want to waste a full Pi or monitor. Turns out the Car Thing is just a tiny Linux computer with a nice screen—perfect for this.

## Hardware You'll Need

- **Spotify Car Thing** - [How to get one](https://www.ebay.com/sch/i.html?_nkw=spotify+car+thing)
- **Raspberry Pi** (any model with USB-A ports)
- **USB-C cable** - Must support data, not just charging
- **5 minutes** for initial setup

## Software Prerequisites

Your Car Thing needs custom firmware with ADB enabled. I used:
- [superbird-tool](https://github.com/Car-Thing-Hax-Community/superbird-tool) for flashing
- [ThingLabs firmware](https://thingify.tools/) (or any ADB-enabled variant)

If your Car Thing still shows the Spotify interface, you'll need to flash it first. There are good guides in the [Car Thing Hax Community Discord](https://discord.com/invite/car-thing-hax-community-1042954149786046604).

## Quick Start

### 1. Set Up the Flask Server

Access your Pi and set up the API server:

```bash
# Create project directory
mkdir ~/carthing-monitor && cd ~/carthing-monitor

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install flask flask-cors psutil
```

Create `api_server.py` (see [api_server.py](#api_serverpy) below).

### 2. Configure Your Logs

Edit `api_server.py` and update these paths to match your setup:

```python
SWITCH_LOG_PATH = '/var/log/switch/switch.log'      # Your switch logs
UFW_LOG_PATH = '/var/log/ufw.log'                   # Firewall logs
SECURITY_SCRIPT = '/home/user/scripts/security.sh'  # Optional custom script
```

### 3. Grant Sudo Permissions

The API needs to read logs and run scripts:

```bash
sudo visudo -f /etc/sudoers.d/carthing-api
```

Add these lines (replace `username` with your actual user):

```
username ALL=(ALL) NOPASSWD: /usr/bin/tail
username ALL=(ALL) NOPASSWD: /usr/bin/journalctl
username ALL=(ALL) NOPASSWD: /home/username/scripts/security.sh
```

### 4. Test the Server

```bash
python3 api_server.py
```

Open a browser to `http://your-pi-ip:5000/api/system` - you should see JSON with system stats.

### 5. Make It Auto-Start

Create a systemd service:

```bash
sudo nano /etc/systemd/system/carthing-api.service
```

Paste this (update paths for your username):

```ini
[Unit]
Description=Car Thing API Server
After=network.target

[Service]
Type=simple
User=username
WorkingDirectory=/home/username/carthing-monitor
ExecStart=/home/username/carthing-monitor/venv/bin/python /home/username/carthing-monitor/api_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable carthing-api
sudo systemctl start carthing-api
sudo systemctl status carthing-api  # Should show "active (running)"
```

### 6. Open Firewall Port

```bash
sudo ufw allow 5000/tcp comment 'Car Thing API'
sudo ufw reload
```

### 7. Push Dashboard to Car Thing

On your computer (with ADB installed):

1. Download `index.html` from this repo
2. Edit line 238 - change `PI_IP` to your Pi's IP address
3. Push to Car Thing:

```bash
# Connect Car Thing via USB
adb devices

# Mount filesystem as writable
adb shell mount -o remount,rw /

# Backup original (optional)
adb shell mv /usr/share/qt-superbird-app/webapp /usr/share/qt-superbird-app/webapp-backup

# Create directory
adb shell mkdir -p /usr/share/qt-superbird-app/webapp

# Push dashboard
adb push index.html /usr/share/qt-superbird-app/webapp/index.html

# Reboot
adb shell reboot
```

Wait 30 seconds for it to reboot. You should see the orange dashboard!

## Button Layout

The Car Thing has 4 physical buttons:

```
[1] [2]
[3] [4]
```

- **Button 1** → System Monitor (CPU, RAM, disk, processes)
- **Button 2** → Network/Switch Logs
- **Button 3** → Firewall Activity
- **Button 4** → Full Security Scan (runs your custom script)

## File Structure

```
carthing-monitor/
├── api_server.py       # Flask backend serving stats and logs
├── index.html          # Dashboard UI (pushed to Car Thing)
└── venv/              # Python virtual environment
```

## Customization

### Change Refresh Rates

Edit `index.html` around line 420:

```javascript
setInterval(updateSystemStats, 2000);    // Change to 5000 for 5 seconds
setInterval(updateSwitchLogs, 3000);     // etc.
```

### Add More Pages

The dashboard supports up to 4 pages. To add a new page:

1. Add a new `<div class="page">` section in `index.html`
2. Add the page name to the `pages` array in JavaScript
3. Create a new API endpoint in `api_server.py`
4. Add update function in JavaScript

### Different Color Schemes

Search for `#ff8800` in `index.html` and replace with your color:
- Green: `#00ff00`
- Blue: `#00ccff`
- Red: `#ff0000`
- Purple: `#cc00ff`

## Troubleshooting

**Car Thing shows "Cannot connect to Pi"**
- Check API is running: `sudo systemctl status carthing-api`
- Verify firewall: `sudo ufw status | grep 5000`
- Test API: `curl http://localhost:5000/api/system`

**Button presses do nothing**
- The Car Thing maps physical buttons to keys 1-4
- If your firmware is different, you might need to remap in the JavaScript

**Logs not showing**
- Verify log paths exist: `ls -la /var/log/switch/`
- Check sudo permissions: `sudo -l`
- Look at API logs: `sudo journalctl -u carthing-api -f`

**Temperature shows "N/A"**
- Only works on Raspberry Pi with thermal sensors
- Other SBCs might use different paths

## API Endpoints

The Flask server exposes these endpoints:

```
GET /api/system          # CPU, RAM, disk, temp, processes
GET /api/switch          # Network switch logs (last 30 lines)
GET /api/security        # UFW firewall blocks
GET /api/security-monitor # Runs custom security script
GET /health              # Health check
```

## Security Notes

- The API runs on port 5000 without authentication
- **Only expose this on a trusted LAN**
- Don't forward port 5000 to the internet
- Consider adding basic auth if you're paranoid

## Future Ideas

Things I might add:
- Docker container monitoring
- Plex active streams
- Network speed graphs
- Multiple Pi support (switch between hosts)
- Historical data / graphs

Pull requests welcome if you implement any of these!

## Credits

- [Car Thing Hax Community](https://discord.com/invite/car-thing-hax-community-1042954149786046604) for reverse-engineering the hardware
- [superbird-tool](https://github.com/Car-Thing-Hax-Community/superbird-tool) for making flashing easy
- Everyone who refused to let Spotify brick their hardware

## License

MIT License - do whatever you want with this code.

---

Built because I had a Car Thing and too much free time. Hope it's useful!

If you build one, I'd love to see it - open an issue with photos!
