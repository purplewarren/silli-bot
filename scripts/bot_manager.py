#!/usr/bin/env python3
"""
Bot Management Script - Ensures only one bot instance runs at a time
Prevents the recurring issue of multiple bot processes causing conflicts
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

def get_bot_processes():
    """Find all running bot processes."""
    try:
        # More comprehensive search for bot processes
        commands = [
            ["pgrep", "-f", "bot.main"],
            ["ps", "aux"]
        ]
        
        bot_pids = set()
        
        # Use pgrep first
        try:
            result = subprocess.run(
                ["pgrep", "-f", "bot.main"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        bot_pids.add(int(line))
        except Exception:
            pass
        
        # Fallback to ps aux
        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                check=True
            )
            
            for line in result.stdout.split('\n'):
                if 'python -m bot.main' in line and 'grep' not in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        pid = int(parts[1])
                        bot_pids.add(pid)
        except Exception:
            pass
        
        return list(bot_pids)
    except Exception as e:
        print(f"Error finding bot processes: {e}")
        return []

def kill_all_bots():
    """Kill all running bot processes."""
    processes = get_bot_processes()
    
    if not processes:
        print("✅ No bot processes found")
        return True
    
    print(f"🔍 Found {len(processes)} bot processes: {processes}")
    
    # Try graceful shutdown first
    for pid in processes:
        try:
            print(f"📤 Sending SIGTERM to process {pid}")
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            print(f"⚠️ Process {pid} already terminated")
        except Exception as e:
            print(f"❌ Error terminating process {pid}: {e}")
    
    # Wait for graceful shutdown
    time.sleep(3)
    
    # Check if any processes remain
    remaining = get_bot_processes()
    if remaining:
        print(f"💀 Force killing remaining processes: {remaining}")
        for pid in remaining:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except Exception as e:
                print(f"❌ Error force killing process {pid}: {e}")
        
        time.sleep(1)
    
    # Final check
    final_check = get_bot_processes()
    if final_check:
        print(f"❌ Failed to kill processes: {final_check}")
        return False
    
    print("✅ All bot processes terminated")
    return True

def clear_telegram_webhook():
    """Clear Telegram webhook to resolve conflicts."""
    try:
        # Read bot token from .env
        env_file = Path(".env")
        if not env_file.exists():
            print("⚠️ No .env file found, skipping webhook clear")
            return
        
        token = None
        for line in env_file.read_text().split('\n'):
            if line.startswith('TELEGRAM_BOT_TOKEN='):
                token = line.split('=', 1)[1].strip()
                break
        
        if not token or token == 'replace_me':
            print("⚠️ No valid bot token found, skipping webhook clear")
            return
        
        print("🧹 Clearing Telegram webhook...")
        result = subprocess.run([
            "curl", "-X", "POST", 
            f"https://api.telegram.org/bot{token}/deleteWebhook"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Webhook cleared")
        else:
            print(f"⚠️ Webhook clear failed: {result.stderr}")
            
    except Exception as e:
        print(f"⚠️ Error clearing webhook: {e}")

def start_bot():
    """Start a single bot instance."""
    if not kill_all_bots():
        print("❌ Failed to clean up existing processes")
        return False
    
    # Clear Telegram webhook to prevent conflicts
    clear_telegram_webhook()
    
    # Wait a moment after cleanup
    time.sleep(2)
    
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    print("🚀 Starting bot...")
    
    try:
        # Start bot in background
        process = subprocess.Popen(
            [sys.executable, "-m", "bot.main"],
            stdout=open("logs/bot.log", "w"),
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid  # Create new process group
        )
        
        # Wait longer to check if it started successfully
        print("⏳ Waiting for startup...")
        time.sleep(5)
        
        if process.poll() is None:
            print(f"✅ Bot started successfully (PID: {process.pid})")
            print(f"📝 Logs: tail -f logs/bot.log")
            print(f"🔍 Status: python scripts/bot_manager.py status")
            return True
        else:
            print(f"❌ Bot failed to start (exit code: {process.returncode})")
            print("📝 Check logs: tail logs/bot.log")
            return False
            
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        return False

def status():
    """Show current bot status."""
    processes = get_bot_processes()
    
    if not processes:
        print("❌ No bot processes running")
        return False
    elif len(processes) == 1:
        print(f"✅ Bot running (PID: {processes[0]})")
        return True
    else:
        print(f"⚠️ Multiple bot processes detected: {processes}")
        print("🔧 Run 'python scripts/bot_manager.py restart' to fix")
        return False

def restart():
    """Restart the bot cleanly."""
    print("🔄 Restarting bot...")
    return start_bot()

def main():
    """Main command handler."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/bot_manager.py start    - Start bot")
        print("  python scripts/bot_manager.py stop     - Stop bot")
        print("  python scripts/bot_manager.py restart  - Restart bot")
        print("  python scripts/bot_manager.py status   - Show status")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "start":
        success = start_bot()
    elif command == "stop":
        success = kill_all_bots()
    elif command == "restart":
        success = restart()
    elif command == "status":
        success = status()
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
