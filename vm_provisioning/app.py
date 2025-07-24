# app.py
from flask import (
    Flask,
    render_template_string,
    request,
    redirect,
    session,
    url_for,
    jsonify,
    Response,
    flash,
    send_from_directory,
)
import threading
import queue
import secrets
import logging
from datetime import datetime, timedelta
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash
import re
import time
import random
from config import config

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.permanent_session_lifetime = timedelta(
    seconds=int(os.environ.get("SESSION_LIFETIME", 7200))
)

# Use demo mode from config
DEMO_MODE = config["DEMO_MODE"]
app.logger.info(f"Demo mode is {'enabled' if DEMO_MODE else 'disabled'}")

# Global variable for storing last provision VMs data
last_provision_vms = []


@app.route("/get_demo_mode", methods=["GET"])
def get_demo_mode():
    """Get current demo mode status"""
    return jsonify({"demo_mode": DEMO_MODE})

@app.route("/toggle-demo-mode", methods=["POST"])
def toggle_demo_mode():
    """Toggle demo mode"""
    global DEMO_MODE
    DEMO_MODE = not DEMO_MODE
    app.logger.info(f"Demo mode {'enabled' if DEMO_MODE else 'disabled'}")
    return jsonify({"demo_mode": DEMO_MODE})


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("vm_provisioning.log"), logging.StreamHandler()],
)

# Thread-safe queue for log messages
log_queue = queue.Queue()

# In-memory storage for demo (use database in production)
users = {
    "admin": generate_password_hash("admin123"),
    "demo": generate_password_hash("demo123"),
}

# Mockup Data
MOCK_TEMPLATES = [
    "Windows-Server-2019-Template",
    "Windows-Server-2022-Template",
    "Ubuntu-20.04-LTS-Template",
    "Ubuntu-22.04-LTS-Template",
    "CentOS-8-Template",
    "RedHat-Enterprise-8-Template",
    "VMware-PhotonOS-Template",
    "Windows-10-Template",
]

MOCK_DATACENTERS = ["DataCenter-Primary", "DataCenter-DR", "DataCenter-Development"]

MOCK_CLUSTERS = {
    "DataCenter-Primary": ["Cluster-Production", "Cluster-Web", "Cluster-Database"],
    "DataCenter-DR": ["Cluster-DR-Primary", "Cluster-DR-Secondary"],
    "DataCenter-Development": ["Cluster-Dev", "Cluster-Test", "Cluster-Staging"],
}

MOCK_NETWORKS = {
    "DataCenter-Primary": [
        "Production-VLAN-100",
        "Web-DMZ-VLAN-200",
        "Database-VLAN-300",
        "Management-VLAN-400",
    ],
    "DataCenter-DR": ["DR-Production-VLAN-150", "DR-Management-VLAN-450"],
    "DataCenter-Development": [
        "Dev-Network-VLAN-10",
        "Test-Network-VLAN-20",
        "Staging-Network-VLAN-30",
    ],
}


def validate_ip(ip):
    """Validate IP address format"""
    pattern = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    return re.match(pattern, ip) is not None


def validate_hostname(hostname):
    """Validate hostname format"""
    pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
    return re.match(pattern, hostname) is not None


# Mock vCenter functions
def mock_get_template_names(vcenter_host, vcenter_user, vcenter_pass):
    """Mock function to return template names"""
    time.sleep(0.5)  # Simulate network delay
    
    # Simulate an error occasionally if host is 'error.vcenter.com'
    if vcenter_host == "error.vcenter.com":
        raise Exception("Mock Connection Error: Could not reach vCenter host.")
    
    # In DEMO MODE, validate basic format but always succeed
    # This is different from production mode behavior
    if not validate_hostname(vcenter_host) and not validate_ip(vcenter_host):
        raise Exception("Mock Error: Invalid vCenter host format")
    
    return MOCK_TEMPLATES


def mock_get_datacenters(vcenter_host, vcenter_user, vcenter_pass):
    """Mock function to return datacenters"""
    time.sleep(0.3)
    
    # In DEMO MODE, validate basic format but always succeed
    if not validate_hostname(vcenter_host) and not validate_ip(vcenter_host):
        raise Exception("Mock Error: Invalid vCenter host format")
    
    return MOCK_DATACENTERS


def mock_get_clusters(vcenter_host, vcenter_user, vcenter_pass, datacenter_name):
    """Mock function to return clusters"""
    time.sleep(0.3)
    return MOCK_CLUSTERS.get(datacenter_name, ["Default-Cluster"])


def mock_get_networks(vcenter_host, vcenter_user, vcenter_pass, datacenter_name):
    """Mock function to return networks"""
    time.sleep(0.3)
    return MOCK_NETWORKS.get(datacenter_name, ["Default-Network"])


def mock_get_nic_count(vcenter_host, vcenter_user, vcenter_pass, template_name):
    """Mock function to return NIC count"""
    time.sleep(0.2)
    # Different templates have different NIC counts
    if "Windows" in template_name:
        return 2
    elif "Ubuntu" in template_name:
        return 1
    elif "Database" in template_name:  # Example for a template with 3 NICs
        return 3
    else:
        return 2  # Default for others


def mock_provision_vms(
    vcenter_host,
    vcenter_user,
    vcenter_pass,
    template,
    prefix,
    count,
    datacenter_name,
    cluster_name,
    network_name,
    ip_map,
    logger=print,
):
    """Mock function to simulate VM provisioning"""

    logger(f"🚀 DEMO: Starting VM provisioning...")
    logger(f"📋 Template: {template}")
    logger(f"📋 Prefix: {prefix}")
    logger(f"📋 Count: {count}")
    logger(f"📋 Datacenter: {datacenter_name}")
    logger(f"📋 Cluster: {cluster_name}")
    logger(f"📋 Network: {network_name}")

    logger("✅ DEMO: Connected to vCenter")
    logger("✅ DEMO: Found all required vCenter objects")
    logger("📁 DEMO: Using datastore: Production-SSD-Datastore")

    # Simulate VM creation process
    for i in range(1, count + 1):
        vm_name = f"{prefix}{i:02d}"
        logger(f"🔄 DEMO: Cloning VM {i}/{count}: {vm_name}")

        # Simulate work with random delays
        time.sleep(random.uniform(0.5, 1.5))

        # Simulate occasional "complexity"
        if random.random() < 0.1:  # 10% chance
            logger(f"⏳ DEMO: {vm_name} - Configuring advanced settings...")
            time.sleep(1)

        # Simulate network configuration
        if ip_map:
            logger(f"🌐 DEMO: Configuring network for {vm_name}")
            for net_key, ip_addr in ip_map.items():
                if ip_addr:
                    logger(f"   - {net_key}: {ip_addr}")

        # Simulate power on
        logger(f"⚡ DEMO: Powering on {vm_name}")
        time.sleep(0.5)

        logger(f"✅ DEMO: {vm_name} created successfully")

    completion_msg = f"DEMO: Provisioned {count} VMs successfully!"
    logger(f"🎉 {completion_msg}")
    return completion_msg


# Dynamic function resolver based on current DEMO_MODE
def get_current_functions():
    """Return appropriate functions based on current DEMO_MODE"""
    global DEMO_MODE
    app.logger.info(f"get_current_functions called with DEMO_MODE={DEMO_MODE}")
    
    if DEMO_MODE:
        app.logger.info("Returning MOCK functions for DEMO_MODE=True")
        # Try to load the demo mode function for realistic logs
        try:
            from vm_provision import provision_vms_demo_mode
            demo_func = provision_vms_demo_mode
        except ImportError as e:
            app.logger.error(f"Failed to import provision_vms_demo_mode: {e}")
            demo_func = None
            
        return {
            'get_template_names': mock_get_template_names,
            'get_datacenters': mock_get_datacenters,
            'get_clusters': mock_get_clusters,
            'get_networks': mock_get_networks,
            'get_nic_count': mock_get_nic_count,
            'provision_vms': mock_provision_vms,
            'provision_vms_demo_mode': demo_func  # Add demo mode function
        }
    else:
        app.logger.info("Attempting to load REAL vCenter functions for DEMO_MODE=False")
        try:
            from vm_provision import (
                provision_vms,
                provision_vms_demo_mode,
                get_template_names,
                get_nic_count,
                get_datacenters,
                get_clusters,
                get_networks,
            )
            app.logger.info("Successfully loaded REAL vCenter functions")
            return {
                'get_template_names': get_template_names,
                'get_datacenters': get_datacenters,
                'get_clusters': get_clusters,
                'get_networks': get_networks,
                'get_nic_count': get_nic_count,
                'provision_vms': provision_vms,
                'provision_vms_demo_mode': provision_vms_demo_mode  # Also available in production for troubleshooting
            }
        except Exception as e:
            app.logger.error(f"Error loading real vCenter functions: {e}, falling back to mock")
            return {
                'get_template_names': mock_get_template_names,
                'get_datacenters': mock_get_datacenters,
            'get_clusters': mock_get_clusters,
            'get_networks': mock_get_networks,
            'get_nic_count': mock_get_nic_count,
            'provision_vms': mock_provision_vms,
            'provision_vms_demo_mode': provision_vms_demo_mode  # Add demo mode function
        }# Wrapper functions that dynamically select implementation
def get_template_names(vcenter_host, vcenter_user, vcenter_pass):
    return get_current_functions()['get_template_names'](vcenter_host, vcenter_user, vcenter_pass)

def get_datacenters(vcenter_host, vcenter_user, vcenter_pass):
    return get_current_functions()['get_datacenters'](vcenter_host, vcenter_user, vcenter_pass)

def get_clusters(vcenter_host, vcenter_user, vcenter_pass, datacenter_name):
    return get_current_functions()['get_clusters'](vcenter_host, vcenter_user, vcenter_pass, datacenter_name)

def get_networks(vcenter_host, vcenter_user, vcenter_pass, datacenter_name):
    return get_current_functions()['get_networks'](vcenter_host, vcenter_user, vcenter_pass, datacenter_name)

def get_nic_count(vcenter_host, vcenter_user, vcenter_pass, template_name):
    return get_current_functions()['get_nic_count'](vcenter_host, vcenter_user, vcenter_pass, template_name)

def provision_vms(vcenter_host, vcenter_user, vcenter_pass, template, prefix, count, datacenter_name, cluster_name, network_name, ip_map, logger=print):
    return get_current_functions()['provision_vms'](vcenter_host, vcenter_user, vcenter_pass, template, prefix, count, datacenter_name, cluster_name, network_name, ip_map, logger)


@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    # Pass demo_mode to the template
    global DEMO_MODE
    
    # Log all POST requests for debugging
    if request.method == "POST":
        app.logger.info(f"POST to /login received")
        app.logger.info(f"Headers: {dict(request.headers)}")
        app.logger.info(f"Form data: {dict(request.form)}")
        app.logger.info(f"X-Requested-With header: {request.headers.get('X-Requested-With')}")
    
    # Check if it's an AJAX request (from fetch in login.html)
    if (
        request.method == "POST"
        and request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ):
        app.logger.info(f"Entering AJAX branch for system login")
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        app.logger.info(f"System login attempt - username: {username}")
        app.logger.info(f"Form keys received: {list(request.form.keys())}")

        # System authentication only
        if username not in users:
            app.logger.error(f"Username {username} not found in users dict")
            return (
                jsonify(
                    {"error": "Invalid system username or password.", "status": "error"}
                ),
                401,
            )
        else:
            password_check = check_password_hash(users[username], password)
            app.logger.info(f"Password check for {username}: {password_check}")
            
        if not check_password_hash(users[username], password):
            return (
                jsonify(
                    {"error": "Invalid system username or password.", "status": "error"}
                ),
                401,
            )

        # Store system credentials in session
        session.permanent = True
        session["username"] = username
        session["system_login_time"] = datetime.now().isoformat()

        app.logger.info(f"System login successful for {username}, redirecting to vCenter login")
        # Redirect to vCenter login page
        return (
            jsonify(
                {
                    "message": "System login successful. Please configure vCenter connection.",
                    "status": "success",
                    "redirect_url": url_for("vcenter_login"),
                }
            ),
            200,
        )

    # For initial GET request or non-AJAX POST (e.g., direct form submission without JS)
    # This part handles initial page load and Flask's flash messages
    error = None
    if (
        request.method == "POST"
    ):  # This block is mostly for non-AJAX fallback or initial system login
        # If it's a non-AJAX POST, it means system login was attempted directly
        # which would then proceed to vCenter login step on the same page.
        # This scenario is less likely with the new AJAX flow for vCenter.
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username not in users or not check_password_hash(users[username], password):
            error = "Invalid username or password"
            flash(error, "error")  # Flash message for non-AJAX flow
        else:
            # If system login is successful here, it implies a direct form submission
            # which would then proceed to vCenter login step on the same page.
            # This scenario is less likely with the new AJAX flow for vCenter.
            pass  # The AJAX part handles vCenter login

    return render_template_string(
        open("templates/login.html", "r", encoding="utf-8").read(),
        error=error,
        demo_mode=DEMO_MODE,  # Use current global DEMO_MODE value
    )


@app.route("/vcenter-login", methods=["GET", "POST"])
def vcenter_login():
    # Check if system login completed
    if not session.get("username"):
        return redirect(url_for("login"))
    
    global DEMO_MODE
    
    if request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        vcenter_host = request.form.get("vcenter_host", "").strip()
        vcenter_user = request.form.get("vcenter_user", "").strip()
        vcenter_pass = request.form.get("vcenter_pass", "")

        app.logger.info(f"vCenter login attempt - user: {session['username']}, demo_mode: {DEMO_MODE}")
        app.logger.info(f"vCenter data received - host: {vcenter_host}, user: {vcenter_user}")

        # vCenter connection test - Use dynamic function resolution
        try:
            if not DEMO_MODE:
                # In Production Mode, validate host format and attempt real vCenter connection
                if not validate_hostname(vcenter_host) and not validate_ip(vcenter_host):
                    return jsonify({
                        "error": "Invalid vCenter host format. Please enter a valid hostname or IP address.",
                        "status": "error"
                    }), 400
                
                # Use dynamic function resolver for production mode
                current_functions = get_current_functions()
                template_func = current_functions['get_template_names']
                
                # This will attempt REAL vCenter connection and should fail with wrong credentials
                template_func(vcenter_host, vcenter_user, vcenter_pass)
                
            else:
                # In demo mode, use mock data with simulated errors
                if vcenter_host.lower() == 'error.vcenter.com':
                    # Simulate a connection error in demo mode
                    raise Exception("Demo Mode: Simulated vCenter connection error")
                    
                # Use dynamic function resolver for demo mode  
                current_functions = get_current_functions()
                template_func = current_functions['get_template_names']
                template_func(vcenter_host, vcenter_user, vcenter_pass)

            # Store vCenter credentials in session
            session["vcenter_host"] = vcenter_host
            session["vcenter_user"] = vcenter_user
            session["vcenter_pass"] = vcenter_pass
            session["login_time"] = datetime.now().isoformat()
            session.permanent = True  # Ensure session is permanent after vCenter login

            message = "Successfully connected to vCenter!"
            if DEMO_MODE:
                message = "Connected to DEMO vCenter! (This is mockup data)"

            # Return JSON response with redirect URL on success
            return (
                jsonify(
                    {
                        "message": message,
                        "status": "success",
                        "redirect_url": url_for("dashboard"),
                    }
                ),
                200,
            )

        except Exception as e:
            error_msg = f"Failed to connect to vCenter: {str(e)}"
            app.logger.error(f"vCenter connection failed for {session['username']} (DEMO_MODE={DEMO_MODE}): {str(e)}")
            app.logger.error(f"Exception type: {type(e).__name__}")
            
            # In production mode, this should be a real connection error
            # In demo mode, this should only happen for simulated errors
            if not DEMO_MODE:
                app.logger.error(f"PRODUCTION MODE: Real vCenter connection failed with wrong credentials")
            else:
                app.logger.error(f"DEMO MODE: Simulated connection error")
                
            return jsonify({"error": error_msg, "status": "error"}), 400

    # Render vCenter login page
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>vCenter Connection - VM Provisioning Hub</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --glass-bg: rgba(255, 255, 255, 0.25);
            --glass-border: rgba(255, 255, 255, 0.18);
            --text-primary: #2d3748;
            --text-secondary: #718096;
            --success-color: #48bb78;
            --error-color: #f56565;
            --shadow-light: 0 8px 32px rgba(31, 38, 135, 0.37);
            --shadow-heavy: 0 8px 32px rgba(31, 38, 135, 0.5);
        }

        body {
            font-family: 'Inter', sans-serif;
            background: var(--primary-gradient);
            min-height: 100vh;
            position: relative;
            overflow-x: hidden;
        }

        .login-container {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
            position: relative;
            z-index: 10;
        }

        .login-card {
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            border-radius: 24px;
            padding: 40px;
            width: 100%;
            max-width: 480px;
            box-shadow: var(--shadow-light);
            border: 1px solid var(--glass-border);
            animation: slideUp 0.6s ease-out;
        }

        .logo-section {
            text-align: center;
            margin-bottom: 40px;
        }

        .logo-title {
            color: white;
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .logo-subtitle {
            color: rgba(255, 255, 255, 0.8);
            font-size: 16px;
            font-weight: 400;
        }

        .form-group {
            margin-bottom: 25px;
        }

        .form-label {
            display: block;
            margin-bottom: 8px;
            color: var(--text-primary);
            font-weight: 600;
            font-size: 14px;
        }

        .input-with-icon {
            position: relative;
        }

        .input-icon {
            position: absolute;
            left: 18px;
            top: 50%;
            transform: translateY(-50%);
            color: #a0aec0;
            font-size: 16px;
            z-index: 1;
        }

        .form-input {
            width: 100%;
            padding: 16px 20px 16px 50px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.9);
            font-size: 16px;
            color: var(--text-primary);
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }

        .form-input:focus {
            outline: none;
            border-color: #667eea;
            background: rgba(255, 255, 255, 0.95);
            box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.15);
        }

        .login-btn {
            width: 100%;
            padding: 18px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 16px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 20px;
        }

        .login-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 32px rgba(102, 126, 234, 0.4);
        }

        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .step-indicator {
            text-align: center;
            margin-bottom: 30px;
            color: rgba(255, 255, 255, 0.9);
            font-size: 14px;
        }

        /* Demo Mode Toggle - Top Right */
        .demo-toggle-container {
            position: fixed;
            top: 25px;
            right: 25px;
            z-index: 1000;
            display: flex;
            align-items: center;
            gap: 12px;
            background: var(--glass-bg);
            backdrop-filter: blur(10px);
            border: 1px solid var(--glass-border);
            border-radius: 50px;
            padding: 12px 20px;
            color: rgba(255, 255, 255, 0.9);
            font-size: 14px;
            font-weight: 500;
            box-shadow: var(--shadow-light);
            transition: all 0.3s ease;
        }

        .demo-toggle-container:hover {
            background: rgba(255, 255, 255, 0.35);
            transform: translateY(-2px);
            box-shadow: var(--shadow-heavy);
        }

        .toggle-switch {
            position: relative;
            width: 50px;
            height: 26px;
            background: rgba(255, 255, 255, 0.3);
            border-radius: 13px;
            cursor: pointer;
            transition: all 0.3s ease;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .toggle-switch.active {
            background: var(--success-color);
        }

        .toggle-slider {
            position: absolute;
            top: 2px;
            left: 2px;
            width: 22px;
            height: 22px;
            background: white;
            border-radius: 50%;
            transition: all 0.3s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }

        .toggle-switch.active .toggle-slider {
            transform: translateX(24px);
        }
    </style>
</head>
<body>
    <!-- Demo Mode Toggle -->
    <div class="demo-toggle-container">
        <span class="demo-mode-label" id="demoModeLabel">{{ 'Demo Mode' if demo_mode else 'Production Mode' }}</span>
        <div class="toggle-switch {{ 'active' if demo_mode else '' }}" id="demoToggle">
            <div class="toggle-slider"></div>
        </div>
    </div>

    <div class="login-container">
        <div class="login-card">
            <div class="logo-section">
                <h1 class="logo-title">vCenter Connection</h1>
                <p class="logo-subtitle">Configure your vCenter Server connection</p>
            </div>

            <div class="step-indicator">
                <i class="fas fa-check-circle" style="color: #48bb78; margin-right: 5px;"></i>
                System Login Complete → 
                <i class="fas fa-cloud" style="margin: 0 5px;"></i>
                vCenter Configuration
            </div>

            <form id="vcenterForm" method="post" class="form-section">
                <div class="form-group">
                    <label for="vcenter_host" class="form-label">vCenter Host</label>
                    <div class="input-with-icon">
                        <i class="fas fa-server input-icon"></i>
                        <input type="text" id="vcenter_host" name="vcenter_host" class="form-input" 
                               placeholder="vcenter.company.com or 192.168.1.100" required>
                    </div>
                </div>

                <div class="form-group">
                    <label for="vcenter_user" class="form-label">vCenter Username</label>
                    <div class="input-with-icon">
                        <i class="fas fa-user-cog input-icon"></i>
                        <input type="text" id="vcenter_user" name="vcenter_user" class="form-input" 
                               placeholder="administrator@vsphere.local" required>
                    </div>
                </div>

                <div class="form-group">
                    <label for="vcenter_pass" class="form-label">vCenter Password</label>
                    <div class="input-with-icon">
                        <i class="fas fa-key input-icon"></i>
                        <input type="password" id="vcenter_pass" name="vcenter_pass" class="form-input" 
                               placeholder="Enter vCenter password" required>
                    </div>
                </div>

                <button type="submit" class="login-btn">
                    <i class="fas fa-plug" style="margin-right: 8px;"></i>
                    Connect to vCenter
                </button>
            </form>
        </div>
    </div>

    <script>
        let isDemoMode = {{ demo_mode | tojson }};
        
        // Toggle demo mode function
        async function toggleDemoMode() {
            const toggle = document.getElementById('demoToggle');
            const label = document.getElementById('demoModeLabel');
            
            // Add loading state
            toggle.style.opacity = '0.6';
            toggle.style.pointerEvents = 'none';
            
            try {
                const response = await fetch('/toggle-demo-mode', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({})
                });
                
                if (response.ok) {
                    const data = await response.json();
                    isDemoMode = data.demo_mode;
                    
                    // Update UI
                    if (isDemoMode) {
                        toggle.classList.add('active');
                        label.textContent = 'Demo Mode';
                    } else {
                        toggle.classList.remove('active');
                        label.textContent = 'Production Mode';
                    }
                    
                    console.log('Demo mode toggled:', isDemoMode);
                } else {
                    console.error('Failed to toggle demo mode');
                }
            } catch (error) {
                console.error('Error toggling demo mode:', error);
            } finally {
                // Remove loading state
                toggle.style.opacity = '1';
                toggle.style.pointerEvents = 'auto';
            }
        }

        // vCenter form submission
        document.getElementById('vcenterForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const btn = this.querySelector('.login-btn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin" style="margin-right: 8px;"></i>Connecting...';
            btn.disabled = true;
            
            const formData = new FormData(this);
            
            try {
                const response = await fetch('/vcenter-login', {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: formData
                });
                
                const data = await response.json();
                
                if (response.ok && data.status === 'success') {
                    window.location.href = data.redirect_url;
                } else {
                    alert(data.error || 'vCenter connection failed. Please try again.');
                }
            } catch (error) {
                console.error('vCenter connection error:', error);
                alert('An error occurred. Please try again.');
            } finally {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        });

        // Add event listener for demo toggle
        const demoToggle = document.getElementById('demoToggle');
        if (demoToggle) {
            demoToggle.addEventListener('click', toggleDemoMode);
            console.log('Demo toggle event listener added');
        }
    </script>
</body>
</html>
    """, username=session.get("username"), demo_mode=DEMO_MODE)


@app.route("/dashboard")
def dashboard():
    if not session.get("username"):
        return redirect(url_for("login"))

    try:
        # Get vCenter information (or mock data)
        templates = get_template_names(
            session["vcenter_host"], session["vcenter_user"], session["vcenter_pass"]
        )
        datacenters = get_datacenters(
            session["vcenter_host"], session["vcenter_user"], session["vcenter_pass"]
        )

        stats = {
            "templates": len(templates),
            "datacenters": len(datacenters),
            "login_time": session.get("login_time", ""),
            "vcenter_host": session.get("vcenter_host", ""),
            "demo_mode": DEMO_MODE,
        }

        return render_template_string(
            open("templates/dashboard.html", "r", encoding="utf-8").read(),
            stats=stats,
            templates=templates[:5],
            session=session,
        )

    except Exception as e:
        flash(f"Error loading dashboard: {str(e)}", "error")
        return redirect(url_for("login"))


@app.route("/provision", methods=["GET", "POST"])
def provision():
    if not session.get("username"):
        # If not authenticated and it's an AJAX POST, return JSON error
        if (
            request.method == "POST"
            and request.headers.get("X-Requested-With") == "XMLHttpRequest"
        ):
            return jsonify({"error": "Not authenticated"}), 401
        return redirect(url_for("login"))

    if request.method == "POST":
        print(
            f"Received POST request to /provision from {session.get('username')}"
        )  # Debug print on server console
        try:
            template = request.form.get("template", "").strip()
            datacenter = request.form.get("datacenter", "").strip()
            cluster = request.form.get("cluster", "").strip()
            network = request.form.get("network", "").strip()

            # Check if individual configuration is enabled
            is_individual_config = request.form.get("individualConfig") == "on"

            ip_map = {}
            individual_nodes_data = None
            if is_individual_config:
                individual_nodes_data_str = request.form.get("individual_nodes_data")
                if not individual_nodes_data_str:
                    raise ValueError("Individual node configuration data is missing.")
                individual_nodes_data = json.loads(individual_nodes_data_str)
                log_queue.put(
                    f"ℹ️ Backend received individual node config: {len(individual_nodes_data)} nodes."
                )
                for i, node in enumerate(individual_nodes_data):
                    log_queue.put(
                        f"   Node {i+1}: Name='{node.get('name')}', Hostname='{node.get('hostname')}', IPs={node.get('ips')}"
                    )
                prefix = "individual-vm"
                count = len(individual_nodes_data)
                if individual_nodes_data:
                    first_node_ips = individual_nodes_data[0].get("ips", {})
                    for nic_key, ip_val in first_node_ips.items():
                        ip_map[nic_key] = ip_val
            else:
                prefix = request.form.get("prefix", "").strip()
                count = int(request.form.get("count", 1))
                hostname_prefix = request.form.get("hostname", "").strip()
                if not all([prefix]):
                    raise ValueError("VM Name Prefix is required for bulk provisioning")
                if count < 1 or count > 50:
                    raise ValueError("Number of VMs must be between 1 and 50")
                if not re.match(r"^[a-zA-Z0-9\-_]+$", prefix):
                    raise ValueError(
                        "Prefix can only contain letters, numbers, hyphens, and underscores"
                    )
                for i in range(1, 10):
                    ip_val = request.form.get(f"ip{i}", "").strip()
                    if ip_val:
                        if not validate_ip(ip_val):
                            raise ValueError(f"Invalid IP address format for NIC {i}")
                        ip_map[f"net{i}"] = ip_val
            if not all([template, datacenter, cluster, network]):
                raise ValueError(
                    "Template, Datacenter, Cluster, and Network are required"
                )
            vcenter_host = session["vcenter_host"]
            vcenter_user = session["vcenter_user"]
            vcenter_pass = session["vcenter_pass"]
            username = session.get("username", "Unknown")
            if DEMO_MODE:
                # ใช้ queue เพื่อรับผลลัพธ์จาก thread
                result_queue = queue.Queue()
                def task():
                    try:
                        current_functions = get_current_functions()
                        demo_provision_func = current_functions.get('provision_vms_demo_mode')
                        if demo_provision_func:
                            individual_data = None
                            if is_individual_config and individual_nodes_data:
                                individual_data = individual_nodes_data
                            result = demo_provision_func(
                                vcenter_host,
                                vcenter_user,
                                vcenter_pass,
                                template,
                                prefix,
                                count,
                                datacenter,
                                cluster,
                                network,
                                ip_map,
                                logger=log_queue.put,
                                individual_nodes_data=individual_data,
                                hostname_prefix=hostname_prefix if not is_individual_config else None,
                            )
                            # ส่ง vms array กลับมาทาง queue
                            if isinstance(result, dict) and 'vms' in result:
                                result_queue.put(result['vms'])
                                log_queue.put(f"📊 VMs data prepared: {len(result['vms'])} VMs")
                                # Debug: แสดง vms data
                                for i, vm in enumerate(result['vms']):
                                    log_queue.put(f"   VM{i+1}: {vm}")
                                log_queue.put("✅ Demo provisioning completed successfully!")
                            else:
                                result_queue.put([])
                                log_queue.put("⚠️ No VMs data in result")
                                log_queue.put(f"Result type: {type(result)}")
                                log_queue.put(f"Result content: {result}")
                        else:
                            result_queue.put([])
                            log_queue.put("⚠️ Demo provision function not found")
                    except Exception as e:
                        result_queue.put([])
                        log_queue.put(f"❌ Demo provision error: {str(e)}")
                t = threading.Thread(target=task, daemon=True)
                t.start()
                # ไม่ต้อง join() เพื่อให้ frontend ได้รับ log ก่อน
                # vms_result = result_queue.get()
                # session['last_provision_vms'] = vms_result
                # return jsonify({'status': 'success', 'message': 'Provisioning completed', 'vms': vms_result})
                
                # ส่ง vms array ผ่าน eventSource เมื่อเสร็จ
                def save_vms_result():
                    global last_provision_vms
                    try:
                        log_queue.put("⏳ Waiting for VMs data...")
                        vms_result = result_queue.get(timeout=60)  # เพิ่ม timeout เป็น 60 วินาที
                        # ใช้ global variable แทน session
                        last_provision_vms = vms_result
                        log_queue.put(f"📊 VMs data saved: {len(vms_result)} VMs")
                        if vms_result:
                            for vm in vms_result:
                                log_queue.put(f"   • {vm.get('name', 'Unknown')}: {vm.get('status', 'Unknown')} - {vm.get('ips', 'No IP')}")
                        else:
                            log_queue.put("⚠️ No VMs data received")
                    except queue.Empty:
                        log_queue.put("⚠️ Timeout waiting for VMs data (60s)")
                        last_provision_vms = []
                    except Exception as e:
                        log_queue.put(f"⚠️ Error waiting for VMs data: {str(e)}")
                        last_provision_vms = []
                
                # เริ่ม thread สำหรับเก็บ vms result
                save_thread = threading.Thread(target=save_vms_result, daemon=True)
                save_thread.start()
            else:
                # Production mode - use real provisioning with per-VM customization
                try:
                    log_queue.put("🏭 PRODUCTION MODE: Starting real VM provisioning with per-VM customization")
                    result = provision_vms(
                        vcenter_host,
                        vcenter_user,
                        vcenter_pass,
                        template,
                        prefix,
                        count,
                        datacenter,
                        cluster,
                        network,
                        ip_map,
                        logger=log_queue.put,
                        timeout_seconds=30,
                        individual_nodes_data=individual_nodes_data if is_individual_config else None,
                    )
                    log_queue.put(f"✅ {result}")
                    logging.info(
                        f"Provisioning completed by {username}: {result}"
                    )
                except Exception as e:
                    # Enhanced error handling for production provisioning
                    error_msg = str(e)
                    log_queue.put(f"❌ ERROR: Provisioning failed: {error_msg}")
                    if "customiz" in error_msg.lower():
                        log_queue.put("❗ Guest Customization failed. Please check that your template has VMware Tools installed, network config is not hardcoded, and OS is supported by vSphere Guest Customization.")
                    elif "vcenter" in error_msg.lower() or "connect" in error_msg.lower():
                        log_queue.put("❗ vCenter connection or resource discovery failed. Please check vCenter credentials, network, and permissions.")
                    else:
                        log_queue.put("❗ An unexpected error occurred during provisioning. Please check logs and vSphere tasks for more details.")
                    logging.error(f"Provisioning failed for user {username}: {error_msg}")
                    return jsonify({"status": "error", "message": error_msg}), 500
            # Add initial logs to queue for immediate streaming
            log_queue.put("🚀 Starting VM provisioning...")
            log_queue.put("📋 Configuration validated successfully")
            
            # Add network zone information if available
            network_zones = request.form.get("networkZones")
            if network_zones:
                try:
                    zones_data = json.loads(network_zones)
                    log_queue.put("🌐 Detected network zones:")
                    for nic, zone in zones_data.items():
                        log_queue.put(f"   {nic.upper()}: {zone}")
                except:
                    pass

            message = "Provisioning started! Check the logs below."
            if DEMO_MODE:
                message = "DEMO: Provisioning started! This is simulated data."

            # Return JSON response for successful POST via AJAX
            return (
                jsonify({"message": message, "status": "success"}),
                202,
            )  # 202 Accepted

        except ValueError as e:
            # Return JSON error for AJAX requests
            print(f"Validation error: {str(e)}")  # Debug print on server console
            return jsonify({"error": str(e), "status": "error"}), 400  # Bad Request
        except Exception as e:
            # Top-level error handler for form/validation errors
            error_msg = str(e)
            log_queue.put(f"❌ ERROR: {error_msg}")
            return jsonify({"status": "error", "message": error_msg}), 400

    # For GET requests, render the HTML template
    return render_template_string(
        open("templates/provision.html", "r", encoding="utf-8").read()
    )


@app.route("/logout")
def logout():
    username = session.get("username")
    session.clear()
    if username:
        logging.info(f"User {username} logged out")
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login"))


@app.route("/stream")
def stream():
    def event_stream():
        while True:
            try:
                message = log_queue.get(timeout=30)
                # Clean the message and ensure proper encoding
                if message:
                    # Escape newlines in the message for proper SSE format
                    clean_message = str(message).replace('\n', '\\n').replace('\r', '\\r')
                    yield f"data: {clean_message}\n\n"
                else:
                    yield f"data: \n\n"  # Keep connection alive
            except queue.Empty:
                yield f"data: \n\n"  # Keep connection alive with ping
            except Exception as e:
                logging.error(f"EventSource error: {e}")
                yield f"data: ❌ Stream error: {e}\n\n"
                break

    response = Response(event_stream(), mimetype="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Cache-Control'
    return response


@app.route("/api/templates")
def get_templates():
    if not session.get("username"):
        return jsonify({"error": "Not authenticated"}), 401

    try:
        templates = get_template_names(
            session["vcenter_host"], session["vcenter_user"], session["vcenter_pass"]
        )
        return jsonify({"templates": templates})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/datacenters")
def get_datacenters_api():
    if not session.get("username"):
        return jsonify({"error": "Not authenticated"}), 401

    try:
        datacenters = get_datacenters(
            session["vcenter_host"], session["vcenter_user"], session["vcenter_pass"]
        )
        return jsonify({"datacenters": datacenters})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/clusters")
def get_clusters_api():
    datacenter = request.args.get("datacenter")
    if not session.get("username") or not datacenter:
        return jsonify({"error": "Not authenticated or missing datacenter"}), 401

    try:
        clusters = get_clusters(
            session["vcenter_host"],
            session["vcenter_user"],
            session["vcenter_pass"],
            datacenter,
        )
        return jsonify({"clusters": clusters})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/networks")
def get_networks_api():
    datacenter = request.args.get("datacenter")
    if not session.get("username") or not datacenter:
        return jsonify({"error": "Not authenticated or missing datacenter"}), 401

    try:
        networks = get_networks(
            session["vcenter_host"],
            session["vcenter_user"],
            session["vcenter_pass"],
            datacenter,
        )
        return jsonify({"networks": networks})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/nic-count")
def get_nic_count_api():
    template = request.args.get("template")
    if not session.get("username") or not template:
        return jsonify({"error": "Not authenticated or missing template"}), 401

    try:
        count = get_nic_count(
            session["vcenter_host"],
            session["vcenter_user"],
            session["vcenter_pass"],
            template,
        )
        return jsonify({"count": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/api/last-provision-vms')
def api_last_provision_vms():
    global last_provision_vms
    return jsonify({'vms': last_provision_vms})


if __name__ == "__main__":
    mode = "DEMO MODE" if DEMO_MODE else "PRODUCTION MODE"
    print(f"🚀 Starting VM Provisioning Application - {mode}")
    print("📋 Server Details:")
    print(f"   - Host: 127.0.0.1")
    print(f"   - Port: 5051")
    print(f"   - URL: http://localhost:5051")
    print("📝 Login Options:")
    print(f"   - Username: admin | Password: admin123")
    print(f"   - Username: demo  | Password: demo123")

    if DEMO_MODE:
        print("🎭 DEMO MODE ENABLED:")
        print("   - No real vCenter connection required")
        print("   - All data is simulated/mockup")
        print("   - Perfect for testing and demonstration")
        print("   - Use any vCenter credentials (will be ignored)")
    else:
        print("⚡ PRODUCTION MODE:")
        print("   - Real vCenter connection required")
        print("   - Provide valid vCenter credentials")

    print("🔧 Press Ctrl+C to stop the server")
    print("-" * 60)

    app.run(debug=True, host="127.0.0.1", port=5051, threaded=True)
