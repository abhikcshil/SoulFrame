#!/bin/bash
# Setup script for SoulFrame device agent

set -e

echo "Setting up SoulFrame Device Agent..."

# Install dependencies
sudo apt-get update
sudo apt-get install -y python3-pip python3-pil mpv qrencode

# Install Python packages
pip3 install requests pillow

# Create directory structure
mkdir -p /home/admin/soulframe/{config,cache,media,logs}

# Download agent
curl -o /home/admin/soulframe/device_agent.py https://your-server/device_agent.py
chmod +x /home/admin/soulframe/device_agent.py

# Prompt for configuration
echo ""
echo "Creating configuration file..."
read -p "Enter API base URL (e.g., http://192.168.1.100:8000): " API_URL
read -p "Enter device token: " DEVICE_TOKEN

cat > /home/admin/soulframe/config/device.json <<EOF
{
  "api_base_url": "$API_URL",
  "device_token": "$DEVICE_TOKEN",
  "checkin_interval_seconds": 20
}
EOF

echo "Configuration saved to /home/admin/soulframe/config/device.json"

# Create systemd service
sudo tee /etc/systemd/system/soulframe.service > /dev/null <<EOF
[Unit]
Description=SoulFrame Device Agent
After=network.target

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/soulframe
ExecStart=/usr/bin/python3 /home/admin/soulframe/device_agent.py
Restart=always
RestartSec=10
Environment=DISPLAY=:0
Environment=XDG_RUNTIME_DIR=/run/user/1000

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable soulframe.service

echo ""
echo "Setup complete!"
echo ""
echo "To start the agent:"
echo "  sudo systemctl start soulframe"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u soulframe -f"
echo "  or: tail -f /home/admin/soulframe/logs/agent.log"
echo ""
echo "To get device token from backend:"
echo "  docker compose exec db psql -U smartframe -d smartframe"
echo "  Then run: SELECT device_token FROM devices WHERE name='Your Device Name';"