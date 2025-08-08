# Remote Reasoner Node Setup

This document describes how to provision a dedicated local machine to run the Silli Reasoner service with `gpt-oss:20b` model for staging environments.

## Hardware Requirements

### Minimum Requirements
- **CPU**: 8+ cores (Intel/AMD)
- **RAM**: 32GB DDR4
- **Storage**: 100GB+ SSD
- **Network**: Gigabit Ethernet

### Recommended Requirements
- **CPU**: 16+ cores (Intel/AMD)
- **RAM**: 64GB DDR4
- **Storage**: 500GB+ NVMe SSD
- **Network**: 2.5Gbps Ethernet

## Installation Steps

### 1. System Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.9+
sudo apt install python3.9 python3.9-pip python3.9-venv

# Install system dependencies
sudo apt install ffmpeg libsndfile1 curl wget git
```

### 2. Install Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
sudo systemctl enable ollama
sudo systemctl start ollama

# Verify installation
ollama --version
```

### 3. Pull GPT-OSS:20B Model

**Option A: Full Model (Recommended for quality)**
```bash
# Pull the full 20B model (requires ~40GB RAM)
ollama pull gpt-oss:20b

# Verify model
ollama list | grep gpt-oss:20b
```

**Option B: Quantized Model (Lower memory usage)**
```bash
# Create quantized version (requires ~20GB RAM)
ollama pull gpt-oss:20b
ollama create gpt-oss:20b-q4 -f Modelfile << EOF
FROM gpt-oss:20b
PARAMETER quantization Q4_K_M
EOF

# Use quantized model
ollama run gpt-oss:20b-q4
```

**Memory Notes:**
- Full model: ~40GB RAM required
- Q4 quantized: ~20GB RAM required
- Q2 quantized: ~12GB RAM required (not recommended for quality)

### 4. Setup Reasoner Service

```bash
# Clone Silli Bot repository
git clone <repository-url>
cd silli-bot

# Create virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp env.staging.example .env
```

### 5. Configure Reasoner

Edit `.env` file:
```bash
# Reasoner Configuration
REASONER_HOST=0.0.0.0
REASONER_PORT=5001
REASONER_MODEL_HINT=gpt-oss:20b
REASONER_ALLOW_FALLBACK=0
REASONER_TEMP=0.2
REASONER_TIMEOUT=120

# Security (optional)
REASONER_API_TOKEN=your-secure-token-here
```

### 6. Add Simple Token Guard

Create `reasoner/auth.py`:
```python
import os
from functools import wraps
from flask import request, jsonify

def require_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        expected_token = os.getenv('REASONER_API_TOKEN')
        
        if expected_token and token != f"Bearer {expected_token}":
            return jsonify({"error": "unauthorized"}), 401
        
        return f(*args, **kwargs)
    return decorated_function
```

Update `reasoner/app.py` to use token guard:
```python
from .auth import require_token

# Add to protected endpoints
@app.route('/v1/reason', methods=['POST'])
@require_token
def reason():
    # ... existing code ...
```

### 7. Start Reasoner Service

**Option A: Direct Start**
```bash
cd reasoner
python app.py
```

**Option B: Systemd Service**
```bash
# Create service file
sudo tee /etc/systemd/system/silli-reasoner.service << EOF
[Unit]
Description=Silli Reasoner Service
After=network.target

[Service]
Type=simple
User=silli
WorkingDirectory=/home/silli/silli-bot
Environment=PATH=/home/silli/silli-bot/venv/bin
ExecStart=/home/silli/silli-bot/venv/bin/python reasoner/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable silli-reasoner
sudo systemctl start silli-reasoner
sudo systemctl status silli-reasoner
```

### 8. Firewall Configuration

```bash
# Allow only staging host to reach reasoner
sudo ufw allow from <staging-host-ip> to any port 5001
sudo ufw deny 5001  # Deny all other access to port 5001

# Verify firewall rules
sudo ufw status numbered
```

### 9. Test Reasoner

```bash
# Test health endpoint
curl http://localhost:5001/health

# Test models endpoint
curl http://localhost:5001/models

# Test reasoning endpoint
curl -X POST http://localhost:5001/v1/reason \
  -H "Content-Type: application/json" \
  -d '{"dyad": "tantrum", "features": {"vad_fraction": 0.45}, "context": {"trigger": "test"}, "metrics": {"escalation_index": 0.5}, "history": []}'
```

## Monitoring

### Logs
```bash
# View service logs
sudo journalctl -u silli-reasoner -f

# View Ollama logs
sudo journalctl -u ollama -f
```

### Performance Monitoring
```bash
# Monitor system resources
htop

# Monitor GPU usage (if available)
nvidia-smi

# Monitor network connections
netstat -tulpn | grep 5001
```

## Troubleshooting

### Common Issues

**1. Out of Memory**
```bash
# Check available memory
free -h

# Reduce model quantization
ollama create gpt-oss:20b-q2 -f Modelfile << EOF
FROM gpt-oss:20b
PARAMETER quantization Q2_K
EOF
```

**2. Slow Response Times**
```bash
# Check CPU usage
top

# Consider using quantized model
# Monitor network latency between staging and reasoner
ping <reasoner-host>
```

**3. Connection Refused**
```bash
# Check if service is running
sudo systemctl status silli-reasoner

# Check firewall rules
sudo ufw status

# Check port binding
netstat -tulpn | grep 5001
```

### Performance Optimization

**1. System Tuning**
```bash
# Increase file descriptor limits
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Optimize memory settings
echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

**2. Ollama Optimization**
```bash
# Set Ollama environment variables
export OLLAMA_HOST=0.0.0.0
export OLLAMA_ORIGINS=*
export OLLAMA_MODELS=/mnt/fast-storage/ollama  # Use fast storage
```

## Security Considerations

1. **Network Security**: Only allow staging host access
2. **API Token**: Use strong authentication tokens
3. **Regular Updates**: Keep system and dependencies updated
4. **Monitoring**: Monitor for unusual access patterns
5. **Backups**: Regular backups of configuration and models

## Maintenance

### Regular Tasks
```bash
# Update system
sudo apt update && sudo apt upgrade

# Update Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Restart services
sudo systemctl restart ollama
sudo systemctl restart silli-reasoner

# Clean up old models (optional)
ollama rm <unused-model>
```

### Health Checks
```bash
# Automated health check script
#!/bin/bash
if ! curl -s http://localhost:5001/health > /dev/null; then
    echo "Reasoner health check failed"
    sudo systemctl restart silli-reasoner
fi
```
