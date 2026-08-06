# Ubuntu VPS Production Deployment Guide

This document describes the production deployment configuration for **Gold Brain** on Ubuntu 24.04 LTS.

---

## Architecture

1. **Web Frontend**: Nginx serves the static single-page dashboard from `/opt/aux/docs` on port 80.
2. **Market Artifact Generator**: Systemd service (`goldbrain-generator.service`) triggered every 5 minutes by systemd timer (`goldbrain-generator.timer`) running `/opt/aux/venv/bin/python publish/generate_artifacts.py`.

---

## Setup & Configuration Details

### 1. Repository Location & Virtual Environment
- Repository Path: `/opt/aux`
- Python Environment: `/opt/aux/venv` (Python 3.12)
- Dependencies Installed: `pip install -e .`

### 2. Systemd Generator Service & Timer
- **Service**: `/etc/systemd/system/goldbrain-generator.service`
- **Timer**: `/etc/systemd/system/goldbrain-generator.timer` (Runs every 5 minutes: `OnCalendar=*:0/5`)

### 3. Nginx Web Server Configuration
- Configuration File: `/etc/nginx/sites-available/goldbrain`
- Symlinked To: `/etc/nginx/sites-enabled/goldbrain`
- Web Root: `/opt/aux/docs`
- Port: 80

---

## Operational Commands

```bash
# Check timer and service status
systemctl status goldbrain-generator.timer
systemctl status goldbrain-generator.service

# Manually trigger generator
systemctl start goldbrain-generator.service

# View generator logs
journalctl -u goldbrain-generator.service -n 50 --no-pager

# Check Nginx status
systemctl status nginx
curl -I http://localhost
```
