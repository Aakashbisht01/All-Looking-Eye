"""
Email service for sending alerts and password reset emails
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import threading

class EmailService:
    """SMTP email service for sending alerts"""
    
    def __init__(self, smtp_server, smtp_port, email, password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email = email
        self.password = password
    
    def send_email(self, to_email, subject, html_body, attachment_path=None):
        """Send an email with optional attachment"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # HTML body
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Attachment (video clip)
            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    filename = os.path.basename(attachment_path)
                    part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                    msg.attach(part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.sendmail(self.email, to_email, msg.as_string())
            
            return True
        except Exception as e:
            print(f"Email error: {e}")
            return False
    
    def send_async(self, to_email, subject, html_body, attachment_path=None):
        """Send email asynchronously"""
        thread = threading.Thread(
            target=self.send_email,
            args=(to_email, subject, html_body, attachment_path)
        )
        thread.start()
        return thread
    
    def send_password_reset(self, to_email, reset_token, reset_url):
        """Send password reset email"""
        subject = "🔐 Password Reset - All Looking Eye"
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #16213e; border-radius: 15px; padding: 30px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ color: #00d4ff; margin: 0; font-size: 28px; }}
                .content {{ line-height: 1.8; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 15px 40px; text-decoration: none; border-radius: 30px; font-weight: bold; margin: 20px 0; }}
                .footer {{ margin-top: 30px; text-align: center; color: #888; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Password Reset Request</h1>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p>We received a request to reset your password for your All Looking Eye account.</p>
                    <p>Click the button below to reset your password:</p>
                    <p style="text-align: center;">
                        <a href="{reset_url}" class="button">Reset Password</a>
                    </p>
                    <p>This link will expire in 1 hour.</p>
                    <p>If you didn't request this, you can safely ignore this email.</p>
                </div>
                <div class="footer">
                    <p>All Looking Eye Anomaly Detection System</p>
                </div>
            </div>
        </body>
        </html>
        """
        return self.send_email(to_email, subject, html_body)
    
    def send_anomaly_alert(self, to_email, anomaly_type, confidence, timestamp, video_clip_path=None):
        """Send anomaly detection alert email"""
        time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        confidence_pct = f"{confidence * 100:.1f}%"
        
        subject = f"🚨 ALERT: {anomaly_type.upper()} Detected - All Looking Eye"
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #16213e; border-radius: 15px; padding: 30px; border: 2px solid #ff4444; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ color: #ff4444; margin: 0; font-size: 28px; }}
                .alert-box {{ background: rgba(255, 68, 68, 0.2); padding: 20px; border-radius: 10px; margin: 20px 0; }}
                .stat {{ display: inline-block; margin: 10px 20px; text-align: center; }}
                .stat-value {{ font-size: 24px; font-weight: bold; color: #ff4444; }}
                .stat-label {{ color: #888; font-size: 12px; }}
                .footer {{ margin-top: 30px; text-align: center; color: #888; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 ANOMALY DETECTED</h1>
                </div>
                <div class="alert-box">
                    <div style="text-align: center;">
                        <div class="stat">
                            <div class="stat-value">{anomaly_type.upper()}</div>
                            <div class="stat-label">Type</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value">{confidence_pct}</div>
                            <div class="stat-label">Confidence</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value">{time_str}</div>
                            <div class="stat-label">Timestamp</div>
                        </div>
                    </div>
                </div>
                <p style="text-align: center;">
                    {"A 5-second video clip is attached to this email." if video_clip_path else ""}
                </p>
                <p style="text-align: center; color: #888;">
                    Please review the detection and take appropriate action if necessary.
                </p>
                <div class="footer">
                    <p>All Looking Eye Anomaly Detection System</p>
                </div>
            </div>
        </body>
        </html>
        """
        return self.send_email(to_email, subject, html_body, video_clip_path)
