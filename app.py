import os
import tempfile
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_wtf.csrf import CSRFProtect

from config import Config
from services.audit import audit
from services.auth import authenticate_os_user, login_user, logout_user, login_required, get_current_user
from services.haproxy import haproxy_service
from services.history import history_service

csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    Config.init_app()
    audit.init_app(app)
    csrf.init_app(app)

    @app.route('/health')
    def health():
        return {'status': 'ok'}

    @app.route('/')
    @login_required
    def dashboard():
        status = haproxy_service.get_status()
        recent_logs = audit.get_recent_logs(limit=5)
        backups = history_service.get_history()
        
        return render_template('dashboard.html', 
                               status=status, 
                               recent_logs=recent_logs,
                               backup_count=len(backups),
                               config_path=app.config['HAPROXY_CONFIG_PATH'])

    @app.route('/commands', methods=['GET'])
    @login_required
    def commands():
        return render_template('commands.html')

    @app.route('/commands/execute', methods=['POST'])
    @login_required
    def execute_command():
        action = request.form.get('action')
        username = get_current_user()
        
        success = False
        output = "Unknown action"
        
        if action == 'start':
            success, output = haproxy_service.start_service()
        elif action == 'stop':
            success, output = haproxy_service.stop_service()
        elif action == 'restart':
            success, output = haproxy_service.restart_service()
        elif action == 'reload':
            success, output = haproxy_service.reload_service()
        elif action == 'status':
            status = haproxy_service.get_status()
            success = status['is_active']
            output = status['raw_output']
        elif action == 'validate':
            success, output = haproxy_service.validate_config()
            
        audit.log('execute_command', username, f'{action}: {"success" if success else "failure"}', ip=request.remote_addr, output=output)
        
        return render_template('commands.html', action=action, success=success, output=output)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            if authenticate_os_user(username, password, service=app.config.get('PAM_SERVICE', 'login')):
                login_user(username, request.remote_addr)
                audit.log('login', username, 'success', ip=request.remote_addr)
                flash('Logged in successfully.', 'success')
                return redirect(url_for('dashboard'))
            else:
                audit.log('login', username or 'unknown', 'failure', ip=request.remote_addr)
                flash('Invalid username or password.', 'danger')
                
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        username = get_current_user()
        if username:
            audit.log('logout', username, 'success', ip=request.remote_addr)
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('login'))

    @app.route('/editor', methods=['GET', 'POST'])
    @login_required
    def editor():
        config_path = app.config['HAPROXY_CONFIG_PATH']
        if request.method == 'POST':
            content = request.form.get('config_content', '')
            flash("Review generated configuration before validating or applying.", "info")
        else:
            try:
                with open(config_path, 'r') as f:
                    content = f.read()
            except FileNotFoundError:
                content = "# Configuration file not found."
                flash(f"Configuration file not found at {config_path}", "warning")
            except Exception as e:
                content = f"# Error reading file: {e}"
                flash("Error reading configuration file.", "danger")
            
        return render_template('editor.html', 
                               content=content,
                               config_path=config_path)

    @app.route('/validate', methods=['POST'])
    @login_required
    def validate_config():
        """AJAX endpoint or separate form post for validation."""
        content = request.form.get('config_content', '')
        
        # Save to temp file
        temp_fd, temp_path = tempfile.mkstemp(prefix='haproxy_', suffix='.cfg', dir=app.config['TMP_DIR'])
        try:
            with os.fdopen(temp_fd, 'w') as f:
                f.write(content)
                
            success, output = haproxy_service.validate_config(config_path=temp_path)
            
            username = get_current_user()
            audit.log('validate', username, 'success' if success else 'failure', 
                      ip=request.remote_addr, temp_file=temp_path)
                      
            # Depending on if we want AJAX or standard form submission
            # Let's do standard rendering back to the editor with results
            return render_template('editor.html', 
                                   content=content, 
                                   config_path=app.config['HAPROXY_CONFIG_PATH'],
                                   validation_output=output,
                                   validation_success=success)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @app.route('/apply', methods=['POST'])
    @login_required
    def apply_config():
        content = request.form.get('config_content', '')
        comment = request.form.get('comment', 'No comment provided')
        username = get_current_user()
        config_path = app.config['HAPROXY_CONFIG_PATH']
        
        # 1. Validate first using temp file
        temp_fd, temp_path = tempfile.mkstemp(prefix='haproxy_', suffix='.cfg', dir=app.config['TMP_DIR'])
        try:
            with os.fdopen(temp_fd, 'w') as f:
                f.write(content)
                
            success, validate_output = haproxy_service.validate_config(config_path=temp_path)
            
            if not success:
                audit.log('apply', username, 'failure_validation', ip=request.remote_addr)
                flash('Validation failed. Configuration not applied.', 'danger')
                return render_template('editor.html', 
                                       content=content,
                                       config_path=config_path,
                                       validation_output=validate_output,
                                       validation_success=False)
                                       
            # 2. Validation passed, create backup
            try:
                backup_path = history_service.save_backup(
                    username=username, 
                    comment=comment,
                    source_path=config_path if os.path.exists(config_path) else None
                )
            except Exception as e:
                audit.log('apply', username, 'failure_backup', ip=request.remote_addr, error=str(e))
                flash(f'Failed to create backup: {e}', 'danger')
                return redirect(url_for('editor'))

            # 3. Write new config
            try:
                # Need elevated privileges potentially? The config file is usually root-owned.
                # If the app doesn't have write access, we must write to a temp file and sudo cp it.
                # For simplicity, let's write to a staging temp file and sudo mv/cp it to destination.
                staging_fd, staging_path = tempfile.mkstemp(prefix='haproxy_staging_', dir=app.config['TMP_DIR'])
                with os.fdopen(staging_fd, 'w') as f:
                    f.write(content)
                
                # Sudo copy staging to actual config
                # Actually, standard subprocess works here if configured in sudoers
                import subprocess
                cp_result = subprocess.run(['sudo', '-n', 'cp', staging_path, config_path], capture_output=True)
                if cp_result.returncode != 0:
                    raise IOError(f"Failed to overwrite config: {cp_result.stderr.decode()}")
                os.remove(staging_path)
                
            except Exception as e:
                audit.log('apply', username, 'failure_write', ip=request.remote_addr, error=str(e))
                flash(f'Failed to write new configuration: {e}', 'danger')
                return redirect(url_for('editor'))

            # 4. Reload HAProxy
            reload_cmd_success, reload_output = haproxy_service.reload_service()
            
            if reload_cmd_success:
                audit.log('apply', username, 'success', ip=request.remote_addr, backup=backup_path)
                flash('Configuration applied and HAProxy reloaded successfully.', 'success')
                return redirect(url_for('dashboard'))
            else:
                audit.log('apply', username, 'failure_reload', ip=request.remote_addr, output=reload_output)
                flash(f'Configuration saved, but reload failed: {reload_output}', 'danger')
                # Config is written but bad state, highly unusual since validation passed
                return redirect(url_for('dashboard'))
                
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @app.route('/visual-editor')
    @login_required
    def visual_editor():
        config_path = app.config['HAPROXY_CONFIG_PATH']
        try:
            with open(config_path, 'r') as f:
                content = f.read()
            config_json = haproxy_service.parse_full_config(content)
        except Exception:
            config_json = {'global': [], 'defaults': [], 'frontends': {}, 'backends': {}}
            
        return render_template('visual_editor.html', config_json=config_json)
        
    @app.route('/api/visual-editor/generate', methods=['POST'])
    @login_required
    def api_visual_editor_generate():
        from flask import request, jsonify
        try:
            config_json = request.json
            new_text = haproxy_service.generate_full_config(config_json)
            return jsonify({'config': new_text})
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    @app.route('/history')
    @login_required
    def history():
        backups = history_service.get_history()
        return render_template('history.html', backups=backups)

    @app.route('/history/diff')
    @login_required
    def diff():
        backup_path = request.args.get('backup_path')
        if not backup_path:
            flash('No backup specified.', 'warning')
            return redirect(url_for('history'))
            
        try:
            with open(app.config['HAPROXY_CONFIG_PATH'], 'r') as f:
                current_content = f.read()
        except FileNotFoundError:
            current_content = ""
            
        backup_content = history_service.get_backup_content(backup_path)
        if backup_content is None:
            flash('Backup file not found.', 'danger')
            return redirect(url_for('history'))
            
        diff_text = history_service.generate_diff(current_content, backup_content)
        
        return render_template('diff.html', diff_text=diff_text, backup_path=backup_path)

    @app.route('/history/rollback', methods=['POST'])
    @login_required
    def rollback():
        backup_path = request.form.get('backup_path')
        username = get_current_user()
        
        if not backup_path:
            flash('No backup specified for rollback.', 'warning')
            return redirect(url_for('history'))
            
        backup_content = history_service.get_backup_content(backup_path)
        if backup_content is None:
            flash('Could not read specified backup file.', 'danger')
            return redirect(url_for('history'))
            
        # Write to staging and apply using same mechanism as apply_config
        staging_fd, staging_path = tempfile.mkstemp(prefix='haproxy_rollback_', dir=app.config['TMP_DIR'])
        try:
            with os.fdopen(staging_fd, 'w') as f:
                f.write(backup_content)
                
            success, validate_output = haproxy_service.validate_config(config_path=staging_path)
            
            if not success:
                audit.log('rollback', username, 'failure_validation', ip=request.remote_addr, target=backup_path)
                flash(f'Rollback validation failed: {validate_output}', 'danger')
                return redirect(url_for('history'))
                
            # Create backup of current state before rollback via sudo
            try:
                history_service.save_backup(
                    username=username,
                    comment=f"Auto-backup before rollback to {os.path.basename(backup_path)}",
                    source_path=app.config['HAPROXY_CONFIG_PATH']
                )
            except Exception as e:
                # non-fatal but log it
                app.logger.error(f"Failed backup pre-rollback: {e}")
                
            # Copy backup to live
            import subprocess
            cp_result = subprocess.run(['sudo', '-n', 'cp', staging_path, app.config['HAPROXY_CONFIG_PATH']], capture_output=True)
            if cp_result.returncode != 0:
                audit.log('rollback', username, 'failure_write', ip=request.remote_addr, target=backup_path)
                flash(f'Failed to apply rollback configuration: {cp_result.stderr.decode()}', 'danger')
                return redirect(url_for('history'))
                
            # Reload
            reload_cmd_success, reload_output = haproxy_service.reload_service()
            if reload_cmd_success:
                audit.log('rollback', username, 'success', ip=request.remote_addr, target=backup_path)
                flash('Rollback applied and HAProxy reloaded successfully.', 'success')
                return redirect(url_for('dashboard'))
            else:
                audit.log('rollback', username, 'failure_reload', ip=request.remote_addr, target=backup_path)
                flash(f'Rollback recorded, but reload failed: {reload_output}', 'danger')
                return redirect(url_for('dashboard'))
                
        finally:
            if os.path.exists(staging_path):
                os.remove(staging_path)

    @app.route('/audit')
    @login_required
    def audit_log():
        logs = audit.get_recent_logs(limit=500)
        return render_template('audit.html', logs=logs)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)
