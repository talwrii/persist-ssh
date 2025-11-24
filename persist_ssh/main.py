#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse
import tomllib
from pathlib import Path

DEFAULT_CONFIG = {
    'session_from_tmux_pane': True,
    'default_session_name': 'main',
    'dtach_install_command': {
        'ubuntu': 'sudo apt update && sudo apt install -y dtach',
        'debian': 'sudo apt update && sudo apt install -y dtach',
        'redhat': 'sudo yum install -y dtach || sudo dnf install -y dtach',
        'arch': 'sudo pacman -S dtach',
        'alpine': 'sudo apk add dtach'
    },
    'mosh_install_command': {
        'ubuntu': 'sudo apt update && sudo apt install -y mosh',
        'debian': 'sudo apt update && sudo apt install -y mosh',
        'redhat': 'sudo yum install -y mosh || sudo dnf install -y mosh',
        'arch': 'sudo pacman -S mosh',
        'alpine': 'sudo apk add mosh'
    }
}

def get_config_path():
    """Get the config file path"""
    return Path.home() / '.config' / 'persist-ssh.toml'

def load_config():
    """Load configuration from TOML file"""
    config_path = get_config_path()
    
    if not config_path.exists():
        # Create default config
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            f.write("""# persist-ssh configuration
# Use current tmux window name as session name
session_from_tmux_pane = true
# Default session name when not in tmux
default_session_name = "main"

# Commands to install dtach on different systems
[dtach_install_command]
ubuntu = "sudo apt update && sudo apt install -y dtach"
debian = "sudo apt update && sudo apt install -y dtach"
redhat = "sudo yum install -y dtach || sudo dnf install -y dtach"
arch = "sudo pacman -S dtach"
alpine = "sudo apk add dtach"

# Commands to install mosh on different systems
[mosh_install_command]
ubuntu = "sudo apt update && sudo apt install -y mosh"
debian = "sudo apt update && sudo apt install -y mosh"
redhat = "sudo yum install -y mosh || sudo dnf install -y mosh"
arch = "sudo pacman -S mosh"
alpine = "sudo apk add mosh"
""")
        print(f"Created default config at {config_path}")
        return DEFAULT_CONFIG
    
    with open(config_path, 'rb') as f:
        return tomllib.load(f)

def get_tmux_window_name():
    """Get the current tmux window name"""
    try:
        result = subprocess.run(['tmux', 'display-message', '-p', '#W'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def get_session_name(config, override_name=None):
    """Determine session name based on config and context"""
    if override_name:
        return override_name
    
    if config.get('session_from_tmux_pane', False):
        tmux_name = get_tmux_window_name()
        if tmux_name:
            return tmux_name
    
    return config.get('default_session_name', 'main')

def run_ssh_command(host, command, need_tty=False):
    """Run a command on remote host via SSH and return result"""
    try:
        ssh_cmd = ['ssh']
        if need_tty:
            ssh_cmd.append('-t')
        ssh_cmd.extend([host, command])
        
        result = subprocess.run(ssh_cmd, 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip(), True
    except subprocess.CalledProcessError as e:
        return e.stderr.strip(), False

def run_ssh_commands_batch(host, commands):
    """Run multiple commands in a single SSH session"""
    # Combine commands with && to run them in sequence
    combined_command = ' && '.join(commands)
    return run_ssh_command(host, combined_command)

def check_and_setup_remote(host, debug=False):
    """Check what's installed and set up everything in one go"""
    if debug:
        print("Checking remote setup in batch...")
    
    # Single command to check everything and setup
    setup_script = """
    # Check if dtach exists
    if command -v dtach >/dev/null 2>&1; then
        echo "DTACH_OK"
    else
        echo "DTACH_MISSING"
    fi
    
    # Create persist-ssh directory
    mkdir -p ~/.persist-ssh
    echo "SETUP_COMPLETE"
    """
    
    output, success = run_ssh_command(host, setup_script)
    
    if not success:
        return False, "Failed to run setup script"
    
    dtach_ok = "DTACH_OK" in output
    setup_complete = "SETUP_COMPLETE" in output
    
    if debug:
        print(f"Batch setup result: dtach_ok={dtach_ok}, setup_complete={setup_complete}")
    
    return dtach_ok, output

def detect_remote_os(host):
    """Detect the remote OS to choose install command"""
    # Try to detect OS
    output, success = run_ssh_command(host, 'cat /etc/os-release 2>/dev/null || uname')
    if not success:
        return 'unknown'
    
    output = output.lower()
    
    if 'ubuntu' in output:
        return 'ubuntu'
    elif 'debian' in output:
        return 'debian'
    elif 'rhel' in output or 'centos' in output or 'fedora' in output or 'red hat' in output:
        return 'redhat'
    elif 'arch' in output:
        return 'arch'
    elif 'alpine' in output:
        return 'alpine'
    else:
        return 'unknown'

def install_dtach(host, config):
    """Install dtach on remote host"""
    os_type = detect_remote_os(host)
    
    install_commands = config.get('dtach_install_command', {})
    
    if os_type in install_commands:
        cmd = install_commands[os_type]
        print(f"Installing dtach on {host} ({os_type})...")
        print("You may be prompted for your password...")
        
        # Use TTY for sudo commands
        result = subprocess.run(['ssh', '-t', host, cmd])
        
        if result.returncode == 0:
            print("dtach installed successfully")
            return True
        else:
            print("Failed to install dtach")
            return False
    else:
        print(f"Don't know how to install dtach on {os_type}. Please install manually.")
        return False

def install_mosh(host, config):
    """Install mosh on remote host"""
    os_type = detect_remote_os(host)
    
    install_commands = config.get('mosh_install_command', {})
    
    if os_type in install_commands:
        cmd = install_commands[os_type]
        print(f"Installing mosh on {host} ({os_type})...")
        print("You may be prompted for your password...")
        
        # Use TTY for sudo commands
        result = subprocess.run(['ssh', '-t', host, cmd])
        
        if result.returncode == 0:
            print("mosh installed successfully")
            return True
        else:
            print("Failed to install mosh")
            return False
    else:
        print(f"Don't know how to install mosh on {os_type}. Please install manually.")
        return False

def list_remote_sessions(host):
    """List existing dtach sessions on remote host"""
    # Use .persist-ssh directory for sessions
    cmd = """python3 -c "
import os
from pathlib import Path
session_dir = Path.home() / '.persist-ssh'
if session_dir.exists():
    sessions = [f.name for f in session_dir.iterdir() if f.is_socket()]
    if sessions:
        print('Active sessions:')
        for s in sorted(sessions): print(f'  {s}')
    else:
        print('No active sessions')
else:
    print('No active sessions')
" """
    
    output, success = run_ssh_command(host, cmd)
    if success:
        print(output)
    else:
        print("Could not list sessions")

def connect_to_session(host, session_name, debug=False):
    """Connect via SSH with a single call that handles everything"""
    if debug:
        print(f"Connecting to {host}, session: {session_name}")
    
    # Single SSH command that:
    # 1. Checks if dtach exists
    # 2. Creates directory if needed
    # 3. Starts/attaches to session with Ctrl+T as detach key
    # 4. Falls back to plain bash if dtach missing
    
    single_command = f'''
        # Create session directory
        mkdir -p ~/.persist-ssh
        
        # Check if dtach is available and try to use it
        if command -v dtach >/dev/null 2>&1; then
            echo "Starting persistent session: {session_name} (Ctrl+T to detach)"
            exec dtach -A ~/.persist-ssh/{session_name} -e "^T" bash
        else
            echo "dtach not found - starting regular shell"
            echo "Install dtach for persistent sessions: sudo apt install dtach"
            exec bash
        fi
    '''
    
    ssh_cmd = ['ssh', '-t', host, single_command]
    
    if debug:
        print(f"Running single SSH command with Ctrl+T detach")
        print(f"Command: {single_command.strip()}")
    
    try:
        subprocess.run(ssh_cmd)
    except KeyboardInterrupt:
        print("\nDisconnected.")
    except Exception as e:
        print(f"Error connecting: {e}")

def main():
    config = load_config()
    
    parser = argparse.ArgumentParser(
        description='Persistent SSH connections via SSH + dtach',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  persist-ssh myserver                    # Connect using tmux window name or default
  persist-ssh myserver --session dev      # Connect to specific session
  persist-ssh myserver --list            # List active sessions
        """
    )
    
    parser.add_argument('host', help='Remote host to connect to')
    parser.add_argument('--session', '-s', help='Session name (overrides config)')
    parser.add_argument('--list', '-l', action='store_true', help='List remote sessions')
    parser.add_argument('--debug', '-d', action='store_true', help='Show debug output')
    
    args = parser.parse_args()
    
    if args.list:
        list_remote_sessions(args.host)
        return
    
    # Determine session name
    session_name = get_session_name(config, args.session)
    
    if args.debug:
        print(f"Session name: {session_name}")
        if config.get('session_from_tmux_pane'):
            tmux_name = get_tmux_window_name()
            print(f"Tmux window name: {tmux_name}")
    
    # Single SSH connection that handles everything
    connect_to_session(args.host, session_name, args.debug)

if __name__ == '__main__':
    main()