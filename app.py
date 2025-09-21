import os
import shutil
import subprocess
import glob
import psutil # <-- NEW: Import for system monitoring
from flask import Flask, request, jsonify
from flask_cors import CORS

# Initialize the Flask application
app = Flask(__name__)
# Enable Cross-Origin Resource Sharing (CORS) to allow the frontend to communicate with this backend
CORS(app)

# Store the current working directory in memory.
current_directory = os.path.expanduser("~")

def execute_command(command):
    """
    Parses and executes a given command.
    Returns the command's output and the current working directory.
    """
    global current_directory
    parts = command.strip().split()
    cmd = parts[0]
    args = parts[1:]

    try:
        if cmd == "pwd":
            return current_directory, current_directory
        
        elif cmd == "ls":
            # Using -lha for detailed, human-readable output
            result = subprocess.run(['ls', '-lha'] + args, cwd=current_directory, capture_output=True, text=True)
            return result.stdout + result.stderr, current_directory

        elif cmd == "cd":
            if not args:
                path = os.path.expanduser("~")
            else:
                path = os.path.expanduser(os.path.join(current_directory, args[0]))
            
            if os.path.isdir(path):
                current_directory = os.path.abspath(path)
                return f"Changed directory to {current_directory}", current_directory
            else:
                return f"cd: no such file or directory: {args[0]}", current_directory

        elif cmd == "mkdir":
            if not args:
                return "mkdir: missing operand", current_directory
            path = os.path.join(current_directory, args[0])
            try:
                os.makedirs(path)
                return f"Created directory: {args[0]}", current_directory
            except FileExistsError:
                return f"mkdir: cannot create directory ‘{args[0]}’: File exists", current_directory

        elif cmd == "rm":
            if not args:
                return "rm: missing operand", current_directory
            path = os.path.join(current_directory, args[0])
            if not os.path.exists(path):
                 return f"rm: cannot remove '{args[0]}': No such file or directory", current_directory
            
            try:
                if os.path.isfile(path):
                    os.remove(path)
                    return f"Removed file: {args[0]}", current_directory
                elif os.path.isdir(path) and not args:
                    shutil.rmtree(path) # Use shutil for directories
                    return f"Removed directory: {args[0]}", current_directory
                else: # Handle rm -r for directories
                    if args[0] == '-r' and len(args) > 1:
                        path = os.path.join(current_directory, args[1])
                        if os.path.isdir(path):
                            shutil.rmtree(path)
                            return f"Removed directory recursively: {args[1]}", current_directory
                    return f"rm: cannot remove '{args[0]}': Not a file or directory needs -r for recursive", current_directory
            except OSError as e:
                return f"rm: cannot remove '{args[0]}': {e.strerror}", current_directory

        # --- NEW FEATURE: SYSTEM STATUS ---
        elif cmd == "status":
            cpu_usage = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()
            memory_usage = memory_info.percent
            process_count = len(psutil.pids())

            status_output = (
                f"--- System Status ---\n"
                f"CPU Usage : {cpu_usage}%\n"
                f"Memory    : {memory_usage}% used ({memory_info.used/1024**3:.2f} GB / {memory_info.total/1024**3:.2f} GB)\n"
                f"Processes : {process_count} running\n"
            )
            return status_output, current_directory

        else:
            safe_commands = ['echo', 'touch', 'cat', 'head', 'tail', 'grep']
            if cmd in safe_commands:
                 result = subprocess.run(parts, cwd=current_directory, capture_output=True, text=True)
                 return result.stdout + result.stderr, current_directory
            else:
                return f"Command not found: {cmd}", current_directory

    except Exception as e:
        return str(e), current_directory

@app.route('/execute', methods=['POST'])
def handle_execute():
    data = request.json
    command = data.get('command')
    if not command:
        return jsonify({"error": "No command provided"}), 400

    output, pwd = execute_command(command)
    
    home_dir = os.path.expanduser("~")
    if pwd.startswith(home_dir):
        display_pwd = "~" + pwd[len(home_dir):]
    else:
        display_pwd = pwd

    return jsonify({"output": output, "pwd": display_pwd})

@app.route('/autocomplete', methods=['POST'])
def handle_autocomplete():
    global current_directory
    data = request.json
    text = data.get('text', '')
    path_to_complete = text.split(' ')[-1]
    
    if path_to_complete.startswith('~'):
        path_to_complete = os.path.expanduser('~') + path_to_complete[1:]

    base_dir = current_directory if not os.path.isabs(path_to_complete) else ''
    full_path_pattern = os.path.join(base_dir, path_to_complete) + '*'

    matches = glob.glob(full_path_pattern)
    
    completions = []
    for match in matches:
        completion = os.path.basename(match)
        if os.path.isdir(match):
            completion += '/'
        completions.append(completion)

    return jsonify({"completions": completions})


if __name__ == '__main__':
    app.run(port=5000, debug=True)

