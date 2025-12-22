# Car Thing Homelab Monitor

Turn your discontinued Spotify Car Thing into a live monitoring dashboard for your homelab. No cloud services, no subscriptions—just a USB cable and some Python.

## Features
- Real-time CPU, memory, disk, and temperature stats
- Live system logs (e.g., network switch, UFW firewall)
- One-click security scan (runs custom script)
- Fully offline — no cloud, no Wi-Fi needed
- Zero flashing after setup — edit HTML on Pi, refresh Car Thing

## How This Works
- Flask server on your Pi serves both the API endpoints AND the HTML dashboard
- Car Thing has a tiny redirect.html file that points to your Pi's IP
- When plugged into the Pi via USB, the Car Thing gets network access through USB Ethernet (RNDIS)
- Car Thing loads the dashboard from your Pi over the network
- No re-flashing needed after initial setup - just edit index.html on the Pi and refresh

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

The Flask server serves BOTH the API endpoints AND the HTML dashboard at the root / route.

### 2. Configure Your Logs

Edit `api_server.py` and update these paths to match your setup:

```python
SWITCH_LOG_PATH = '/var/log/switch/switch.log'      # Your switch logs
UFW_LOG_PATH = '/var/log/ufw.log'                   # Firewall logs
SECURITY_SCRIPT = '/home/user/scripts/security.sh'  # Optional custom script
```
OR whatever logs you choose to integrate.

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

### 5. Configure Firewall

The Car Thing connects via USB creating a network
```bash
sudo ufw allow from 192.168.x.x/24 to any port 5000 proto tcp
sudo ufw reload
```

### 6. Push Dashboard to Car Thing

The Car Thing only needs a tiny redirect file that points to your Pi:

Edit `redirect.html` with your actual Pi IP address.

Push to Car Thing:

```bash
#Connect carthing via USB
adb devices

#Mount filesystem as writable
adb shell mount -o remount,rw /

#Backup original (optional)
adb shell mv /usr/share/qt-superbird-app/webapp /usr/share/qt-superbird-app/webapp-backup

# Create directory
adb shell mkdir -p /usr/share/qt-superbird-app/webapp

# Push redirect file
adb push redirect.html /usr/share/qt-superbird-app/webapp/index.html

# Reboot
adb shell reboot
```
Wait 30 seconds for it to reboot. The Car Thing will load the redirect, which immediately loads the dashboard from your Pi!

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
├── index.html          # Dashboard UI (served by flask)
├── access.log          # API request logs (rotated weekly)
└── venv/              # Python virtual environment
```

## Customization

Since the dashboard is served from the Pi, just edit index.html on your Pi and reload the Car Thing (unplug/replug USB)

No need to push via ADB again!

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

## Troubleshooting

**Car Thing shows "Cannot connect to Pi"**
- Check API is running
- Verify firewall
- Test API: `curl http://localhost:5000/api/system`

**Button presses do nothing**
- The Car Thing maps physical buttons to keys 1-4
- If your firmware is different, you might need to remap in the JavaScript

**Logs not showing**
- Verify log paths exist
- Check sudo permissions
- Look at API logs

## API Endpoints

The Flask server exposes these endpoints:

```
GET /api/system          # CPU, RAM, disk, temp, processes
GET /api/switch          # Network switch logs (last 30 lines)
GET /api/security        # UFW firewall blocks
GET /api/security-monitor # Runs custom security script
GET /health              # Health check
```

## Security Implementation

Basic security features included:

- **Firewall**: Port 5000 restricted to USB interface (`192.168.x.x/24`)
- **Request logging**: All API access logged to `access.log`
- **Minimal sudo**: Only essential commands whitelisted
- **Debug disabled**: No system info leakage

This setup is secure for a homelab on a trusted network. Don't expose port 5000 to the internet.

## Future Ideas
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

If you build one, I'd love to see it - open an issue with photos!
