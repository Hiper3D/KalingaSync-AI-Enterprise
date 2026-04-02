import json
import boto3
import os

def lambda_handler(event, context):
    """
    AWS Cognito "Custom Message" & "Post Confirmation" Trigger
    This function intercepts automated Cognito emails AND fires security alerts after critical actions.
    """
    
    # 1. Identify WHY Cognito is calling this Lambda
    trigger_source = event.get('triggerSource')
    
    # 2. Extract context variables from the Cognito event
    code = event['request'].get('codeParameter', '{####}')
    user_attributes = event['request'].get('userAttributes', {})
    name = user_attributes.get('name', 'User')
    email = user_attributes.get('email')

    # ==========================================
    # 🚀 BULLETPROOF ENTERPRISE HTML TEMPLATE
    # ==========================================
    def get_html(title, main_message, color="#58a6ff"):
        # Upgraded to a robust Table-based layout for perfect alignment across all email clients
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #c9d1d9; background-color: #0d1117; padding: 0; margin: 0;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #0d1117; padding: 40px 15px;">
                <tr>
                    <td align="center">
                        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width: 500px; background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; margin: 0 auto; text-align: left;">
                            <tr>
                                <td style="padding: 30px;">
                                    <!-- Perfectly Aligned Header Table -->
                                    <table cellpadding="0" cellspacing="0" border="0" width="100%" style="border-bottom: 1px solid #30363d; margin-bottom: 20px;">
                                        <tr>
                                            <td width="30" valign="middle" style="padding-bottom: 15px; font-size: 24px;">🛡️</td>
                                            <td valign="middle" style="padding-bottom: 15px;">
                                                <h2 style="color: {color}; margin: 0; font-size: 20px; font-weight: 600;">{title}</h2>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <p style="font-size: 15px; line-height: 1.6; margin: 0 0 15px 0; color: #c9d1d9;">Hello {name},</p>
                                    <div style="font-size: 15px; line-height: 1.6; color: #c9d1d9; margin: 0 0 25px 0;">
                                        {main_message}
                                    </div>
                                    
                                    <p style="font-size: 14px; line-height: 1.5; margin: 0; color: #8b949e;">
                                        Best regards,<br>
                                        <strong style="color: #58a6ff;">KalingaSync Security</strong>
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

    # ==========================================
    # 🔀 ROUTE GROUP 1: Custom Messages (Cognito sends these automatically)
    # ==========================================
    
    # ROUTE 1: Forgot Password OTP (Yellow Warning Theme)
    if trigger_source == "CustomMessage_ForgotPassword":
        event['response']['emailSubject'] = "KalingaSync: Password Reset Code"
        msg = f"""
        <p style='margin: 0 0 15px 0;'>We received a request to reset your password. Your secure OTP code is:</p>
        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #1f1a0f; border: 1px solid #d29922; border-radius: 6px; margin-bottom: 15px;">
            <tr><td align="center" style="padding: 15px; font-size: 26px; font-weight: bold; letter-spacing: 5px; color: #d29922;">{code}</td></tr>
        </table>
        <p style='margin: 0; font-size: 13px; color: #8b949e;'>If you did not request this, please contact IT Security immediately.</p>
        """
        event['response']['emailMessage'] = get_html("Password Reset Request", msg, "#d29922")
        
    # ROUTE 2: Admin Created Account (Green Success Theme)
    elif trigger_source == "CustomMessage_AdminCreateUser":
        event['response']['emailSubject'] = "Welcome to KalingaSync Enterprise"
        msg = f"""
        <p style='margin: 0 0 15px 0;'>An administrator has provisioned your enterprise account. Your temporary login password is:</p>
        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #0f1d13; border: 1px solid #3fb950; border-radius: 6px; margin-bottom: 15px;">
            <tr><td align="center" style="padding: 15px; font-size: 22px; font-weight: bold; color: #3fb950;">{code}</td></tr>
        </table>
        <p style='margin: 0;'>Please log in to the dashboard and change this password immediately.</p>
        """
        event['response']['emailMessage'] = get_html("Account Provisioned", msg, "#3fb950")
        
    # ROUTE 3: Standard User Sign-Up (Blue Info Theme)
    elif trigger_source == "CustomMessage_SignUp":
        event['response']['emailSubject'] = "KalingaSync: Verify Your Email"
        msg = f"""
        <p style='margin: 0 0 15px 0;'>Thank you for registering. Please verify your email address using this secure code:</p>
        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #0d1726; border: 1px solid #58a6ff; border-radius: 6px; margin-bottom: 15px;">
            <tr><td align="center" style="padding: 15px; font-size: 26px; font-weight: bold; letter-spacing: 5px; color: #58a6ff;">{code}</td></tr>
        </table>
        """
        event['response']['emailMessage'] = get_html("Email Verification", msg, "#58a6ff")

    # ==========================================
    # 🔀 ROUTE GROUP 2: Post Confirmation (We must send these manually via SES)
    # ==========================================
    
    elif trigger_source == "PostConfirmation_ConfirmForgotPassword":
        if email:
            try:
                ses_client = boto3.client('ses')
                sender_email = os.environ.get('SENDER_EMAIL')
                if sender_email:
                    msg = "<p style='margin: 0 0 15px 0;'>Your KalingaSync password was successfully changed just now.</p><p style='margin: 0; font-size: 14px; color: #8b949e;'><strong>If you did not make this change, please contact IT Security immediately to lock your account.</strong></p>"
                    html_body = get_html("Password Successfully Changed", msg, "#3fb950")
                    
                    ses_client.send_email(
                        Source=sender_email,
                        Destination={'ToAddresses': [email]},
                        Message={
                            'Subject': {'Data': "Security Alert: Password Changed"},
                            'Body': {'Html': {'Data': html_body}}
                        }
                    )
            except Exception as e:
                print(f"SES PostConfirmation Email Failed: {str(e)}")

    # 🚀 Crucial: Return the modified event object back to Cognito
    return event