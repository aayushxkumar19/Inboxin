#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
InboxIN - Professional Email Automation
"""

import os
import sys
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from PyQt6 import QtWidgets, uic, QtGui
from PyQt6.QtGui import QPixmap, QIcon, QColor
from PyQt6.QtWidgets import QMessageBox, QFileDialog
from PyQt6.QtCore import QTimer, Qt
import qtawesome as qta


class EmailSender:
    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)
        self.window = uic.loadUi('InboxIn.ui')

        # Pause/Resume functionality
        self.is_paused = False
        self.paused_at_index = 0

        # Existing initialization
        self.templates_dir = "templates"
        self.notifications = []
        self.attachments = []

        self.setup_ui()

    def setup_ui(self):
        """Initialize UI with all features"""
        self.window.setWindowState(Qt.WindowState.WindowMaximized)

        # Set icons
        self.window.setWindowIcon(qta.icon("mdi.email", color="#7289da"))
        self.window.Logo.setPixmap(qta.icon("mdi.email", color="#7289da").pixmap(80, 80))

        # Button icons
        self.window.checkbtn.setIcon(qta.icon("mdi.check", color="white"))
        self.window.attachButton.setIcon(qta.icon("mdi.paperclip", color="white"))
        self.window.btnLoadTemplate.setIcon(qta.icon("mdi.folder-open", color="white"))
        self.window.submibtn.setIcon(qta.icon("mdi.send", color="white"))
        self.window.btnPauseResume.setIcon(qta.icon("mdi.pause", color="white"))

        # Setup features
        self.setup_templates()
        self.setup_notifications()

        # Connect signals
        self.window.checkbtn.clicked.connect(self.on_check)
        self.window.submibtn.clicked.connect(self.start_sending)
        self.window.attachButton.clicked.connect(self.handle_attach)
        self.window.btnLoadTemplate.clicked.connect(self.load_template)
        self.window.templateList.itemDoubleClicked.connect(self.load_template)
        self.window.btnPauseResume.clicked.connect(self.toggle_pause_resume)

        # Initialize components
        self.window.sendProgress.setValue(0)
        self.add_notification("Application started")

    def toggle_pause_resume(self):
        """Toggle between pause and resume states"""
        if self.is_paused:
            # Resume sending
            self.is_paused = False
            self.window.btnPauseResume.setText("PAUSE")
            self.window.btnPauseResume.setIcon(qta.icon("mdi.pause", color="white"))
            self.window.btnPauseResume.setStyleSheet("""
                background-color: #f0a732;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            """)
            self.add_notification("Resuming email sending...")

            # Restart timer
            self.timer.start(self.window.delayInput.value() * 1000)
        else:
            # Pause sending
            self.is_paused = True
            self.paused_at_index = self.current_email_index
            self.window.btnPauseResume.setText("RESUME")
            self.window.btnPauseResume.setIcon(qta.icon("mdi.play", color="white"))
            self.window.btnPauseResume.setStyleSheet("""
                background-color: #7289da;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            """)
            self.add_notification("Paused email sending")
            self.timer.stop()

    def start_sending(self):
        """Start batch email sending"""
        if not self.window.emailfile.text():
            self.show_message("Error", "No recipient file selected", QMessageBox.Icon.Warning)
            self.add_notification("Send failed: No recipient file", error=True)
            return

        subject = self.window.sub.text()
        message = self.window.emailtext.toPlainText()
        if not subject or not message:
            self.show_message("Error", "Subject and message cannot be empty", QMessageBox.Icon.Warning)
            self.add_notification("Send failed: Empty subject/message", error=True)
            return

        try:
            with open(self.window.emailfile.text(), 'r') as file:
                self.recipient_emails = [line.strip() for line in file if line.strip()]
        except Exception as e:
            self.show_message("Error", f"Failed to read recipients:\n{str(e)}", QMessageBox.Icon.Critical)
            self.add_notification(f"Send failed: {str(e)}", error=True)
            return

        if not self.recipient_emails:
            self.show_message("Warning", "No valid email addresses found", QMessageBox.Icon.Warning)
            self.add_notification("Send failed: No valid emails", error=True)
            return

        # Initialize batch
        self.current_email_index = 0
        self.success_count = 0
        self.window.sendProgress.setMaximum(len(self.recipient_emails))
        self.window.sendProgress.setValue(0)
        self.window.statusbar.showMessage("Preparing to send...")
        self.add_notification(f"Starting batch send to {len(self.recipient_emails)} recipients")

        # Enable pause button
        self.window.btnPauseResume.setEnabled(True)

        # Disable other UI during send
        self.window.submibtn.setEnabled(False)
        self.window.attachButton.setEnabled(False)
        self.window.checkbtn.setEnabled(False)
        self.window.btnLoadTemplate.setEnabled(False)

        # Start batch timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.send_next_email)
        delay_ms = self.window.delayInput.value() * 1000
        self.timer.start(delay_ms)

    def send_next_email(self):
        """Send one email per timer tick"""
        if self.is_paused:
            return

        if self.current_email_index >= len(self.recipient_emails):
            self.timer.stop()
            self.finish_sending()
            return

        recipient = self.recipient_emails[self.current_email_index]

        try:
            # SMTP Configuration
            smtp_server = 'smtp.gmail.com'
            smtp_port = 587
            sender_email = 'inboxin40@gmail.com'
            sender_password = 'fgjl kkfg ioax ptxr'

            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient
            msg['Subject'] = self.window.sub.text()
            msg.attach(MIMEText(self.window.emailtext.toPlainText(), 'plain'))

            # Add attachments
            if self.attachments:
                for filepath in self.attachments:
                    try:
                        with open(filepath, "rb") as attachment:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename={os.path.basename(filepath)}",
                        )
                        msg.attach(part)
                    except Exception as e:
                        self.add_notification(f"Failed to attach {filepath}: {str(e)}", error=True)

            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipient, msg.as_string())
            self.success_count += 1
            self.add_notification(f"Sent to {recipient}")

        except Exception as e:
            self.add_notification(f"Failed to send to {recipient}: {str(e)}", error=True)

        # Update progress
        self.current_email_index += 1
        self.window.sendProgress.setValue(self.current_email_index)
        self.window.statusbar.showMessage(
            f"Sent {self.current_email_index}/{len(self.recipient_emails)} "
            f"({self.success_count} successful)"
        )

    def finish_sending(self):
        """Clean up after batch complete"""
        self.is_paused = False

        # Reset pause button
        self.window.btnPauseResume.setEnabled(False)
        self.window.btnPauseResume.setText("PAUSE")
        self.window.btnPauseResume.setIcon(qta.icon("mdi.pause", color="white"))
        self.window.btnPauseResume.setStyleSheet("""
            background-color: #f0a732;
            color: white;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        """)

        # Re-enable UI
        self.window.submibtn.setEnabled(True)
        self.window.attachButton.setEnabled(True)
        self.window.checkbtn.setEnabled(True)
        self.window.btnLoadTemplate.setEnabled(True)

        # Show results
        total = len(self.recipient_emails)
        if self.success_count == total:
            self.show_message("Success",
                              f"Sent to all {self.success_count} recipients!",
                              QMessageBox.Icon.Information)
        else:
            self.show_message("Partial Success",
                              f"Sent to {self.success_count} of {total} recipients",
                              QMessageBox.Icon.Warning)

        self.add_notification(f"Batch complete: {self.success_count}/{total} successful")
        self.clear_form()

    def setup_templates(self):
        """Initialize template system"""
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir)
            self.add_notification(f"Created templates directory: {self.templates_dir}")
        self.refresh_templates()

    def refresh_templates(self):
        """Reload template list"""
        self.window.templateList.clear()
        templates = [f for f in os.listdir(self.templates_dir) if f.endswith('.txt')]
        self.window.templateList.addItems(templates)
        if templates:
            self.add_notification(f"Loaded {len(templates)} templates")

    def load_template(self):
        """Load selected template into editor"""
        selected = self.window.templateList.currentItem()
        if selected:
            try:
                with open(os.path.join(self.templates_dir, selected.text()), 'r') as f:
                    self.window.emailtext.setPlainText(f.read())
                self.add_notification(f"Template loaded: {selected.text()}")
            except Exception as e:
                self.add_notification(f"Error loading template: {str(e)}", error=True)

    def setup_notifications(self):
        """Initialize notification system"""
        self.window.notificationList.setAlternatingRowColors(True)

    def add_notification(self, message, error=False):
        """Add message to notification center"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        notification = f"[{timestamp}] {message}"
        self.notifications.insert(0, notification)
        self.window.notificationList.insertItem(0, notification)

        # Highlight errors in red
        if error:
            self.window.notificationList.item(0).setForeground(QColor('#ff6b6b'))

        # Keep only last 50 notifications
        if len(self.notifications) > 50:
            self.window.notificationList.takeItem(50)
            self.notifications.pop()

    def handle_attach(self):
        """Handle file attachments"""
        files, _ = QFileDialog.getOpenFileNames(
            self.window,
            "Select Files",
            "",
            "All Files (*);;PDF (*.pdf);;Images (*.png *.jpg *.jpeg)"
        )
        if files:
            self.attachments = files
            if len(files) == 1:
                self.window.attachmentLabel.setText(os.path.basename(files[0]))
            else:
                names = ", ".join(os.path.basename(f) for f in files[:2])
                if len(files) > 2:
                    names += f" (+{len(files) - 2} more)"
                self.window.attachmentLabel.setText(names)
            self.add_notification(f"Added {len(files)} attachments")

    def on_check(self):
        """Check recipient file"""
        filename = self.window.emailfile.text()
        try:
            with open(filename, 'r') as f:
                recipients = [line.strip() for line in f if line.strip()]
                count = len(recipients)
                self.show_message("Success",
                                  f"File loaded with {count} recipient{'s' if count != 1 else ''}",
                                  QMessageBox.Icon.Information)
                self.add_notification(f"Verified {count} recipients")
        except Exception as err:
            self.show_message("Error",
                              f"File Not Found!\n{str(err)}",
                              QMessageBox.Icon.Critical)
            self.add_notification(f"Error verifying recipients: {str(err)}", error=True)

    def clear_form(self):
        """Reset the form after sending"""
        self.window.emailtext.setPlainText("")
        self.window.sub.setText("")
        self.attachments = []
        self.window.attachmentLabel.setText("No attachments")
        self.window.sendProgress.setValue(0)
        self.window.statusbar.showMessage("Ready")

    def show_message(self, title, message, icon):
        """Display a message dialog"""
        msg = QMessageBox()
        msg.setIcon(icon)
        msg.setText(title)
        msg.setInformativeText(message)
        msg.setWindowTitle(title)
        msg.exec()

    def run(self):
        """Start the application"""
        self.window.show()
        sys.exit(self.app.exec())


if __name__ == "__main__":
    # Install qtawesome if needed
    try:
        import qtawesome
    except ImportError:
        import subprocess

        subprocess.check_call([sys.executable, "-m", "pip", "install", "qtawesome"])

    app = EmailSender()
    app.run()