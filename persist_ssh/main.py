#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse
import tomllib
from pathlib import Path

DEFAULT_CONFIG = {
    'session_from_tmux_pane': False,
    'default_session_name': 'default',  # Changed from 'main' to 'default'
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
# Use current tmux window name as session name (set to true to enable)
session_from_tmux_pane = false
# Default session name when not using tmux window names
default_session_name = "default"

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
    
    return config.get('default_session_name', 'default')

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

# Remove these unused functions since we're SSH-only now

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
        
        # Detect user's shell (fallback to bash if not found)
        USER_SHELL=$(getent passwd $USER | cut -d: -f7)
        if [ -z "$USER_SHELL" ] || [ ! -x "$USER_SHELL" ]; then
            USER_SHELL=/bin/bash
        fi
        
        # Check if dtach is available
        if command -v dtach >/dev/null 2>&1; then
            echo "Starting persistent session: {session_name} (Ctrl+T to detach)"
            exec dtach -A ~/.persist-ssh/{session_name} -e "^T" $USER_SHELL
        else
            echo "dtach not found - attempting to install..."
            
            # Try to install dtach based on available package manager
            if command -v apt >/dev/null 2>&1; then
                sudo apt update && sudo apt install -y dtach
            elif command -v yum >/dev/null 2>&1; then
                sudo yum install -y dtach
            elif command -v dnf >/dev/null 2>&1; then
                sudo dnf install -y dtach
            elif command -v pacman >/dev/null 2>&1; then
                sudo pacman -S --noconfirm dtach
            elif command -v apk >/dev/null 2>&1; then
                sudo apk add dtach
            else
                echo "Could not detect package manager. Please install dtach manually:"
                echo "  Ubuntu/Debian: sudo apt install dtach"
                echo "  RHEL/CentOS:   sudo yum install dtach"
                echo "  Fedora:        sudo dnf install dtach"
                echo "  Arch:          sudo pacman -S dtach"
                echo "  Alpine:        sudo apk add dtach"
                exec $USER_SHELL
            fi
            
            # Check if installation succeeded
            if command -v dtach >/dev/null 2>&1; then
                echo "dtach installed successfully!"
                echo "Starting persistent session: {session_name} (Ctrl+T to detach)"
                exec dtach -A ~/.persist-ssh/{session_name} -e "^T" $USER_SHELL
            else
                echo "Failed to install dtach. Starting regular shell."
                exec $USER_SHELL
            fi
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
  persist-ssh myserver                    # Connect using default session name
  persist-ssh myserver --session dev      # Connect to specific session
  persist-ssh myserver --tmux             # Use current tmux window name as session
  persist-ssh myserver --list             # List active sessions
        """
    )
    
    parser.add_argument('host', help='Remote host to connect to')
    parser.add_argument('--session', '-s', help='Session name (overrides config)')
    parser.add_argument('--list', '-l', action='store_true', help='List remote sessions')
    parser.add_argument('--debug', '-d', action='store_true', help='Show debug output')
    parser.add_argument('--tmux', '-t', action='store_true', help='Use tmux window name as session name')
    
    args = parser.parse_args()
    
    if args.list:
        list_remote_sessions(args.host)
        return
    
    # Determine session name with --tmux flag override
    if args.tmux:
        # Force tmux window name usage regardless of config
        tmux_name = get_tmux_window_name()
        if tmux_name:
            session_name = tmux_name
        else:
            print("Warning: Not in tmux or tmux not found, using default session name")
            session_name = config.get('default_session_name', 'default')
    else:
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