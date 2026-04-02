import json
import boto3
import base64
import re
import os
from datetime import datetime, timezone
from decimal import Decimal

# 🚀 NEW: JSON Encoder to handle DynamoDB Decimals safely
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj)
        return super(DecimalEncoder, self).default(obj)

dynamodb = boto3.resource('dynamodb')
cognito_client = boto3.client('cognito-idp')

# 🚨 Database Table Names
USERS_TABLE = 'Users'
ANNOUNCEMENTS_TABLE = 'Announcements'
UPDATE_REQUESTS_TABLE = 'UpdateRequests'
POLLS_TABLE = 'Polls' 

# 🚀 ARCHITECT FIX: Strict Infrastructure Routing via Environment Variables
USER_POOL_ID = os.environ['USER_POOL_ID']
BUCKET_NAME = os.environ['BUCKET_NAME']

# ==========================================
# 🚀 UPGRADED MASTER SES EMAIL ENGINE
# ==========================================
def send_kalingasync_email(to_address, subject, title, status_text, status_color, main_message):
    try:
        ses_client = boto3.client('ses')
        sender_email = os.environ.get('SENDER_EMAIL')
        if not sender_email:
            return

        # Map the primary color to a solid, dark background for the status box (better than rgba)
        bg_colors = { "#d29922": "#1f1a0f", "#3fb950": "#0f1d13", "#f85149": "#201314", "#58a6ff": "#0d1726" }
        box_bg = bg_colors.get(status_color, "#161b22")

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="margin: 0; padding: 0; background-color: #0d1117; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #0d1117; padding: 40px 15px;">
                <tr>
                    <td align="center">
                        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width: 500px; background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; text-align: left;">
                            <tr>
                                <td style="padding: 30px;">
                                    <table cellpadding="0" cellspacing="0" border="0" width="100%" style="border-bottom: 1px solid #30363d; margin-bottom: 20px;">
                                        <tr>
                                            <td width="30" valign="middle" style="padding-bottom: 15px; font-size: 24px;">🛡️</td>
                                            <td valign="middle" style="padding-bottom: 15px;">
                                                <h2 style="color: {status_color}; margin: 0; font-size: 20px; font-weight: 600;">{title}</h2>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <p style="font-size: 15px; line-height: 1.6; margin: 0 0 20px 0; color: #c9d1d9;">Hello,</p>
                                    <div style="font-size: 15px; line-height: 1.6; color: #c9d1d9; margin: 0 0 25px 0;">{main_message}</div>
                                    
                                    <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: {box_bg}; border-left: 4px solid {status_color}; margin-bottom: 25px;">
                                        <tr>
                                            <td style="padding: 12px 15px; font-size: 14px;">
                                                <strong style="color: #c9d1d9;">Status:</strong> <span style="color: {status_color}; font-weight: 600;">{status_text}</span>
                                            </td>
                                        </tr>
                                    </table>
                                    
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
        
        ses_client.send_email(
            Source=sender_email,
            Destination={'ToAddresses': [to_address]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Html': {'Data': html_body}}
            }
        )
    except Exception as e:
        print(f"SES Engine Alert: {str(e)}")


def lambda_handler(event, context):
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }

    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps('CORS OK')}

    try:
        body = json.loads(event.get('body', '{}'))
        action = body.get('action')

        # ==========================================
        # 🔐 ACCESS APPROVALS
        # ==========================================
        if action == 'list_pending':
            res = cognito_client.list_users(UserPoolId=USER_POOL_ID, Filter='cognito:user_status=\"UNCONFIRMED\"')
            pending = []
            for u in res.get('Users', []):
                attrs = {a['Name']: a['Value'] for a in u.get('Attributes', [])}
                pending.append({
                    'username': u['Username'],
                    'email': attrs.get('email', ''),
                    'name': attrs.get('name', ''),
                    'phone': attrs.get('phone_number', ''),
                    'dept': attrs.get('custom:department', ''),
                    'role': attrs.get('custom:role', ''),
                    'address': attrs.get('address', '')
                })
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps(pending)}

        elif action == 'approve_user':
            email = body.get('email', '')
            username = body.get('username', '')
            
            if not email or not username:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": "Missing identity constraints."})}
                
            try: 
                cognito_client.admin_confirm_sign_up(UserPoolId=USER_POOL_ID, Username=username)
            except Exception as e: 
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": f"Cognito Confirmation Failed: {str(e)}"})}
            
            dynamodb.Table(USERS_TABLE).put_item(
                Item={
                    'EmployeeEmail': email, 
                    'FullName': body.get('name', 'Unknown'), 
                    'Handle': email.split('@')[0].lower(), 
                    'JoinedDate': datetime.now(timezone.utc).isoformat(), 
                    'PhoneNumber': body.get('phone', ''), 
                    'Department': body.get('dept', 'N/A'), 
                    'Role': body.get('role', 'N/A'), 
                    'Address': body.get('address', '')
                }
            )
            
            # 🚀 TRIGGER: Admin Approved Account
            send_kalingasync_email(
                email, "KalingaSync: Account Approved!", "Welcome to KalingaSync", 
                "Active & Verified", "#3fb950", 
                "Your enterprise account has been approved. You can now log into your secure dashboard."
            )
            
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": "Onboarded!"})}

        elif action == 'reject_user':
            username = body.get('username', '')
            if not username:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": "Missing username constraint."})}
                
            try: 
                cognito_client.admin_delete_user(UserPoolId=USER_POOL_ID, Username=username)
            except Exception as e: 
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": f"Cognito Deletion Failed: {str(e)}"})}
                
            # 🚀 TRIGGER: Admin Rejected Account
            # Assuming username is the email address for Cognito
            send_kalingasync_email(
                username, "KalingaSync: Registration Update", "Access Request Declined", 
                "Rejected", "#f85149", 
                "Your recent request to join KalingaSync was reviewed and declined by the administrator."
            )
                
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": "Rejected."})}

        # ==========================================
        # 📢 TARGETED BROADCAST SYSTEM
        # ==========================================
        elif action == 'post_note':
            target = body.get('target_handle', '').strip()
            if target.startswith('@'): target = target[1:] 
            note_id = f"PIN_{target}" if target else "LATEST_PIN"
            dynamodb.Table(ANNOUNCEMENTS_TABLE).put_item(Item={'NoteID': note_id, 'NoteContent': body.get('content', ''), 'Target': target or 'ALL'})
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": "Broadcast Live."})}

        elif action == 'get_note':
            item = dynamodb.Table(ANNOUNCEMENTS_TABLE).get_item(Key={'NoteID': 'LATEST_PIN'}, ConsistentRead=True).get('Item', {})
            if item and 'Acknowledgments' in item:
                item['Acknowledgments'] = list(item['Acknowledgments'])
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps(item)}

        elif action == 'list_private_notes':
            table = dynamodb.Table(ANNOUNCEMENTS_TABLE)
            private_notes = []
            
            response = table.scan(ConsistentRead=True)
            while True:
                for item in response.get('Items', []):
                    if item.get('NoteID', '').startswith('PIN_'):
                        if 'Acknowledgments' in item:
                            item['Acknowledgments'] = list(item['Acknowledgments'])
                        private_notes.append(item)
                        
                if 'LastEvaluatedKey' in response:
                    response = table.scan(ConsistentRead=True, ExclusiveStartKey=response['LastEvaluatedKey'])
                else:
                    break
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps(private_notes)}

        elif action == 'delete_note':
            target = body.get('target_handle', '').strip()
            if target.startswith('@'): target = target[1:]
            note_id = f"PIN_{target}" if target else "LATEST_PIN"
            dynamodb.Table(ANNOUNCEMENTS_TABLE).delete_item(Key={'NoteID': note_id})
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": "Broadcast Unpinned."})}

        # ==========================================
        # 👥 ENTERPRISE ROSTER MANAGEMENT
        # ==========================================
        elif action == 'list_roster':
            table = dynamodb.Table(USERS_TABLE)
            items = []
            
            response = table.scan(ConsistentRead=True)
            while True:
                items.extend(response.get('Items', []))
                if 'LastEvaluatedKey' in response:
                    response = table.scan(ConsistentRead=True, ExclusiveStartKey=response['LastEvaluatedKey'])
                else:
                    break
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps(items)}

        elif action == 'add_employee':
            email = body.get('email', '')
            name = body.get('name', '').strip()
            password = body.get('password', '') 
            
            if not email or not name or not password:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": "Missing critical onboarding constraints."})}
                
            generated_handle = email.split('@')[0].lower() 
            joined_date = datetime.now(timezone.utc).isoformat()
            
            try:
                cognito_client.admin_create_user(
                    UserPoolId=USER_POOL_ID, 
                    Username=email, 
                    TemporaryPassword=password, 
                    UserAttributes=[
                        {'Name': 'email', 'Value': email}, 
                        {'Name': 'email_verified', 'Value': 'true'}, 
                        {'Name': 'name', 'Value': name}
                    ], 
                    MessageAction='SUPPRESS'
                )
            except Exception as e:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": f"Auth Failed: {str(e)}"})}
                
            dynamodb.Table(USERS_TABLE).put_item(
                Item={
                    'EmployeeEmail': email, 
                    'FullName': name, 
                    'Handle': generated_handle, 
                    'JoinedDate': joined_date, 
                    'PhoneNumber': body.get('phone', ''), 
                    'Department': body.get('dept', 'N/A'), 
                    'Role': body.get('role', 'N/A'), 
                    'Address': body.get('address', '')
                }
            )
            
            # 🚀 TRIGGER: Admin directly added an employee
            send_kalingasync_email(
                email, "Welcome to KalingaSync!", "Account Created", 
                "Active & Verified", "#3fb950", 
                f"An administrator has created your KalingaSync enterprise account. Your temporary password is: <strong>{password}</strong><br><br>Please log in and change this password immediately."
            )
            
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": "User added!"})}

        elif action == 'edit_employee':
            email = body.get('email', '')
            if not email:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": "Missing identity constraint."})}
                
            dynamodb.Table(USERS_TABLE).update_item(
                Key={'EmployeeEmail': email}, 
                UpdateExpression="set FullName=:n, Handle=:h, PhoneNumber=:p, Department=:d, #r=:role, Address=:a", 
                ExpressionAttributeValues={
                    ':n': body.get('name', 'Unknown'), 
                    ':h': body.get('handle', email.split('@')[0].lower()), 
                    ':p': body.get('phone', ''), 
                    ':d': body.get('dept', 'N/A'), 
                    ':role': body.get('role', 'N/A'), 
                    ':a': body.get('address', '')
                }, 
                ExpressionAttributeNames={'#r': 'Role'}
            )
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": "Updated successfully."})}

        elif action == 'delete_employee':
            email = body.get('email', '')
            if not email:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": "Missing identity constraint."})}
                
            dynamodb.Table(USERS_TABLE).update_item(Key={'EmployeeEmail': email}, UpdateExpression="set AccountStatus=:s", ExpressionAttributeValues={':s': 'Terminated'})
            try: cognito_client.admin_delete_user(UserPoolId=USER_POOL_ID, Username=email)
            except Exception: pass
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": "Employee safely archived (Soft Delete)."})}

        elif action == 'promote_to_admin':
            email = body.get('email', '')
            if not email:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": "Missing identity constraint."})}
                
            try:
                cognito_client.admin_add_user_to_group(UserPoolId=USER_POOL_ID, Username=email, GroupName='Admins')
                dynamodb.Table(USERS_TABLE).update_item(Key={'EmployeeEmail': email}, UpdateExpression="set #r=:r", ExpressionAttributeNames={'#r': 'Role'}, ExpressionAttributeValues={':r': 'System Administrator'})
                return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": f"{email} promoted to Admin!"})}
            except Exception as e:
                return {'statusCode': 500, 'headers': headers, 'body': json.dumps({"error": str(e)})}

        elif action == 'demote_admin':
            email = body.get('email', '')
            if not email:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": "Missing identity constraint."})}
                
            try:
                cognito_client.admin_remove_user_from_group(UserPoolId=USER_POOL_ID, Username=email, GroupName='Admins')
                dynamodb.Table(USERS_TABLE).update_item(Key={'EmployeeEmail': email}, UpdateExpression="set #r=:r", ExpressionAttributeNames={'#r': 'Role'}, ExpressionAttributeValues={':r': 'Employee'})
                return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": f"{email} removed from Admin group!"})}
            except Exception as e:
                return {'statusCode': 500, 'headers': headers, 'body': json.dumps({"error": str(e)})}

        # ==========================================
        # 📝 PROFILE UPDATE WORKFLOW
        # ==========================================
        elif action == 'list_updates':
            table = dynamodb.Table(UPDATE_REQUESTS_TABLE)
            items = []
            
            response = table.scan(ConsistentRead=True)
            while True:
                items.extend(response.get('Items', []))
                if 'LastEvaluatedKey' in response:
                    response = table.scan(ConsistentRead=True, ExclusiveStartKey=response['LastEvaluatedKey'])
                else:
                    break
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps(items)}

        elif action == 'approve_update':
            email = body.get('email', '')
            if not email:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": "Missing identity constraint."})}
                
            dynamodb.Table(USERS_TABLE).update_item(
                Key={'EmployeeEmail': email}, 
                UpdateExpression="set PhoneNumber=:p, Department=:d, #r=:role, Address=:a", 
                ExpressionAttributeValues={
                    ':p': body.get('phone', ''), 
                    ':d': body.get('dept', 'N/A'), 
                    ':role': body.get('role', 'N/A'), 
                    ':a': body.get('address', '')
                }, 
                ExpressionAttributeNames={'#r': 'Role'}
            )
            dynamodb.Table(UPDATE_REQUESTS_TABLE).delete_item(Key={'EmployeeEmail': email})
            
            # 🚀 TRIGGER: Profile Update Approved
            send_kalingasync_email(
                email, "KalingaSync: Profile Update Approved", "Profile Update Approved", 
                "Approved", "#3fb950", 
                "Your requested profile updates have been approved by Admin and applied to your identity profile."
            )
            
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": "Approved."})}

        elif action == 'reject_update':
            email = body.get('email', '')
            if not email:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": "Missing identity constraint."})}
                
            dynamodb.Table(UPDATE_REQUESTS_TABLE).delete_item(Key={'EmployeeEmail': email})
            
            # 🚀 TRIGGER: Profile Update Rejected
            send_kalingasync_email(
                email, "KalingaSync: Profile Update Declined", "Profile Update Declined", 
                "Rejected", "#f85149", 
                "Your recent request to update your KalingaSync profile was declined by an administrator."
            )
            
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": "Rejected."})}

        # ==========================================
        # 📸 ADMIN IMAGE OVERRIDE CONTROLS
        # ==========================================
        elif action == 'admin_upload_photo':
            email = body.get('email', '')
            
            if not email or 'Item' not in dynamodb.Table(USERS_TABLE).get_item(Key={'EmployeeEmail': email}):
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": "Missing or invalid identity constraint."})}

            safe_prefix = re.sub(r'[^a-zA-Z0-9]', '', email.split('@')[0])
            image_data = body.get('image_data', '')
            if "," in image_data:
                image_data = image_data.split(",")[1]
                
            file_name = f"profiles/{safe_prefix}.jpg"
            boto3.client('s3').put_object(Bucket=BUCKET_NAME, Key=file_name, Body=base64.b64decode(image_data), ContentType='image/jpeg')
            url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{file_name}"
            dynamodb.Table(USERS_TABLE).update_item(Key={'EmployeeEmail': email}, UpdateExpression="set PhotoURL=:u", ExpressionAttributeValues={':u': url})
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": "Uploaded.", "photo_url": url})}

        elif action == 'admin_remove_photo':
            email = body.get('email', '')
            if not email:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": "Missing identity constraint."})}

            safe_prefix = re.sub(r'[^a-zA-Z0-9]', '', email.split('@')[0])
            file_name = f"profiles/{safe_prefix}.jpg"
            
            try:
                boto3.client('s3').delete_object(Bucket=BUCKET_NAME, Key=file_name)
            except Exception:
                pass 

            dynamodb.Table(USERS_TABLE).update_item(Key={'EmployeeEmail': email}, UpdateExpression="REMOVE PhotoURL")
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": "Official photo removed by Admin."})}

        # ==========================================
        # 📊 COMPANY POLLING ENGINE (ADMIN)
        # ==========================================
        elif action == 'get_polls':
            table = dynamodb.Table(POLLS_TABLE)
            polls = []
            
            response = table.scan(ConsistentRead=True)
            while True:
                polls.extend(response.get('Items', []))
                if 'LastEvaluatedKey' in response:
                    response = table.scan(ConsistentRead=True, ExclusiveStartKey=response['LastEvaluatedKey'])
                else:
                    break
                    
            polls = sorted(polls, key=lambda x: x.get('CreatedAt', ''), reverse=True)
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps(polls, cls=DecimalEncoder)}

        elif action == 'create_poll':
            question = body.get('question', '').strip()
            options = body.get('options', [])
            
            if not question or not options or len(options) < 2:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": "A poll requires a question and at least 2 options."})}

            poll_id = f"POLL_{int(datetime.now(timezone.utc).timestamp())}"
            
            dynamodb.Table(POLLS_TABLE).put_item(
                Item={
                    'PollID': poll_id,
                    'Question': question,
                    'Options': options,
                    'Votes': {}, 
                    'Status': 'Active',
                    'CreatedAt': datetime.now(timezone.utc).isoformat()
                }
            )
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": "Company Poll Deployed!", "poll_id": poll_id})}

        elif action == 'delete_poll':
            poll_id = body.get('poll_id', '')
            if not poll_id:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": "Missing poll_id constraint."})}
                
            dynamodb.Table(POLLS_TABLE).delete_item(Key={'PollID': poll_id})
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": "Poll permanently removed."})}

        else:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": "Unknown Action"})}

    except Exception as e:
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({"error": f"Lambda Execution Failed: {str(e)}"}) }