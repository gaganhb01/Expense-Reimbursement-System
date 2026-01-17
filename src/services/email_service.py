"""
Email Service
Sends emails for expense claim submissions, approvals, and rejections
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional
import os

from src.utils.logger import setup_logger

logger = setup_logger()


class EmailService:
    """Email service for sending expense notifications"""
    
    def __init__(self):
        """Initialize email service with SMTP configuration"""
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_username)
        self.from_name = os.getenv("FROM_NAME", "Expense Reimbursement System")
        
        # Check if email is configured
        self.is_configured = bool(self.smtp_username and self.smtp_password)
        
        if not self.is_configured:
            logger.warning("⚠️ Email service not configured. Set SMTP credentials in .env file.")
    
    def _send_email(self, to_email: str, subject: str, html_content: str, text_content: str = None):
        """
        Send email via SMTP
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text fallback (optional)
        """
        if not self.is_configured:
            logger.warning(f"Email not sent to {to_email} - SMTP not configured")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Add text and HTML parts
            if text_content:
                part1 = MIMEText(text_content, 'plain')
                msg.attach(part1)
            
            part2 = MIMEText(html_content, 'html')
            msg.attach(part2)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"✅ Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {str(e)}")
            return False
    
    # ✅✅✅ NEW: Generic send_email method for auth system ✅✅✅
    def send_email(self, to_email: str, subject: str, html_body: str, text_body: str = None):
        """
        Generic email sending method (wrapper for _send_email)
        
        This method is used by the new authentication system for:
        - Invitation emails
        - Password set confirmations
        - OTP emails
        - Password reset confirmations
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email content
            text_body: Plain text fallback (optional)
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        return self._send_email(to_email, subject, html_body, text_body)
    
    def send_submission_confirmation(
        self,
        to_email: str,
        employee_name: str,
        expense_data: dict
    ):
        """
        Send confirmation email when expense is submitted
        
        Args:
            to_email: Employee email
            employee_name: Employee full name
            expense_data: Dictionary with expense details
        """
        subject = f"✅ Expense Submitted - {expense_data.get('expense_number')}"
        
        # HTML email body
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
        .details {{ background: white; padding: 15px; margin: 15px 0; border-left: 4px solid #4CAF50; }}
        .detail-row {{ margin: 10px 0; padding: 5px 0; border-bottom: 1px solid #eee; }}
        .label {{ font-weight: bold; color: #555; display: inline-block; width: 150px; }}
        .value {{ color: #333; }}
        .footer {{ background: #333; color: white; padding: 15px; text-align: center; font-size: 12px; border-radius: 0 0 5px 5px; }}
        .success {{ color: #4CAF50; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ Expense Claim Submitted</h1>
        </div>
        
        <div class="content">
            <p>Dear {employee_name},</p>
            
            <p>Your expense claim has been <span class="success">successfully submitted</span> and is now under review.</p>
            
            <div class="details">
                <h3>📋 Expense Details</h3>
                
                <div class="detail-row">
                    <span class="label">Expense ID:</span>
                    <span class="value">{expense_data.get('id')}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Expense Number:</span>
                    <span class="value">{expense_data.get('expense_number')}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Bill Number:</span>
                    <span class="value">{expense_data.get('bill_number', 'N/A')}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Vendor:</span>
                    <span class="value">{expense_data.get('vendor_name', 'N/A')}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Amount:</span>
                    <span class="value">₹{expense_data.get('amount', 0):,.2f}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Category:</span>
                    <span class="value">{expense_data.get('category', '').upper()}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Expense Date:</span>
                    <span class="value">{expense_data.get('expense_date', 'N/A')}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Description:</span>
                    <span class="value">{expense_data.get('description', 'N/A')}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Submitted At:</span>
                    <span class="value">{expense_data.get('submitted_at', 'N/A')}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Status:</span>
                    <span class="value">SUBMITTED (Pending Manager Approval)</span>
                </div>
            </div>
            
            <p><strong>What's Next?</strong></p>
            <ul>
                <li>Your claim is being reviewed by the manager</li>
                <li>You will receive an email once it's approved or if any action is needed</li>
                <li>You can track the status in the system</li>
            </ul>
            
            <p>Thank you for submitting your expense claim!</p>
        </div>
        
        <div class="footer">
            <p>This is an automated message from the Expense Reimbursement System</p>
            <p>Please do not reply to this email</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Plain text fallback
        text_content = f"""
EXPENSE CLAIM SUBMITTED

Dear {employee_name},

Your expense claim has been successfully submitted and is now under review.

EXPENSE DETAILS:
- Expense ID: {expense_data.get('id')}
- Expense Number: {expense_data.get('expense_number')}
- Bill Number: {expense_data.get('bill_number', 'N/A')}
- Vendor: {expense_data.get('vendor_name', 'N/A')}
- Amount: ₹{expense_data.get('amount', 0):,.2f}
- Category: {expense_data.get('category', '').upper()}
- Expense Date: {expense_data.get('expense_date', 'N/A')}
- Description: {expense_data.get('description', 'N/A')}
- Submitted At: {expense_data.get('submitted_at', 'N/A')}
- Status: SUBMITTED (Pending Manager Approval)

What's Next?
- Your claim is being reviewed by the manager
- You will receive an email once it's approved or if any action is needed
- You can track the status in the system

Thank you for submitting your expense claim!

---
This is an automated message from the Expense Reimbursement System.
Please do not reply to this email.
"""
        
        return self._send_email(to_email, subject, html_content, text_content)
    
    def send_approval_notification(
        self,
        to_email: str,
        employee_name: str,
        expense_data: dict,
        approver_name: str,
        approver_level: str,
        comments: str = None
    ):
        """
        Send email when expense is approved
        
        Args:
            to_email: Employee email
            employee_name: Employee full name
            expense_data: Dictionary with expense details
            approver_name: Name of person who approved
            approver_level: MANAGER or FINANCE
            comments: Optional approval comments
        """
        subject = f"✅ Expense Approved - {expense_data.get('expense_number')}"
        
        # Determine if fully approved or needs more approval
        is_final_approval = expense_data.get('status') == 'approved'
        next_step = "Your reimbursement will be processed soon." if is_final_approval else "Waiting for Finance approval."
        
        # HTML email body
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
        .details {{ background: white; padding: 15px; margin: 15px 0; border-left: 4px solid #4CAF50; }}
        .detail-row {{ margin: 10px 0; padding: 5px 0; border-bottom: 1px solid #eee; }}
        .label {{ font-weight: bold; color: #555; display: inline-block; width: 150px; }}
        .value {{ color: #333; }}
        .comments-box {{ background: #e8f5e9; padding: 15px; margin: 15px 0; border-radius: 5px; border: 1px solid #4CAF50; }}
        .footer {{ background: #333; color: white; padding: 15px; text-align: center; font-size: 12px; border-radius: 0 0 5px 5px; }}
        .success {{ color: #4CAF50; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ Expense Claim Approved!</h1>
        </div>
        
        <div class="content">
            <p>Dear {employee_name},</p>
            
            <p>Good news! Your expense claim has been <span class="success">APPROVED</span> by {approver_level}.</p>
            
            <div class="details">
                <h3>📋 Expense Details</h3>
                
                <div class="detail-row">
                    <span class="label">Expense ID:</span>
                    <span class="value">{expense_data.get('id')}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Expense Number:</span>
                    <span class="value">{expense_data.get('expense_number')}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Bill Number:</span>
                    <span class="value">{expense_data.get('bill_number', 'N/A')}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Vendor:</span>
                    <span class="value">{expense_data.get('vendor_name', 'N/A')}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Amount:</span>
                    <span class="value">₹{expense_data.get('amount', 0):,.2f}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Category:</span>
                    <span class="value">{expense_data.get('category', '').upper()}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Description:</span>
                    <span class="value">{expense_data.get('description', 'N/A')}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Approved By:</span>
                    <span class="value">{approver_name} ({approver_level})</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Approved At:</span>
                    <span class="value">{datetime.now().strftime('%d %B %Y at %I:%M %p')}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Current Status:</span>
                    <span class="value">{"FULLY APPROVED ✅" if is_final_approval else "PENDING FINANCE APPROVAL"}</span>
                </div>
            </div>
            
            {f'''
            <div class="comments-box">
                <h4>💬 Approver Comments</h4>
                <p>{comments}</p>
            </div>
            ''' if comments else ''}
            
            <p><strong>What's Next?</strong></p>
            <p>{next_step}</p>
            
            <p>Thank you!</p>
        </div>
        
        <div class="footer">
            <p>This is an automated message from the Expense Reimbursement System</p>
            <p>Please do not reply to this email</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Plain text fallback
        text_content = f"""
EXPENSE CLAIM APPROVED!

Dear {employee_name},

Good news! Your expense claim has been APPROVED by {approver_level}.

EXPENSE DETAILS:
- Expense ID: {expense_data.get('id')}
- Expense Number: {expense_data.get('expense_number')}
- Bill Number: {expense_data.get('bill_number', 'N/A')}
- Vendor: {expense_data.get('vendor_name', 'N/A')}
- Amount: ₹{expense_data.get('amount', 0):,.2f}
- Category: {expense_data.get('category', '').upper()}
- Description: {expense_data.get('description', 'N/A')}
- Approved By: {approver_name} ({approver_level})
- Approved At: {datetime.now().strftime('%d %B %Y at %I:%M %p')}
- Current Status: {"FULLY APPROVED" if is_final_approval else "PENDING FINANCE APPROVAL"}

{f"APPROVER COMMENTS: {comments}" if comments else ""}

What's Next?
{next_step}

Thank you!

---
This is an automated message from the Expense Reimbursement System.
Please do not reply to this email.
"""
        
        return self._send_email(to_email, subject, html_content, text_content)
    
    def send_rejection_notification(
        self,
        to_email: str,
        employee_name: str,
        expense_data: dict,
        rejector_name: str,
        rejector_level: str,
        rejection_reason: str,
        manager_comments: str = None,
        ai_summary: str = None
    ):
        """
        Send email when expense is rejected
        
        Args:
            to_email: Employee email
            employee_name: Employee full name
            expense_data: Dictionary with expense details
            rejector_name: Name of person who rejected
            rejector_level: MANAGER or FINANCE
            rejection_reason: Main rejection reason
            manager_comments: Optional manager comments
            ai_summary: Optional AI analysis summary
        """
        subject = f"❌ Expense Rejected - {expense_data.get('expense_number')}"
        
        # HTML email body
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #f44336; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
        .details {{ background: white; padding: 15px; margin: 15px 0; border-left: 4px solid #f44336; }}
        .detail-row {{ margin: 10px 0; padding: 5px 0; border-bottom: 1px solid #eee; }}
        .label {{ font-weight: bold; color: #555; display: inline-block; width: 150px; }}
        .value {{ color: #333; }}
        .rejection-box {{ background: #ffebee; padding: 15px; margin: 15px 0; border-radius: 5px; border: 1px solid #f44336; }}
        .comments-box {{ background: #fff3e0; padding: 15px; margin: 15px 0; border-radius: 5px; border: 1px solid #ff9800; }}
        .ai-box {{ background: #e3f2fd; padding: 15px; margin: 15px 0; border-radius: 5px; border: 1px solid #2196F3; }}
        .footer {{ background: #333; color: white; padding: 15px; text-align: center; font-size: 12px; border-radius: 0 0 5px 5px; }}
        .error {{ color: #f44336; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>❌ Expense Claim Rejected</h1>
        </div>
        
        <div class="content">
            <p>Dear {employee_name},</p>
            
            <p>Your expense claim has been <span class="error">REJECTED</span> by {rejector_level}.</p>
            
            <div class="rejection-box">
                <h4>🚫 Rejection Reason</h4>
                <p><strong>{rejection_reason}</strong></p>
            </div>
            
            <div class="details">
                <h3>📋 Expense Details</h3>
                
                <div class="detail-row">
                    <span class="label">Expense ID:</span>
                    <span class="value">{expense_data.get('id')}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Expense Number:</span>
                    <span class="value">{expense_data.get('expense_number')}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Bill Number:</span>
                    <span class="value">{expense_data.get('bill_number', 'N/A')}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Vendor:</span>
                    <span class="value">{expense_data.get('vendor_name', 'N/A')}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Amount:</span>
                    <span class="value">₹{expense_data.get('amount', 0):,.2f}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Category:</span>
                    <span class="value">{expense_data.get('category', '').upper()}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Description:</span>
                    <span class="value">{expense_data.get('description', 'N/A')}</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Rejected By:</span>
                    <span class="value">{rejector_name} ({rejector_level})</span>
                </div>
                
                <div class="detail-row">
                    <span class="label">Rejected At:</span>
                    <span class="value">{datetime.now().strftime('%d %B %Y at %I:%M %p')}</span>
                </div>
            </div>
            
            {f'''
            <div class="comments-box">
                <h4>💬 {rejector_level} Comments</h4>
                <p>{manager_comments}</p>
            </div>
            ''' if manager_comments else ''}
            
            {f'''
            <div class="ai-box">
                <h4>🤖 AI Analysis Summary</h4>
                <pre style="white-space: pre-wrap; font-family: Arial, sans-serif;">{ai_summary}</pre>
            </div>
            ''' if ai_summary else ''}
            
            <p><strong>What You Can Do:</strong></p>
            <ul>
                <li>Review the rejection reason and comments carefully</li>
                <li>If you have a valid bill with correct details, submit a new claim</li>
                <li>Contact {rejector_level} if you have questions about the rejection</li>
                <li>Ensure your next submission has all required documentation</li>
            </ul>
            
            <p>If you believe this rejection was made in error, please contact your manager.</p>
        </div>
        
        <div class="footer">
            <p>This is an automated message from the Expense Reimbursement System</p>
            <p>Please do not reply to this email</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Plain text fallback
        comments_section = f"{rejector_level} COMMENTS:\n{manager_comments}\n" if manager_comments else ""
        ai_section = f"AI ANALYSIS SUMMARY:\n{ai_summary}\n" if ai_summary else ""
        
        text_content = f"""
EXPENSE CLAIM REJECTED

Dear {employee_name},

Your expense claim has been REJECTED by {rejector_level}.

REJECTION REASON:
{rejection_reason}

EXPENSE DETAILS:
- Expense ID: {expense_data.get('id')}
- Expense Number: {expense_data.get('expense_number')}
- Bill Number: {expense_data.get('bill_number', 'N/A')}
- Vendor: {expense_data.get('vendor_name', 'N/A')}
- Amount: ₹{expense_data.get('amount', 0):,.2f}
- Category: {expense_data.get('category', '').upper()}
- Description: {expense_data.get('description', 'N/A')}
- Rejected By: {rejector_name} ({rejector_level})
- Rejected At: {datetime.now().strftime('%d %B %Y at %I:%M %p')}

{comments_section}
{ai_section}
WHAT YOU CAN DO:
- Review the rejection reason and comments carefully
- If you have a valid bill with correct details, submit a new claim
- Contact {rejector_level} if you have questions about the rejection
- Ensure your next submission has all required documentation

If you believe this rejection was made in error, please contact your manager.

---
This is an automated message from the Expense Reimbursement System.
Please do not reply to this email.
"""
        
        return self._send_email(to_email, subject, html_content, text_content)


# Create singleton instance
email_service = EmailService()