#!/usr/bin/env python3
"""
Watchdog v4.3 - Web Interface
=============================
Multi-user, multi-language Flask web application.
Features: GitHub updates, live status, health checks, themes.

© 2026 MaraXa
"""

import os
import json
import secrets
import csv
import io
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, session,
    url_for, jsonify, flash, Response, send_file, g
)
from werkzeug.security import generate_password_hash

from constants import (
    CONFIG_FILE, VERSION, COPYRIGHT, SESSION_LIFETIME_HOURS,
    MAX_GROUPS, MIN_FAIL_COUNT, MAX_FAIL_COUNT,
    MIN_OFF_TIME, MAX_OFF_TIME, MIN_CHECK_INTERVAL, MAX_CHECK_INTERVAL,
    BACKUP_DIR, LANGUAGES, DEFAULT_LANGUAGE, ROLES,
    ROLE_ADMIN, ROLE_OPERATOR, ROLE_VIEWER, SSL_DIR, INSTALL_DIR,
    AJAX_POLL_INTERVAL, VALID_GPIO_PINS, GPIO_PIN_INFO, MAX_OUTLETS,
    TIMEZONES, DEFAULT_TIMEZONE, THEMES, DEFAULT_THEME,
    CHECK_TYPES, CHECK_TYPE_PING, CHECK_TYPE_HTTP, CHECK_TYPE_TCP,
    DEFAULT_LATENCY_WARNING, DEFAULT_LATENCY_CRITICAL
)
from config_validator import load_config, save_config, ConfigValidator, ConfigError
from gpio_manager import gpio_manager, GPIOCommand
from logger import log, get_log_page
from notifier import get_notifier, configure_notifier
from users import user_manager
from updater import updater
from health_checker import health_checker
from audit import audit_log
from i18n import i18n, t, set_language, get_language
from scheduler import scheduler
from network_manager import network_manager
from stats import ping_stats


# Flask app setup
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=SESSION_LIFETIME_HOURS)


# ==================== Request Hooks ====================

@app.before_request
def before_request():
    """Set up request context."""
    # Set language from session or user preference
    if 'language' in session:
        set_language(session['language'])
    elif 'username' in session:
        user = user_manager.get_user_info(session['username'])
        if user:
            set_language(user.get('language', DEFAULT_LANGUAGE))
            session['language'] = user.get('language', DEFAULT_LANGUAGE)
    else:
        set_language(DEFAULT_LANGUAGE)
    
    # Make common data available to templates
    g.language = get_language()
    g.languages = LANGUAGES
    g.t = t
    g.version = VERSION
    g.copyright = COPYRIGHT


@app.context_processor
def inject_template_globals():
    """Inject globals into all templates."""
    return {
        't': t,
        'language': get_language(),
        'languages': LANGUAGES,
        'version': VERSION,
        'copyright': COPYRIGHT,
        'csrf_token': generate_csrf_token,
        'user': session.get('user_info'),
        'has_permission': lambda p: session.get('user_info', {}).get('permissions', []) and p in session.get('user_info', {}).get('permissions', [])
    }


# ==================== CSRF Protection ====================

def generate_csrf_token():
    """Generate CSRF token for forms."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']


def validate_csrf_token():
    """Validate CSRF token from form or header."""
    token = session.get('_csrf_token', '')
    form_token = request.form.get('_csrf_token', '')
    header_token = request.headers.get('X-CSRF-Token', '')
    return token and (token == form_token or token == header_token)


def csrf_protect(f):
    """Decorator to require CSRF token on POST requests."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'POST':
            if not validate_csrf_token():
                log("SECURITY", f"CSRF validation failed from {request.remote_addr}")
                if request.is_json:
                    return jsonify({"error": "CSRF validation failed"}), 403
                flash(t("errors.invalid_request"), "error")
                return redirect(request.referrer or url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


# ==================== Authentication ====================

def login_required(f):
    """Decorator to require login."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            if request.is_json:
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def permission_required(permission):
    """Decorator to require specific permission."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'username' not in session:
                if request.is_json:
                    return jsonify({"error": "Unauthorized"}), 401
                return redirect(url_for('login'))
            
            user_info = session.get('user_info', {})
            permissions = user_info.get('permissions', [])
            
            if permission not in permissions:
                if request.is_json:
                    return jsonify({"error": "Forbidden"}), 403
                flash(t("errors.forbidden"), "error")
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated
    return decorator


def admin_required(f):
    """Shortcut for admin permission."""
    return permission_required('manage_users')(f)


@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = user_manager.authenticate(username, password)
        
        if user:
            session.permanent = True
            session['username'] = username
            session['user_info'] = user
            session['language'] = user.get('language', DEFAULT_LANGUAGE)
            
            audit_log.log_login(username, request.remote_addr)
            log("AUTH", f"Login: {username} from {request.remote_addr}")
            
            return redirect(url_for('dashboard'))
        
        audit_log.log_login_failed(username, request.remote_addr)
        log("AUTH", f"Login failed: {username} from {request.remote_addr}")
        return render_template('login.html', error=t("auth.invalid_credentials"), version=VERSION)
    
    return render_template('login.html', version=VERSION)


@app.route('/logout')
def logout():
    username = session.get('username', 'unknown')
    audit_log.log_logout(username, request.remote_addr)
    session.clear()
    return redirect(url_for('login'))


# ==================== Dashboard ====================

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        cfg = load_config()
        enabled_groups = [g for g in cfg.get("groups", []) if g.get("enabled", False)]
        
        # Get stats summaries if feature enabled
        stats_summaries = {}
        if cfg.get("features", {}).get("ping_stats", True):
            stats_summaries = ping_stats.get_all_groups_summary()
        
        return render_template('dashboard.html',
                             groups=enabled_groups,
                             outlets=cfg.get("outlets", {}),
                             config=cfg,
                             stats_summaries=stats_summaries,
                             live_status_enabled=cfg.get("features", {}).get("live_status", True),
                             poll_interval=AJAX_POLL_INTERVAL)
    except ConfigError as e:
        flash(f"{t('common.error')}: {e.message}", "error")
        return render_template('dashboard.html', groups=[], outlets={}, config={})


@app.route('/api/status')
@login_required
def api_status():
    """API endpoint for live status updates."""
    try:
        cfg = load_config()
        
        if not cfg.get("features", {}).get("live_status", True):
            return jsonify({"error": "Feature disabled"}), 403
        
        enabled_groups = [g for g in cfg.get("groups", []) if g.get("enabled", False)]
        
        # Get pending commands
        pending = gpio_manager.get_pending_commands()
        
        # Get stats
        stats = ping_stats.get_all_groups_summary()
        
        return jsonify({
            "groups": enabled_groups,
            "pending_commands": len(pending),
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/control', methods=['POST'])
@login_required
@permission_required('control_relays')
@csrf_protect
def control():
    """Queue GPIO control command."""
    try:
        cfg = load_config()
        group_idx = int(request.form.get('group', 0))
        action = request.form.get('action', '')
        
        if group_idx >= len(cfg.get("groups", [])):
            flash(t("common.error"), "error")
            return redirect(url_for('dashboard'))
        
        group = cfg["groups"][group_idx]
        group_name = group.get("name", "Unknown")
        outlet_key = group.get("outlet")
        
        command_map = {
            "on": GPIOCommand.ON,
            "off": GPIOCommand.OFF,
            "restart": GPIOCommand.RESTART
        }
        
        if action not in command_map:
            flash(t("common.error"), "error")
            return redirect(url_for('dashboard'))
        
        # Audit log
        audit_log.log_relay_control(
            session['username'], 
            group_name, 
            action.upper(),
            request.remote_addr
        )
        
        # Queue command
        cmd_id = gpio_manager.queue_command(
            group_name=group_name,
            outlet_key=outlet_key,
            command=command_map[action],
            off_time=group.get("off_time", 10),
            source=f"web:{session['username']}"
        )
        
        if cmd_id:
            flash(t("control.command_queued"), "success")
        else:
            flash(t("control.command_error"), "error")
        
    except Exception as e:
        log("ERROR", f"Control error: {e}")
        flash(f"{t('common.error')}: {e}", "error")
    
    return redirect(url_for('dashboard'))


# ==================== Server Groups ====================

@app.route('/groups', methods=['GET', 'POST'])
@login_required
@permission_required('manage_groups')
@csrf_protect
def groups():
    if request.method == 'POST':
        try:
            cfg = load_config()
            new_groups = []
            
            max_groups = cfg.get("max_groups", MAX_GROUPS)
            for i in range(max_groups):
                if request.form.get(f'group_{i}_exists'):
                    servers_input = request.form.get(f'group_{i}_servers', '')
                    servers = [s.strip() for s in servers_input.replace(',', ' ').split() if s.strip()]
                    
                    fail_count = int(request.form.get(f'group_{i}_fail_count', 3))
                    fail_count = max(MIN_FAIL_COUNT, min(MAX_FAIL_COUNT, fail_count))
                    
                    off_time = int(request.form.get(f'group_{i}_off_time', 10))
                    off_time = max(MIN_OFF_TIME, min(MAX_OFF_TIME, off_time))
                    
                    check_port = int(request.form.get(f'group_{i}_check_port', 80))
                    latency_warning = int(request.form.get(f'group_{i}_latency_warning', DEFAULT_LATENCY_WARNING))
                    latency_critical = int(request.form.get(f'group_{i}_latency_critical', DEFAULT_LATENCY_CRITICAL))
                    
                    # Preserve existing schedules
                    old_group = next((g for g in cfg.get("groups", []) 
                                     if g.get("name") == request.form.get(f'group_{i}_name')), {})
                    
                    new_groups.append({
                        "name": request.form.get(f'group_{i}_name', f'Group {i+1}'),
                        "servers": servers,
                        "outlet": request.form.get(f'group_{i}_outlet', 'outlet_1'),
                        "fail_count": fail_count,
                        "off_time": off_time,
                        "enabled": request.form.get(f'group_{i}_enabled') == 'true',
                        "check_type": request.form.get(f'group_{i}_check_type', CHECK_TYPE_PING),
                        "check_port": check_port,
                        "require_all": request.form.get(f'group_{i}_require_all') == 'true',
                        "latency_warning": latency_warning,
                        "latency_critical": latency_critical,
                        "schedules": old_group.get("schedules", [])
                    })
            
            cfg['groups'] = new_groups
            save_config(cfg, backup=True)
            
            audit_log.log_config_change(session['username'], "groups", 
                                       f"Updated {len(new_groups)} groups", request.remote_addr)
            log("CONFIG", f"Groups updated by {session['username']}")
            
            flash(t("groups.saved"), "success")
            
        except Exception as e:
            log("ERROR", f"Groups save failed: {e}")
            flash(f"{t('common.error')}: {e}", "error")
    
    cfg = load_config()
    return render_template('groups.html', config=cfg)


# ==================== Outlets Management ====================

@app.route('/outlets')
@login_required
@permission_required('manage_system')
def outlets():
    """Manage GPIO outlets."""
    cfg = load_config()
    
    # Get used pins
    used_pins = set()
    for outlet in cfg.get("outlets", {}).values():
        used_pins.add(outlet.get("gpio_pin"))
    
    # Get outlets used by groups
    used_outlets = set()
    for group in cfg.get("groups", []):
        if group.get("outlet"):
            used_outlets.add(group["outlet"])
    
    return render_template('outlets.html',
                         outlets=cfg.get("outlets", {}),
                         groups=cfg.get("groups", []),
                         gpio_info=GPIO_PIN_INFO,
                         used_pins=used_pins,
                         used_outlets=used_outlets,
                         valid_pins=VALID_GPIO_PINS)


@app.route('/outlets/add', methods=['POST'])
@login_required
@permission_required('manage_system')
@csrf_protect
def outlets_add():
    """Add new outlet."""
    try:
        cfg = load_config()
        
        outlet_name = request.form.get('outlet_name', '').strip()
        gpio_pin = int(request.form.get('gpio_pin', 0))
        
        if not outlet_name:
            flash(t("common.error") + ": Missing name", "error")
            return redirect(url_for('outlets'))
        
        if gpio_pin not in VALID_GPIO_PINS:
            flash(t("common.error") + ": Invalid GPIO pin", "error")
            return redirect(url_for('outlets'))
        
        # Check if pin is already used
        for outlet in cfg.get("outlets", {}).values():
            if outlet.get("gpio_pin") == gpio_pin:
                flash(t("common.error") + ": GPIO pin already in use", "error")
                return redirect(url_for('outlets'))
        
        # Check max outlets
        if len(cfg.get("outlets", {})) >= MAX_OUTLETS:
            flash(t("common.error") + f": Maximum {MAX_OUTLETS} outlets", "error")
            return redirect(url_for('outlets'))
        
        # Generate outlet key
        outlet_num = len(cfg.get("outlets", {})) + 1
        outlet_key = f"outlet_{outlet_num}"
        
        # Find unique key
        while outlet_key in cfg.get("outlets", {}):
            outlet_num += 1
            outlet_key = f"outlet_{outlet_num}"
        
        # Add outlet
        if "outlets" not in cfg:
            cfg["outlets"] = {}
        
        cfg["outlets"][outlet_key] = {
            "name": outlet_name,
            "gpio_pin": gpio_pin
        }
        
        save_config(cfg, backup=True)
        audit_log.log_config_change(session['username'], "outlets", 
                                   f"Added {outlet_key} (GPIO {gpio_pin})", request.remote_addr)
        flash(t("common.success"), "success")
        
    except Exception as e:
        log("ERROR", f"Add outlet failed: {e}")
        flash(f"{t('common.error')}: {e}", "error")
    
    return redirect(url_for('outlets'))


@app.route('/outlets/delete/<outlet_key>', methods=['POST'])
@login_required
@permission_required('manage_system')
@csrf_protect
def outlets_delete(outlet_key):
    """Delete outlet."""
    try:
        cfg = load_config()
        
        if outlet_key not in cfg.get("outlets", {}):
            flash(t("common.error"), "error")
            return redirect(url_for('outlets'))
        
        # Check if outlet is used by any group
        for group in cfg.get("groups", []):
            if group.get("outlet") == outlet_key:
                flash(t("common.error") + f": Outlet is used by group '{group.get('name')}'", "error")
                return redirect(url_for('outlets'))
        
        # Delete
        gpio_pin = cfg["outlets"][outlet_key].get("gpio_pin")
        del cfg["outlets"][outlet_key]
        
        save_config(cfg, backup=True)
        audit_log.log_config_change(session['username'], "outlets",
                                   f"Deleted {outlet_key} (GPIO {gpio_pin})", request.remote_addr)
        flash(t("common.success"), "success")
        
    except Exception as e:
        log("ERROR", f"Delete outlet failed: {e}")
        flash(f"{t('common.error')}: {e}", "error")
    
    return redirect(url_for('outlets'))


@app.route('/outlets/rename/<outlet_key>', methods=['POST'])
@login_required
@permission_required('manage_system')
@csrf_protect
def outlets_rename(outlet_key):
    """Rename outlet."""
    try:
        cfg = load_config()
        
        if outlet_key not in cfg.get("outlets", {}):
            flash(t("common.error"), "error")
            return redirect(url_for('outlets'))
        
        new_name = request.form.get('new_name', '').strip()
        if not new_name:
            flash(t("common.error"), "error")
            return redirect(url_for('outlets'))
        
        old_name = cfg["outlets"][outlet_key].get("name")
        cfg["outlets"][outlet_key]["name"] = new_name
        
        save_config(cfg, backup=True)
        audit_log.log_config_change(session['username'], "outlets",
                                   f"Renamed {outlet_key}: '{old_name}' → '{new_name}'", request.remote_addr)
        
    except Exception as e:
        log("ERROR", f"Rename outlet failed: {e}")
        flash(f"{t('common.error')}: {e}", "error")
    
    return redirect(url_for('outlets'))


# ==================== Scheduler ====================

@app.route('/scheduler', methods=['GET', 'POST'])
@login_required
@permission_required('manage_scheduler')
@csrf_protect
def scheduler_page():
    cfg = load_config()
    
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            group_name = request.form.get('group_name')
            
            if action == 'add':
                day = int(request.form.get('day', 0))
                hour = int(request.form.get('hour', 0))
                minute = int(request.form.get('minute', 0))
                
                group_scheduler = scheduler.get_group(group_name)
                group_scheduler.add_schedule(day, hour, minute)
                
                # Save to config
                cfg['groups'] = scheduler.save_to_config(cfg.get('groups', []))
                save_config(cfg, backup=True)
                
                audit_log.log_config_change(session['username'], "scheduler",
                                           f"Added schedule for {group_name}", request.remote_addr)
                
            elif action == 'remove':
                index = int(request.form.get('index', 0))
                group_scheduler = scheduler.get_group(group_name)
                group_scheduler.remove_schedule(index)
                
                cfg['groups'] = scheduler.save_to_config(cfg.get('groups', []))
                save_config(cfg, backup=True)
                
                audit_log.log_config_change(session['username'], "scheduler",
                                           f"Removed schedule from {group_name}", request.remote_addr)
            
            elif action == 'toggle':
                index = int(request.form.get('index', 0))
                enabled = request.form.get('enabled') == 'true'
                group_scheduler = scheduler.get_group(group_name)
                group_scheduler.update_schedule(index, enabled=enabled)
                
                cfg['groups'] = scheduler.save_to_config(cfg.get('groups', []))
                save_config(cfg, backup=True)
            
            flash(t("common.success"), "success")
            
        except Exception as e:
            log("ERROR", f"Scheduler error: {e}")
            flash(f"{t('common.error')}: {e}", "error")
    
    # Load schedules from config
    scheduler.load_from_config(cfg.get('groups', []))
    all_schedules = scheduler.get_all_schedules()
    
    enabled_groups = [g.get("name") for g in cfg.get("groups", []) if g.get("enabled")]
    
    return render_template('scheduler.html', 
                         schedules=all_schedules,
                         groups=enabled_groups,
                         config=cfg)


# ==================== Statistics ====================

@app.route('/stats')
@login_required
@permission_required('view_stats')
def stats_page():
    cfg = load_config()
    
    if not cfg.get("features", {}).get("ping_stats", True):
        flash(t("common.disabled"), "info")
        return redirect(url_for('dashboard'))
    
    # Support both single group and multiple groups
    groups_param = request.args.get('groups', '')
    single_group = request.args.get('group', '')
    days = int(request.args.get('days', 1))
    
    enabled_groups = [g.get("name") for g in cfg.get("groups", []) if g.get("enabled")]
    
    # Parse selected groups
    if groups_param:
        selected_groups = [g.strip() for g in groups_param.split(',') if g.strip() in enabled_groups]
    elif single_group:
        selected_groups = [single_group] if single_group in enabled_groups else []
    else:
        # Default to first group
        selected_groups = [enabled_groups[0]] if enabled_groups else []
    
    # Get stats for all selected groups
    stats_data = {}
    combined_chart_data = {}
    
    for group_name in selected_groups:
        group_stats = ping_stats.get_stats(group_name, days)
        stats_data[group_name] = group_stats
        
        # Prepare chart data with group name prefix
        chart_data = group_stats.get("chart_data", {})
        
        # If multiple groups, use group name as key
        # If single group with multiple servers, use server names
        if len(selected_groups) > 1:
            # Multi-group comparison: one line per group (average)
            combined_chart_data[group_name] = {
                "labels": chart_data.get("labels", []),
                "availability": chart_data.get("availability", []),
                "response_times": chart_data.get("response_times", [])
            }
        else:
            # Single group: show per-server data if available
            servers = chart_data.get("servers", {})
            servers_avail = chart_data.get("servers_availability", {})
            
            if servers and len(servers) > 1:
                # Multiple servers in one group - use per-server data
                for server in servers.keys():
                    combined_chart_data[server] = {
                        "labels": chart_data.get("labels", []),
                        "availability": servers_avail.get(server, chart_data.get("availability", [])),
                        "response_times": servers.get(server, [])
                    }
            else:
                # Single server or no per-server data
                combined_chart_data[group_name] = {
                    "labels": chart_data.get("labels", []),
                    "availability": chart_data.get("availability", []),
                    "response_times": chart_data.get("response_times", [])
                }
    
    return render_template('stats.html',
                         groups=enabled_groups,
                         selected_groups=selected_groups,
                         selected_days=days,
                         stats=stats_data,
                         combined_chart_data=combined_chart_data)


@app.route('/api/stats/<group_name>')
@login_required
@permission_required('view_stats')
def api_stats(group_name):
    """API endpoint for stats data."""
    days = int(request.args.get('days', 1))
    stats_data = ping_stats.get_stats(group_name, days)
    return jsonify(stats_data)


# ==================== Users Management ====================

@app.route('/users')
@login_required
@permission_required('manage_users')
def users_list():
    users = user_manager.list_users()
    return render_template('users.html', users=users, roles=ROLES)


@app.route('/users/add', methods=['POST'])
@login_required
@permission_required('manage_users')
@csrf_protect
def users_add():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    role = request.form.get('role', ROLE_VIEWER)
    language = request.form.get('language', DEFAULT_LANGUAGE)
    
    success, message = user_manager.create_user(username, password, role, language)
    
    if success:
        audit_log.log_user_change(session['username'], username, "Created user", request.remote_addr)
        flash(t("common.success"), "success")
    else:
        flash(message, "error")
    
    return redirect(url_for('users_list'))


@app.route('/users/edit/<username>', methods=['POST'])
@login_required
@permission_required('manage_users')
@csrf_protect
def users_edit(username):
    role = request.form.get('role')
    language = request.form.get('language')
    active = request.form.get('active') == 'true'
    
    success, message = user_manager.update_user(username, role=role, language=language, active=active)
    
    if success:
        audit_log.log_user_change(session['username'], username, "Updated user", request.remote_addr)
        flash(t("common.success"), "success")
    else:
        flash(message, "error")
    
    return redirect(url_for('users_list'))


@app.route('/users/delete/<username>', methods=['POST'])
@login_required
@permission_required('manage_users')
@csrf_protect
def users_delete(username):
    if username == session.get('username'):
        flash(t("users.cannot_delete_self"), "error")
        return redirect(url_for('users_list'))
    
    success, message = user_manager.delete_user(username)
    
    if success:
        audit_log.log_user_change(session['username'], username, "Deleted user", request.remote_addr)
        flash(t("common.success"), "success")
    else:
        flash(message, "error")
    
    return redirect(url_for('users_list'))


@app.route('/users/reset-password/<username>', methods=['POST'])
@login_required
@permission_required('manage_users')
@csrf_protect
def users_reset_password(username):
    new_password = request.form.get('new_password', '')
    
    success, message = user_manager.reset_password(username, new_password)
    
    if success:
        audit_log.log_password_change(session['username'], username, request.remote_addr)
        flash(t("common.success"), "success")
    else:
        flash(message, "error")
    
    return redirect(url_for('users_list'))


# ==================== My Account ====================

@app.route('/account', methods=['GET', 'POST'])
@login_required
@csrf_protect
def account():
    username = session['username']
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'change_password':
            current = request.form.get('current_password', '')
            new_pass = request.form.get('new_password', '')
            confirm = request.form.get('confirm_password', '')
            
            if new_pass != confirm:
                flash(t("account.passwords_mismatch"), "error")
            else:
                success, message = user_manager.change_password(username, current, new_pass)
                if success:
                    audit_log.log_password_change(username, ip=request.remote_addr)
                    flash(t("account.password_changed"), "success")
                else:
                    flash(message, "error")
        
        elif action == 'change_language':
            language = request.form.get('language', DEFAULT_LANGUAGE)
            user_manager.update_user(username, language=language)
            session['language'] = language
            set_language(language)
            flash(t("common.success"), "success")
        
        elif action == 'generate_token':
            token = user_manager.generate_api_token(username)
            if token:
                flash(f"Token: {token}", "info")
        
        elif action == 'revoke_token':
            user_manager.revoke_api_token(username)
            flash(t("common.success"), "success")
    
    user = user_manager.get_user_info(username)
    return render_template('account.html', user=user)


# ==================== Audit Log ====================

@app.route('/audit')
@login_required
@permission_required('view_audit')
def audit_page():
    event_filter = request.args.get('event')
    user_filter = request.args.get('user')
    
    entries = audit_log.get_formatted_entries(
        limit=200,
        language=get_language(),
        event_type=event_filter,
        username=user_filter
    )
    
    return render_template('audit.html', entries=entries)


# ==================== Logs ====================

@app.route('/logs')
@login_required
@permission_required('view_logs')
def logs():
    page = int(request.args.get('page', 0))
    errors_only = request.args.get('errors_only', '0') == '1'
    autorefresh = request.args.get('autorefresh', '0') == '1'
    refresh_interval = int(request.args.get('refresh_interval', 5))
    
    try:
        cfg = load_config()
        lines_per_page = cfg.get('log_view_lines', 50)
    except:
        lines_per_page = 50
    
    lines, current_page, total_pages = get_log_page(page, lines_per_page)
    
    formatted = []
    for line in lines:
        line = line.strip()
        css_class = ""
        is_error = False
        
        if 'RESET' in line or 'power cut' in line.lower():
            css_class = "reset"
            is_error = True
        elif 'ERROR' in line:
            css_class = "error"
            is_error = True
        elif 'FAIL' in line or 'unreachable' in line:
            css_class = "fail"
            is_error = True
        elif 'WARNING' in line or 'latency' in line.lower():
            css_class = "warning"
            is_error = True
        elif 'INIT' in line or 'SHUTDOWN' in line or 'CONFIG' in line or 'MANUAL' in line or 'SCHEDULE' in line:
            css_class = "success"
        
        # Filter if errors_only
        if errors_only and not is_error:
            continue
        
        formatted.append({'text': line, 'class': css_class})
    
    return render_template('logs.html',
                         formatted_lines=formatted,
                         current_page=current_page,
                         total_pages=total_pages,
                         errors_only=errors_only,
                         autorefresh=autorefresh,
                         refresh_interval=refresh_interval)


# ==================== Network, System, SMTP, Backups - similar to v3 ====================
# (Keeping these routes similar but with i18n and audit logging)

@app.route('/network', methods=['GET', 'POST'])
@login_required
@permission_required('manage_network')
@csrf_protect
def network():
    cfg = load_config()
    
    # Get current system network config
    current = network_manager.get_current_config()
    interfaces = network_manager.get_interfaces()
    pending_change = network_manager.get_pending_change()
    rollback_timeout = network_manager.ROLLBACK_TIMEOUT
    redirect_to = None
    new_ip = None
    
    if request.method == 'POST':
        try:
            if 'network' not in cfg:
                cfg['network'] = {}
            
            # Get form data
            network_config = {
                "interface": request.form.get('interface', current['interface']),
                "mode": request.form.get('network_mode', 'dhcp'),
                "static_ip": request.form.get('static_ip', ''),
                "netmask": request.form.get('netmask', '255.255.255.0'),
                "gateway": request.form.get('gateway', ''),
                "dns_servers": [s.strip() for s in request.form.get('dns_servers', '').split() if s.strip()]
            }
            
            # Save to Watchdog config
            cfg['network']['mode'] = network_config['mode']
            cfg['network']['static_ip'] = network_config['static_ip']
            cfg['network']['netmask'] = network_config['netmask']
            cfg['network']['gateway'] = network_config['gateway']
            cfg['network']['dns_servers'] = network_config['dns_servers']
            cfg['network']['interface'] = network_config['interface']
            
            save_config(cfg, backup=True)
            
            # Check if IP is changing
            old_ip = current.get('ip_address', '')
            new_ip = network_config['static_ip'] if network_config['mode'] == 'static' else None
            ip_changing = new_ip and new_ip != old_ip
            
            # Always apply to system
            success, message = network_manager.apply_config(network_config, with_rollback=True)
            
            if success:
                flash(message, "warning")
                audit_log.log_config_change(session['username'], "network_system", network_config.get('static_ip', 'DHCP'), request.remote_addr)
                log("NETWORK", f"Network config applied by {session['username']}: {network_config}")
                
                # If IP changed, prepare redirect
                if ip_changing and new_ip:
                    # Get current port
                    port = cfg.get('system', {}).get('web_port', 80)
                    ssl = cfg.get('system', {}).get('ssl_enabled', False)
                    protocol = 'https' if ssl else 'http'
                    
                    if port == 80 or (ssl and port == 443):
                        redirect_to = f"{protocol}://{new_ip}/network"
                    else:
                        redirect_to = f"{protocol}://{new_ip}:{port}/network"
            else:
                flash(f"{t('common.error')}: {message}", "error")
            
            # Refresh current config
            current = network_manager.get_current_config()
            pending_change = network_manager.get_pending_change()
            
        except Exception as e:
            flash(f"{t('common.error')}: {e}", "error")
            log("ERROR", f"Network config error: {e}")
    
    return render_template('network.html', 
                         config=cfg, 
                         current=current,
                         interfaces=interfaces,
                         pending_change=pending_change,
                         rollback_timeout=rollback_timeout,
                         redirect_to=redirect_to,
                         new_ip=new_ip)


@app.route('/network/confirm', methods=['POST'])
@login_required
@permission_required('manage_network')
@csrf_protect
def network_confirm():
    """Confirm pending network configuration."""
    if network_manager.confirm_config():
        flash("Konfigurace potvrzena!" if get_language() == 'cs' else "Configuration confirmed!", "success")
        log("NETWORK", f"Network config confirmed by {session['username']}")
    else:
        flash("Žádná čekající konfigurace" if get_language() == 'cs' else "No pending configuration", "info")
    return redirect(url_for('network'))


@app.route('/network/cancel', methods=['POST'])
@login_required
@permission_required('manage_network')
@csrf_protect
def network_cancel():
    """Cancel pending network configuration and restore backup."""
    if network_manager.cancel_config():
        flash("Původní konfigurace obnovena" if get_language() == 'cs' else "Original configuration restored", "success")
        log("NETWORK", f"Network config cancelled by {session['username']}")
    else:
        flash("Žádná čekající konfigurace" if get_language() == 'cs' else "No pending configuration", "info")
    return redirect(url_for('network'))


@app.route('/system', methods=['GET', 'POST'])
@login_required
@permission_required('manage_system')
@csrf_protect
def system():
    if request.method == 'POST':
        try:
            cfg = load_config()
            old_port = cfg.get('system', {}).get('web_port', 80)
            old_ssl = cfg.get('system', {}).get('ssl_enabled', False)
            
            if 'system' not in cfg:
                cfg['system'] = {}
            if 'features' not in cfg:
                cfg['features'] = {}
            
            cfg['system']['hostname'] = request.form.get('hostname', 'watchdog')
            cfg['system']['web_port'] = int(request.form.get('web_port', 80))
            cfg['system']['debug'] = request.form.get('debug') == 'true'
            cfg['system']['ssl_enabled'] = request.form.get('ssl_enabled') == 'true'
            cfg['system']['ssl_port'] = int(request.form.get('ssl_port', 443))
            cfg['system']['default_language'] = request.form.get('default_language', DEFAULT_LANGUAGE)
            cfg['system']['timezone'] = request.form.get('timezone', DEFAULT_TIMEZONE)
            
            check_interval = int(request.form.get('check_interval', 10))
            cfg['check_interval'] = max(MIN_CHECK_INTERVAL, min(MAX_CHECK_INTERVAL, check_interval))
            
            ntp_input = request.form.get('ntp_servers', '')
            cfg['system']['ntp_servers'] = [s.strip() for s in ntp_input.split() if s.strip()]
            
            cfg['log_max_kb'] = int(request.form.get('log_max_kb', 512))
            cfg['log_view_lines'] = int(request.form.get('log_view_lines', 50))
            cfg['audit_retention_days'] = int(request.form.get('audit_retention_days', 90))
            cfg['stats_retention_days'] = int(request.form.get('stats_retention_days', 30))
            
            # Features
            cfg['features']['live_status'] = request.form.get('live_status') == 'true'
            cfg['features']['ping_stats'] = request.form.get('ping_stats') == 'true'
            
            # Apply timezone to system
            timezone = cfg['system'].get('timezone', DEFAULT_TIMEZONE)
            try:
                import subprocess
                subprocess.run(['timedatectl', 'set-timezone', timezone], capture_output=True)
            except:
                pass
            
            # Generate SSL certificate if SSL enabled and no cert exists
            new_ssl = cfg['system']['ssl_enabled']
            new_ssl_port = cfg['system']['ssl_port']
            new_port = cfg['system']['web_port']
            
            if new_ssl and not old_ssl:
                ssl_ok = generate_ssl_certificate()
                if not ssl_ok:
                    flash(t("common.error") + ": Failed to generate SSL certificate", "error")
                    cfg['system']['ssl_enabled'] = False
                    new_ssl = False
            
            save_config(cfg, backup=True)
            audit_log.log_config_change(session['username'], "system", "", request.remote_addr)
            flash(t("system.saved"), "success")
            
            # Restart web service if port changed or SSL changed
            need_restart = old_port != new_port or old_ssl != new_ssl
            
            if need_restart:
                log("CONFIG", f"Port/SSL changed, scheduling service restart")
                
                # Inform user about new address
                if new_ssl:
                    new_url = f"https://{request.host.split(':')[0]}:{new_ssl_port}/"
                    flash(f"SSL enabled! After restart connect to: {new_url}", "warning")
                elif old_ssl and not new_ssl:
                    new_url = f"http://{request.host.split(':')[0]}:{new_port}/"
                    flash(f"SSL disabled! After restart connect to: {new_url}", "warning")
                elif old_port != new_port:
                    new_url = f"http://{request.host.split(':')[0]}:{new_port}/"
                    flash(f"Port changed! After restart connect to: {new_url}", "warning")
                
                try:
                    import subprocess
                    import threading
                    def delayed_restart():
                        import time
                        time.sleep(3)
                        subprocess.run(['systemctl', 'restart', 'watchdog-web'], capture_output=True)
                    threading.Thread(target=delayed_restart, daemon=True).start()
                except Exception as e:
                    log("ERROR", f"Failed to restart service: {e}")
            
        except Exception as e:
            flash(f"{t('common.error')}: {e}", "error")
    
    try:
        cfg = load_config()
        
        # Ensure features exists
        if 'features' not in cfg:
            cfg['features'] = {}
        if 'system' not in cfg:
            cfg['system'] = {}
        
        # Check if git installed
        import os
        git_installed = os.path.isdir(os.path.join(INSTALL_DIR, '.git'))
        
        return render_template('system.html', config=cfg, timezones=TIMEZONES, git_installed=git_installed, languages=LANGUAGES)
    except Exception as e:
        log("ERROR", f"System page error: {e}")
        import traceback
        log("ERROR", f"Traceback: {traceback.format_exc()}")
        raise


def generate_ssl_certificate():
    """Generate self-signed SSL certificate."""
    import subprocess
    import os
    
    cert_path = os.path.join(SSL_DIR, 'cert.pem')
    key_path = os.path.join(SSL_DIR, 'key.pem')
    
    # Check if already exists
    if os.path.exists(cert_path) and os.path.exists(key_path):
        return True
    
    try:
        os.makedirs(SSL_DIR, exist_ok=True)
        
        # Generate self-signed certificate
        cmd = [
            'openssl', 'req', '-x509', '-newkey', 'rsa:2048',
            '-keyout', key_path,
            '-out', cert_path,
            '-days', '365',
            '-nodes',
            '-subj', '/CN=watchdog/O=Watchdog/C=CZ'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            os.chmod(key_path, 0o600)
            os.chmod(cert_path, 0o644)
            log("SSL", "Self-signed certificate generated successfully")
            return True
        else:
            log("ERROR", f"SSL generation failed: {result.stderr}")
            return False
            
    except Exception as e:
        log("ERROR", f"SSL generation error: {e}")
        return False


@app.route('/smtp', methods=['GET', 'POST'])
@login_required
@permission_required('manage_smtp')
@csrf_protect
def smtp():
    if request.method == 'POST':
        try:
            cfg = load_config()
            
            if 'smtp' not in cfg:
                cfg['smtp'] = {}
            
            cfg['smtp']['enabled'] = request.form.get('smtp_enabled') == 'true'
            cfg['smtp']['server'] = request.form.get('smtp_server', '')
            cfg['smtp']['port'] = int(request.form.get('smtp_port', 587))
            cfg['smtp']['username'] = request.form.get('smtp_username', '')
            
            new_smtp_password = request.form.get('smtp_password', '').strip()
            if new_smtp_password:
                cfg['smtp']['password'] = new_smtp_password
            
            cfg['smtp']['use_tls'] = request.form.get('smtp_tls') == 'true'
            cfg['smtp']['from_address'] = request.form.get('smtp_from', '')
            
            to_input = request.form.get('smtp_to', '')
            cfg['smtp']['to_addresses'] = [s.strip() for s in to_input.replace(',', ' ').split() if s.strip()]
            
            cfg['smtp']['notify_on_reset'] = request.form.get('notify_reset') == 'true'
            cfg['smtp']['notify_on_error'] = request.form.get('notify_error') == 'true'
            
            save_config(cfg, backup=True)
            configure_notifier(cfg['smtp'])
            audit_log.log_config_change(session['username'], "smtp", "", request.remote_addr)
            flash(t("smtp.saved"), "success")
            
        except Exception as e:
            flash(f"{t('common.error')}: {e}", "error")
    
    cfg = load_config()
    return render_template('smtp.html', config=cfg)


@app.route('/smtp/test', methods=['POST'])
@login_required
@permission_required('manage_smtp')
@csrf_protect
def smtp_test():
    try:
        cfg = load_config()
        configure_notifier(cfg.get('smtp', {}))
        
        notifier = get_notifier()
        success, message = notifier.test_connection()
        
        if success:
            notifier.send("Test Connection", "Test email from Watchdog system.")
            return jsonify({"success": True, "message": t("smtp.test_success")})
        else:
            return jsonify({"success": False, "message": message})
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route('/export')
@login_required
@permission_required('export_import')
def export_config():
    try:
        cfg = load_config()
        
        export_cfg = cfg.copy()
        if 'smtp' in export_cfg:
            export_cfg['smtp'] = export_cfg['smtp'].copy()
            export_cfg['smtp'].pop('password', None)
        
        export_cfg['_exported'] = datetime.now().isoformat()
        export_cfg['_exported_by'] = session.get('username')
        export_cfg['_version'] = VERSION
        
        filename = f"watchdog_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        audit_log.log_config_change(session['username'], "export", "", request.remote_addr)
        
        return Response(
            json.dumps(export_cfg, indent=2),
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
    except Exception as e:
        flash(f"{t('common.error')}: {e}", "error")
        return redirect(url_for('system'))


@app.route('/import', methods=['POST'])
@login_required
@permission_required('export_import')
@csrf_protect
def import_config():
    try:
        if 'config_file' not in request.files:
            flash(t("common.error"), "error")
            return redirect(url_for('system'))
        
        file = request.files['config_file']
        if file.filename == '':
            flash(t("common.error"), "error")
            return redirect(url_for('system'))
        
        import_cfg = json.load(file)
        
        validator = ConfigValidator()
        valid, errors = validator.validate(import_cfg)
        
        if not valid:
            flash(f"{t('common.error')}: {', '.join(errors[:3])}", "error")
            return redirect(url_for('system'))
        
        current_cfg = load_config()
        
        if 'smtp' in current_cfg and current_cfg['smtp'].get('password'):
            if 'smtp' not in import_cfg:
                import_cfg['smtp'] = {}
            import_cfg['smtp']['password'] = current_cfg['smtp']['password']
        
        import_cfg.pop('_exported', None)
        import_cfg.pop('_exported_by', None)
        import_cfg.pop('_version', None)
        
        save_config(import_cfg, backup=True)
        audit_log.log_config_change(session['username'], "import", "", request.remote_addr)
        flash(t("common.success"), "success")
        
    except json.JSONDecodeError:
        flash(t("common.error"), "error")
    except Exception as e:
        flash(f"{t('common.error')}: {e}", "error")
    
    return redirect(url_for('system'))


# ==================== GitHub Updates ====================

@app.route('/updates')
@login_required
@permission_required('manage_system')
def updates_page():
    """Show updates page."""
    update_info = updater.check_for_updates()
    git_status = updater.get_git_status()
    
    return render_template('updates.html', 
                         update_info=update_info,
                         git_status=git_status)


@app.route('/api/check-updates')
@login_required
@permission_required('manage_system')
def api_check_updates():
    """API endpoint to check for updates."""
    update_info = updater.check_for_updates()
    return jsonify(update_info)


@app.route('/updates/perform', methods=['POST'])
@login_required
@permission_required('manage_system')
@csrf_protect
def perform_update():
    """Perform the update from GitHub."""
    import threading
    
    audit_log.log_config_change(session['username'], "update", "GitHub update initiated", request.remote_addr)
    
    success, message = updater.update_from_git()
    
    if success:
        # Schedule service restart
        def delayed_restart():
            import time
            time.sleep(3)
            updater.restart_services()
        
        threading.Thread(target=delayed_restart, daemon=True).start()
        flash(f"Update successful! Restarting in 3 seconds...", "success")
    else:
        flash(f"Update failed: {message}", "error")
    
    return redirect(url_for('updates_page'))


# ==================== Live Status API ====================

@app.route('/api/live-status')
@login_required
def api_live_status():
    """Get real-time status of all servers."""
    cfg = load_config()
    groups = cfg.get("groups", [])
    
    status = {}
    
    for group in groups:
        if not group.get("enabled", True):
            continue
            
        group_name = group.get("name", "Unknown")
        servers = group.get("servers", [])
        check_type = group.get("check_type", CHECK_TYPE_PING)
        port = group.get("check_port", 80)
        require_all = group.get("require_all", False)
        
        group_healthy, results = health_checker.check_group(
            servers, 
            check_type=check_type,
            port=port,
            require_all=require_all
        )
        
        status[group_name] = {
            "healthy": group_healthy,
            "servers": [r.to_dict() for r in results],
            "check_type": check_type
        }
    
    return jsonify({
        "status": status,
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/ping/<path:target>')
@login_required
def api_ping_server(target):
    """Ping a specific server."""
    result = health_checker.ping(target)
    return jsonify(result.to_dict())


# ==================== Logs Management ====================

@app.route('/logs/delete', methods=['POST'])
@login_required
@permission_required('control_relays')  # Operator+
@csrf_protect
def delete_logs():
    """Delete system log file (not audit)."""
    log_dir = os.path.join(os.path.dirname(CONFIG_FILE), 'log')
    
    try:
        log_file = os.path.join(log_dir, 'watchdog.log')
        if os.path.exists(log_file):
            with open(log_file, 'w') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO     | Log cleared by {session['username']}\n")
        
        # Also delete rotated log
        old_log = log_file + ".old"
        if os.path.exists(old_log):
            os.remove(old_log)
        
        audit_log.log_config_change(session['username'], "logs", "System log cleared", request.remote_addr)
        flash("Log cleared" if session.get('language') == 'en' else "Log smazán", "success")
        
    except Exception as e:
        flash(f"{t('common.error')}: {e}", "error")
    
    return redirect(url_for('logs'))


@app.route('/audit/delete', methods=['POST'])
@login_required
@permission_required('manage_system')  # Admin only
@csrf_protect
def delete_audit():
    """Delete audit log entries."""
    older_than = int(request.form.get('older_than', 0))
    
    try:
        audit_log.clear(older_than_days=older_than)
        
        if older_than > 0:
            msg = f"Audit entries older than {older_than} days deleted"
        else:
            msg = "Audit log cleared"
        
        audit_log.log_config_change(session['username'], "audit", msg, request.remote_addr)
        flash(msg, "success")
        
    except Exception as e:
        flash(f"{t('common.error')}: {e}", "error")
    
    return redirect(url_for('audit'))


@app.route('/system/clear-stats', methods=['POST'])
@login_required
@permission_required('manage_system')
@csrf_protect
def clear_stats():
    """Clear all statistics files."""
    import glob
    
    stats_dir = os.path.join(os.path.dirname(CONFIG_FILE), 'stats')
    
    try:
        deleted = 0
        for f in glob.glob(os.path.join(stats_dir, '*.json')):
            os.remove(f)
            deleted += 1
        
        audit_log.log_config_change(session['username'], "stats", f"Cleared {deleted} stats files", request.remote_addr)
        flash(f"Statistics cleared ({deleted} files)" if session.get('language') == 'en' else f"Statistiky smazány ({deleted} souborů)", "success")
        
    except Exception as e:
        flash(f"{t('common.error')}: {e}", "error")
    
    return redirect(url_for('system'))


@app.route('/system/clear-old-logs', methods=['POST'])
@login_required
@permission_required('manage_system')
@csrf_protect
def clear_old_logs():
    """Clear rotated log files."""
    import glob
    
    log_dir = os.path.join(os.path.dirname(CONFIG_FILE), 'log')
    
    try:
        deleted = 0
        for pattern in ['*.log.old', '*.log.gz', '*.log.[0-9]*']:
            for f in glob.glob(os.path.join(log_dir, pattern)):
                os.remove(f)
                deleted += 1
        
        audit_log.log_config_change(session['username'], "logs", f"Cleared {deleted} rotated logs", request.remote_addr)
        flash(f"Rotated logs cleared ({deleted} files)" if session.get('language') == 'en' else f"Rotované logy smazány ({deleted} souborů)", "success")
        
    except Exception as e:
        flash(f"{t('common.error')}: {e}", "error")
    
    return redirect(url_for('system'))


# ==================== Statistics Export ====================

@app.route('/stats/export/<group_name>')
@login_required
@permission_required('view_stats')
def export_stats_csv(group_name):
    """Export group statistics as CSV."""
    from stats import stats_manager
    
    try:
        # Get stats for last 30 days
        days = int(request.args.get('days', 30))
        data = stats_manager.get_group_history(group_name, days=days)
        
        if not data:
            flash("No statistics data available", "warning")
            return redirect(url_for('stats'))
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Timestamp', 'Uptime %', 'Avg Latency (ms)', 'Min Latency', 'Max Latency', 'Checks', 'Failures', 'Resets'])
        
        # Data rows
        for entry in data:
            writer.writerow([
                entry.get('timestamp', ''),
                entry.get('uptime_percent', 0),
                entry.get('avg_latency', 0),
                entry.get('min_latency', 0),
                entry.get('max_latency', 0),
                entry.get('total_checks', 0),
                entry.get('failed_checks', 0),
                entry.get('resets', 0)
            ])
        
        # Create response
        output.seek(0)
        filename = f"watchdog_stats_{group_name}_{datetime.now().strftime('%Y%m%d')}.csv"
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
    except Exception as e:
        flash(f"Export failed: {e}", "error")
        return redirect(url_for('stats'))


# ==================== Theme ====================

@app.route('/api/theme', methods=['POST'])
@login_required
def set_theme():
    """Set user theme preference."""
    theme = request.json.get('theme', DEFAULT_THEME)
    
    if theme not in THEMES:
        return jsonify({"success": False, "error": "Invalid theme"})
    
    # Save to user preferences
    user = user_manager.get_user(session['username'])
    if user:
        user['theme'] = theme
        user_manager.update_user(session['username'], user)
    
    session['theme'] = theme
    return jsonify({"success": True, "theme": theme})


# ==================== Groups Reorder (Drag & Drop) ====================

@app.route('/api/groups/reorder', methods=['POST'])
@login_required
@permission_required('manage_groups')
@csrf_protect
def reorder_groups():
    """Reorder groups via drag & drop."""
    try:
        new_order = request.json.get('order', [])
        
        if not new_order:
            return jsonify({"success": False, "error": "No order provided"})
        
        cfg = load_config()
        groups = cfg.get("groups", [])
        
        # Create mapping of name to group
        group_map = {g['name']: g for g in groups}
        
        # Reorder
        new_groups = []
        for name in new_order:
            if name in group_map:
                new_groups.append(group_map[name])
                del group_map[name]
        
        # Add any remaining groups
        new_groups.extend(group_map.values())
        
        cfg['groups'] = new_groups
        save_config(cfg, backup=True)
        
        audit_log.log_config_change(session['username'], "groups", "Reordered groups", request.remote_addr)
        
        return jsonify({"success": True})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ==================== Maintenance ====================

@app.route('/maintenance')
@login_required
@permission_required('manage_system')
def maintenance():
    """Maintenance page with system controls."""
    import subprocess
    
    # Get system info
    system_info = {}
    
    try:
        # Uptime
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            system_info['uptime'] = f"{days}d {hours}h {minutes}m"
    except:
        system_info['uptime'] = '-'
    
    try:
        # Memory
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
            total = int([l for l in meminfo.split('\n') if 'MemTotal' in l][0].split()[1]) // 1024
            free = int([l for l in meminfo.split('\n') if 'MemAvailable' in l][0].split()[1]) // 1024
            system_info['memory'] = f"{total - free} / {total} MB"
    except:
        system_info['memory'] = '-'
    
    try:
        # Disk
        result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                system_info['disk'] = f"{parts[2]} / {parts[1]} ({parts[4]})"
    except:
        system_info['disk'] = '-'
    
    try:
        # CPU Temperature (Raspberry Pi)
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = int(f.read().strip()) / 1000
            system_info['temperature'] = f"{temp:.1f}°C"
    except:
        system_info['temperature'] = '-'
    
    # Service status
    services = {}
    for service in ['watchdog', 'watchdog-web']:
        try:
            result = subprocess.run(['systemctl', 'is-active', service], capture_output=True, text=True)
            services[service] = result.stdout.strip() == 'active'
        except:
            services[service] = False
    
    return render_template('maintenance.html', system_info=system_info, services=services)


@app.route('/maintenance/restart-services', methods=['POST'])
@login_required
@permission_required('manage_system')
@csrf_protect
def restart_services():
    """Restart watchdog services."""
    import subprocess
    import threading
    
    audit_log.log_config_change(session['username'], "maintenance", "Restart services", request.remote_addr)
    log("MAINTENANCE", f"Services restart requested by {session['username']}")
    
    def delayed_restart():
        import time
        time.sleep(2)
        subprocess.run(['systemctl', 'restart', 'watchdog'], capture_output=True)
        time.sleep(1)
        subprocess.run(['systemctl', 'restart', 'watchdog-web'], capture_output=True)
    
    threading.Thread(target=delayed_restart, daemon=True).start()
    flash("Services restart scheduled (2s delay)", "success")
    
    return redirect(url_for('maintenance'))


@app.route('/maintenance/restart-system', methods=['POST'])
@login_required
@permission_required('manage_system')
@csrf_protect
def restart_system():
    """Restart the entire system."""
    import subprocess
    import threading
    
    audit_log.log_config_change(session['username'], "maintenance", "System reboot", request.remote_addr)
    log("MAINTENANCE", f"System reboot requested by {session['username']}")
    
    def delayed_reboot():
        import time
        time.sleep(3)
        subprocess.run(['reboot'], capture_output=True)
    
    threading.Thread(target=delayed_reboot, daemon=True).start()
    flash("System reboot scheduled (3s delay)", "warning")
    
    return redirect(url_for('maintenance'))


@app.route('/backups')
@login_required
@permission_required('export_import')
def list_backups():
    validator = ConfigValidator()
    backups = validator.get_backups()
    
    backup_info = []
    for path in backups[:20]:
        try:
            stat = os.stat(path)
            backup_info.append({
                'path': path,
                'filename': os.path.basename(path),
                'date': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'size': f"{stat.st_size / 1024:.1f} KB"
            })
        except:
            pass
    
    return render_template('backups.html', backups=backup_info)


@app.route('/backup/restore/<path:filename>', methods=['POST'])
@login_required
@permission_required('export_import')
@csrf_protect
def restore_backup(filename):
    try:
        backup_path = os.path.join(BACKUP_DIR, filename)
        
        if not os.path.exists(backup_path):
            flash(t("common.error"), "error")
            return redirect(url_for('list_backups'))
        
        validator = ConfigValidator()
        if validator.restore(backup_path):
            audit_log.log_config_change(session['username'], "restore", filename, request.remote_addr)
            flash(t("backups.restored"), "success")
        else:
            flash(t("common.error"), "error")
            
    except Exception as e:
        flash(f"{t('common.error')}: {e}", "error")
    
    return redirect(url_for('list_backups'))


# ==================== API for Mobile App ====================

@app.route('/api/auth', methods=['POST'])
def api_auth():
    """API authentication - returns token."""
    data = request.get_json() or {}
    username = data.get('username', '')
    password = data.get('password', '')
    
    user = user_manager.authenticate(username, password)
    
    if user:
        token = user_manager.generate_api_token(username)
        audit_log.log_login(username, request.remote_addr)
        return jsonify({
            "success": True,
            "token": token,
            "user": user
        })
    
    audit_log.log_login_failed(username, request.remote_addr)
    return jsonify({"success": False, "error": "Invalid credentials"}), 401


@app.route('/api/groups')
@login_required
def api_groups():
    """Get all groups."""
    try:
        cfg = load_config()
        return jsonify({
            "groups": cfg.get("groups", []),
            "outlets": cfg.get("outlets", {})
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/control', methods=['POST'])
@login_required
@permission_required('control_relays')
def api_control():
    """API control endpoint."""
    data = request.get_json() or {}
    group_name = data.get('group')
    action = data.get('action')
    
    if not group_name or action not in ['on', 'off', 'restart']:
        return jsonify({"error": "Invalid request"}), 400
    
    try:
        cfg = load_config()
        group = next((g for g in cfg.get("groups", []) if g.get("name") == group_name), None)
        
        if not group:
            return jsonify({"error": "Group not found"}), 404
        
        command_map = {
            "on": GPIOCommand.ON,
            "off": GPIOCommand.OFF,
            "restart": GPIOCommand.RESTART
        }
        
        audit_log.log_relay_control(session['username'], group_name, action.upper(), request.remote_addr)
        
        cmd_id = gpio_manager.queue_command(
            group_name=group_name,
            outlet_key=group.get("outlet"),
            command=command_map[action],
            off_time=group.get("off_time", 10),
            source=f"api:{session['username']}"
        )
        
        return jsonify({"success": True, "command_id": cmd_id})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== Error Handlers ====================

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', 
                         error_code=404, 
                         error_message=t("errors.not_found")), 404


@app.errorhandler(500)
def server_error(e):
    log("ERROR", f"Server error: {e}")
    return render_template('error.html',
                         error_code=500,
                         error_message=t("errors.server_error")), 500


@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html',
                         error_code=403,
                         error_message=t("errors.forbidden")), 403


# ==================== Language Switch ====================

@app.route('/language/<lang>')
def switch_language(lang):
    if lang in LANGUAGES:
        session['language'] = lang
        
        if 'username' in session:
            user_manager.update_user(session['username'], language=lang)
    
    return redirect(request.referrer or url_for('dashboard'))


# ==================== Main ====================

if __name__ == '__main__':
    import socket
    
    try:
        cfg = load_config()
        port = cfg.get("system", {}).get("web_port", 80)
        ssl_enabled = cfg.get("system", {}).get("ssl_enabled", False)
        ssl_port = cfg.get("system", {}).get("ssl_port", 443)
        configure_notifier(cfg.get("smtp", {}))
        scheduler.load_from_config(cfg.get("groups", []))
        scheduler.start()
    except Exception as e:
        log("ERROR", f"Failed to load config: {e}")
        port = 80
        ssl_enabled = False
        ssl_port = 443
    
    # Get IP address
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_addr = s.getsockname()[0]
        s.close()
    except:
        ip_addr = "localhost"
    
    cert_path = os.path.join(SSL_DIR, 'cert.pem')
    key_path = os.path.join(SSL_DIR, 'key.pem')
    
    if ssl_enabled:
        # Check if certificate exists, if not try to generate
        if not os.path.exists(cert_path) or not os.path.exists(key_path):
            log("SSL", "Certificate not found, generating self-signed certificate...")
            if generate_ssl_certificate():
                log("SSL", "Certificate generated successfully")
            else:
                log("ERROR", "Failed to generate certificate, falling back to HTTP")
                ssl_enabled = False
        
        if ssl_enabled and os.path.exists(cert_path) and os.path.exists(key_path):
            log("WEB", f"Starting Watchdog v{VERSION} web interface")
            log("WEB", f"HTTPS enabled on port {ssl_port}")
            log("WEB", f"Access URL: https://{ip_addr}:{ssl_port}/")
            print(f"\n{'='*50}")
            print(f"  Watchdog v{VERSION} - HTTPS Mode")
            print(f"  URL: https://{ip_addr}:{ssl_port}/")
            print(f"{'='*50}\n")
            
            app.run(
                host='0.0.0.0', 
                port=ssl_port, 
                threaded=True,
                ssl_context=(cert_path, key_path)
            )
        else:
            ssl_enabled = False
    
    if not ssl_enabled:
        log("WEB", f"Starting Watchdog v{VERSION} web interface")
        log("WEB", f"HTTP on port {port}")
        log("WEB", f"Access URL: http://{ip_addr}:{port}/")
        print(f"\n{'='*50}")
        print(f"  Watchdog v{VERSION} - HTTP Mode")
        print(f"  URL: http://{ip_addr}:{port}/")
        print(f"{'='*50}\n")
        
        app.run(host='0.0.0.0', port=port, threaded=True)
