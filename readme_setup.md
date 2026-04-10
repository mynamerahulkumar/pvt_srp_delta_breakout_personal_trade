sudo yum update -y

Git setup
sudo yum install git -y

Python setup 
sudo yum install python3 -y


Uv set up

curl -Ls https://astral.sh/uv/install.sh | bash
source ~/.bashrc

https://github.com/mynamerahulkumar/pvt_srp_delta_breakout_personal_trade.git

uv --version

(Optional) Add to PATH manually
If uv is not found:

export PATH="$HOME/.local/bin:$PATH"

To make it permanent:

echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc


## Run Bot (survives SSH logout)

nohup uv run start.py &

## Monitor Bot

# Check if bot is running (shows PID + uptime)
./monitor.sh status

# Stream live logs in real-time (Ctrl+C to stop)
./monitor.sh logs

# Show last 50 log lines
./monitor.sh last

# Show last N lines
./monitor.sh last 100

# Quick status + last 10 lines
./monitor.sh
