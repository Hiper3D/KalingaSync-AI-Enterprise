import json
import boto3
from botocore.exceptions import ClientError
import base64
import os
# 🚀 FIX: Moved timedelta here to the global scope
from datetime import datetime, timezone, timedelta
from boto3.dynamodb.conditions import Key, Attr
import re
import urllib.request
import urllib.error
from decimal import Decimal

# 🚀 NEW: JSON Encoder to handle DynamoDB Decimals safely
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj)
        return super(DecimalEncoder, self).default(obj)

# Initialize AWS Services
dynamodb = boto3.resource('dynamodb')

# 🚨 Database Table Names
USERS_TABLE = 'Users'
ANNOUNCEMENTS_TABLE = 'Announcements'
UPDATE_REQUESTS_TABLE = 'UpdateRequests'
MESSAGES_TABLE = 'DirectMessages'
POLLS_TABLE = 'Polls' # 🚀 NEW: Polls Database Reference

# 🚀 ARCHITECT FIX: Strict Infrastructure Routing via Environment Variables
# Fails fast if the environment variable is not set in the AWS Lambda Console.
BUCKET_NAME = os.environ['BUCKET_NAME']

# ==========================================
# 🚀 UPGRADED MASTER SES EMAIL ENGINE
# ==========================================
def send_kalingasync_email(to_address, subject, title, status_text, status_color, main_message):
    try:
        ses_client = boto3.client('ses')
        sender_email = os.environ.get('SENDER_EMAIL')
        if not sender_email: return

        # Dynamic fallback background for the Status Box based on color
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
            Message={'Subject': {'Data': subject}, 'Body': {'Html': {'Data': html_body}}}
        )
    except Exception as e: print(f"SES Engine Alert: {str(e)}")

def lambda_handler(event, context):
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }

    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}

    try:
        body = json.loads(event.get('body', '{}'))
        action = body.get('action')

        # --- ROUTE 1: Fetch Profile ---
        if action == 'get_profile':
            email = body.get('email', '')
            
            # 🛡️ RESILIENCE FIX 1: Prevent Boto3 ParamValidationError
            if not email:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": "Missing identity constraint."})}
                
            response = dynamodb.Table(USERS_TABLE).get_item(Key={'EmployeeEmail': email})
            if 'Item' in response:
                if response['Item'].get('AccountStatus') == 'Terminated':
                    return {'statusCode': 403, 'headers': headers, 'body': json.dumps({"error": "Access Denied: Account Terminated."})}
                return {'statusCode': 200, 'headers': headers, 'body': json.dumps(response['Item'])}
            return {'statusCode': 404, 'headers': headers, 'body': json.dumps({"error": "Identity not found."})}

        # --- ROUTE 2: Fetch Company Directory (Safe Public Data Only) ---
        elif action == 'get_directory':
            table = dynamodb.Table(USERS_TABLE)
            directory = []
            
            response = table.scan()
            while True:
                for emp in response.get('Items', []):
                    if emp.get('AccountStatus') == 'Terminated':
                        continue
                    directory.append({
                        'FullName': emp.get('FullName', 'Unknown'),
                        'Handle': emp.get('Handle', ''),
                        'EmployeeEmail': emp.get('EmployeeEmail', ''),
                        'Role': emp.get('Role', 'N/A'),
                        'Department': emp.get('Department', 'N/A'),
                        'PhotoURL': emp.get('PhotoURL', '')
                    })
                
                if 'LastEvaluatedKey' in response:
                    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                else:
                    break
                    
            directory = sorted(directory, key=lambda x: x['FullName'])
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps(directory)}

        # --- ROUTE 3: Fetch Super Note (Broadcast) ---
        elif action == 'get_note':
            handle = body.get('handle', '').strip().lower()
            if handle.startswith('@'):
                handle = handle[1:]
            table = dynamodb.Table(ANNOUNCEMENTS_TABLE)
            
            # Fetch Global Note and convert DynamoDB Set to JSON-readable List
            global_item = table.get_item(Key={'NoteID': 'LATEST_PIN'}, ConsistentRead=True).get('Item', {})
            if global_item and 'Acknowledgments' in global_item:
                global_item['Acknowledgments'] = list(global_item['Acknowledgments'])

            # Fetch Private Note and convert DynamoDB Set to JSON-readable List
            private_item = table.get_item(Key={'NoteID': f"PIN_{handle}"}, ConsistentRead=True).get('Item', {}) if handle else {}
            if private_item and 'Acknowledgments' in private_item:
                private_item['Acknowledgments'] = list(private_item['Acknowledgments'])

            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'global_note': global_item, 'private_note': private_item})}

        # --- ROUTE 3.5: Super Note Acknowledgment Engine ---
        elif action == 'acknowledge_note':
            note_id = body.get('note_id', '')
            handle = body.get('handle', '').strip().lower()
            
            if not note_id or not handle:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": "Missing routing constraints."})}
                
            try:
                # 🚀 ARCHITECT FIX: Use DynamoDB String Sets (SS) to prevent duplicate acknowledgments natively
                dynamodb.Table(ANNOUNCEMENTS_TABLE).update_item(
                    Key={'NoteID': note_id},
                    UpdateExpression="ADD Acknowledgments :h",
                    ExpressionAttributeValues={':h': set([handle])}
                )
                return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": "Note safely acknowledged."})}
            except Exception as e:
                return {'statusCode': 500, 'headers': headers, 'body': json.dumps({"error": f"Database mutation failed: {str(e)}"}) }

        # --- ROUTE 4: Threaded Chat Engines ---
        elif action == 'send_message':
            receiver = body.get('receiver_handle', '').strip().lower()
            sender = body.get('sender_handle', '').strip().lower()
            if receiver.startswith('@'):
                receiver = receiver[1:]
            if sender.startswith('@'):
                sender = sender[1:]
            
            # 🛡️ RESILIENCE FIX 2: Strict guard against unroutable ghost messages
            if not receiver or not sender:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": "Missing critical routing constraints."})}
            
            dynamodb.Table(MESSAGES_TABLE).put_item(
                Item={
                    'ReceiverHandle': receiver,
                    'Timestamp': datetime.now(timezone.utc).isoformat(),
                    'SenderEmail': body.get('sender_email', ''),
                    'SenderName': body.get('sender_name', 'Unknown'),
                    'SenderPhoto': body.get('sender_photo', ''),
                    'SenderHandle': sender, 
                    'MessageContent': body.get('content', '')
                }
            )
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": "Message securely delivered."})}

        elif action == 'get_inbox':
            handle = body.get('handle', '').strip().lower()
            if handle.startswith('@'):
                handle = handle[1:]
            
            table = dynamodb.Table(MESSAGES_TABLE)
            inbox = []
            sent = []
            
            response = table.query(KeyConditionExpression=Key('ReceiverHandle').eq(handle))
            while True:
                inbox.extend(response.get('Items', []))
                if 'LastEvaluatedKey' in response:
                    response = table.query(KeyConditionExpression=Key('ReceiverHandle').eq(handle), ExclusiveStartKey=response['LastEvaluatedKey'])
                else:
                    break

            # ⚠️ ARCHITECT WARNING: A full table scan for sent messages is not scalable long-term.
            # For massive enterprise scale, create a GSI [Global Secondary Index] on 'SenderHandle'.
            response_sent = table.scan(FilterExpression=Attr('SenderHandle').eq(handle))
            while True:
                sent.extend(response_sent.get('Items', []))
                if 'LastEvaluatedKey' in response_sent:
                    response_sent = table.scan(FilterExpression=Attr('SenderHandle').eq(handle), ExclusiveStartKey=response_sent['LastEvaluatedKey'])
                else:
                    break
            
            all_messages = sorted(inbox + sent, key=lambda x: x.get('Timestamp', ''))
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps(all_messages)}

        elif action == 'delete_thread':
            my_handle = body.get('my_handle', '').strip().lower()
            partner_handle = body.get('partner_handle', '').strip().lower()
            if my_handle.startswith('@'):
                my_handle = my_handle[1:]
            if partner_handle.startswith('@'):
                partner_handle = partner_handle[1:]
            
            table = dynamodb.Table(MESSAGES_TABLE)
            inbox = []
            outbox = []
            
            res_in = table.query(KeyConditionExpression=Key('ReceiverHandle').eq(my_handle))
            while True:
                inbox.extend(res_in.get('Items', []))
                if 'LastEvaluatedKey' in res_in:
                    res_in = table.query(KeyConditionExpression=Key('ReceiverHandle').eq(my_handle), ExclusiveStartKey=res_in['LastEvaluatedKey'])
                else:
                    break

            res_out = table.query(KeyConditionExpression=Key('ReceiverHandle').eq(partner_handle))
            while True:
                outbox.extend(res_out.get('Items', []))
                if 'LastEvaluatedKey' in res_out:
                    res_out = table.query(KeyConditionExpression=Key('ReceiverHandle').eq(partner_handle), ExclusiveStartKey=res_out['LastEvaluatedKey'])
                else:
                    break
            
            with table.batch_writer() as batch:
                for msg in inbox:
                    if msg.get('SenderHandle') == partner_handle:
                        batch.delete_item(Key={'ReceiverHandle': my_handle, 'Timestamp': msg['Timestamp']})
                for msg in outbox:
                    if msg.get('SenderHandle') == my_handle:
                        batch.delete_item(Key={'ReceiverHandle': partner_handle, 'Timestamp': msg['Timestamp']})
                        
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": "Chat history completely cleared."})}

        # --- ROUTE 5: Log an Update Request ---
        elif action == 'request_update':
            email = body.get('email', '')
            if not email or 'Item' not in dynamodb.Table(USERS_TABLE).get_item(Key={'EmployeeEmail': email}):
                return {'statusCode': 403, 'headers': headers, 'body': json.dumps({"error": "Security Block: Identity does not exist."})}

            dynamodb.Table(UPDATE_REQUESTS_TABLE).put_item(
                Item={
                    'EmployeeEmail': email,
                    'RequestedPhone': body.get('phone', ''),
                    'RequestedAddress': body.get('address', ''),
                    'RequestedDept': body.get('dept', 'N/A'),
                    'RequestedRole': body.get('role', 'N/A'),
                    'Status': 'PENDING',
                    'RequestDate': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # 🚀 SES INTEGRATION: Instantly email the user a security receipt
            send_kalingasync_email(
                email, 
                "KalingaSync: Profile Update Requested", 
                "Security Alert", 
                "Pending Admin Approval", 
                "#d29922", 
                "We have successfully received your request to update your KalingaSync Identity Profile. <br><br><span style='font-size: 13px; color: #8b949e;'>If you did not request this change, please contact IT Security immediately to secure your account.</span>"
            )

            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": "Update request safely logged and email confirmation sent!"})}

        # --- ROUTE 6: Image Override Controls ---
        elif action == 'upload_photo':
            email = body.get('email', '')
            if not email or 'Item' not in dynamodb.Table(USERS_TABLE).get_item(Key={'EmployeeEmail': email}):
                return {'statusCode': 403, 'headers': headers, 'body': json.dumps({"error": "Security Block: Identity constraint failed."})}

            image_data = body.get('image_data', '')
            if not image_data:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": "Invalid payload: Image data is empty."})}
                
            # 🛡️ RESILIENCE FIX 3: Prevent cross-user S3 overwrites by utilizing the full, safe email string
            safe_prefix = re.sub(r'[^a-zA-Z0-9._-]', '', email)
            
            if "," in image_data:
                image_data = image_data.split(",")[1]
                
            file_name = f"profiles/{safe_prefix}.jpg"
            boto3.client('s3').put_object(Bucket=BUCKET_NAME, Key=file_name, Body=base64.b64decode(image_data), ContentType='image/jpeg')
            url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{file_name}"
            dynamodb.Table(USERS_TABLE).update_item(Key={'EmployeeEmail': email}, UpdateExpression="set PhotoURL=:u", ExpressionAttributeValues={':u': url})
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": "Uploaded.", "photo_url": url})}

        elif action == 'remove_photo':
            email = body.get('email', '')
            # 🛡️ RESILIENCE FIX 4: Identity constraint added to block arbitrary file deletions
            if not email or 'Item' not in dynamodb.Table(USERS_TABLE).get_item(Key={'EmployeeEmail': email}):
                return {'statusCode': 403, 'headers': headers, 'body': json.dumps({"error": "Security Block: Identity constraint failed."})}

            safe_prefix = re.sub(r'[^a-zA-Z0-9._-]', '', email)
            file_name = f"profiles/{safe_prefix}.jpg"
            
            try:
                boto3.client('s3').delete_object(Bucket=BUCKET_NAME, Key=file_name)
            except Exception:
                pass

            dynamodb.Table(USERS_TABLE).update_item(Key={'EmployeeEmail': email}, UpdateExpression="REMOVE PhotoURL")
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": "Photo removed."})}

        # ==========================================
        # 📊 COMPANY POLLING ENGINE (EMPLOYEE)
        # ==========================================
        elif action == 'get_polls':
            table = dynamodb.Table(POLLS_TABLE)
            polls = []
            
            # 🚀 ARCHITECT FIX: Pagination for infinite scaling
            response = table.scan(ConsistentRead=True)
            while True:
                polls.extend(response.get('Items', []))
                if 'LastEvaluatedKey' in response:
                    response = table.scan(ConsistentRead=True, ExclusiveStartKey=response['LastEvaluatedKey'])
                else:
                    break
                    
            # Sort newest first
            polls = sorted(polls, key=lambda x: x.get('CreatedAt', ''), reverse=True)
            
            # 🚀 ARCHITECT FIX: Use the custom DecimalEncoder to prevent JSON serialization crashes
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps(polls, cls=DecimalEncoder)}

        elif action == 'submit_vote':
            poll_id = body.get('poll_id')
            option_index = body.get('option_index')
            handle = body.get('handle', '').strip().lower()

            if not poll_id or option_index is None or not handle:
                return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": "Missing voting constraints."})}

            try:
                # 🛡️ RESILIENCE FIX: ConditionExpression prevents double-voting at the database level!
                dynamodb.Table(POLLS_TABLE).update_item(
                    Key={'PollID': poll_id},
                    UpdateExpression=f"SET Votes.#h = :v",
                    ExpressionAttributeNames={'#h': handle},
                    ExpressionAttributeValues={':v': option_index},
                    ConditionExpression="attribute_not_exists(Votes.#h)" 
                )
                return {'statusCode': 200, 'headers': headers, 'body': json.dumps({"message": "Vote securely cast."})}
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                    return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": "You have already voted on this poll."})}
                return {'statusCode': 500, 'headers': headers, 'body': json.dumps({"error": str(e)})}

        # ==========================================
        # 🤖 KALINGASYNC AI INTEGRATION (GROQ UPGRADE)
        # ==========================================
        elif action == 'ask_ai':
            prompt = body.get('prompt', '')
            history = body.get('history', [])
            
            # 🚀 FIX: Removed the local inner import to prevent the UnboundLocalError
            
            # Live clock for the KalingaSync persona
            ist_time = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
            live_date_string = ist_time.strftime("%A, %B %d, %Y, at %I:%M %p IST")
            
            system_prompt = f"You are KalingaSync AI, the advanced and approachable enterprise assistant for our organization. 🚀 Your mission is to empower employees, solve technical challenges, and streamline daily operations. 💡 Speak with a warm, engaging, and highly professional tone. Use emojis tastefully. You operate within a secure corporate environment: maintain strict confidentiality. You do not have live access to the company database. If an employee asks for specific company metrics, employee counts, or private data, you must politely inform them that you do not have clearance, and you must NEVER guess or invent numbers. 🛡️ When generating programming code, you must enclose them strictly within triple backtick Markdown code blocks. 💻 The current live date and time is {live_date_string}. ⏰ Always provide complete, polished sentences. ✅"
            
            # 1. Initialize the Groq messages array with the system prompt
            groq_messages = [{"role": "system", "content": system_prompt}]
            
            # 2. Translate Gemini history format to Groq format so the AI remembers the conversation
            MAX_HISTORY = 8
            trimmed_history = history[-MAX_HISTORY:] if history else []
            for msg in trimmed_history:
                mapped_role = "assistant" if msg.get("role") == "model" else "user"
                extracted_text = msg.get("parts", [{"text": ""}])[0].get("text", "")
                if extracted_text:
                    groq_messages.append({"role": mapped_role, "content": extracted_text})
            
            # 3. If it is the first message (no history), add the current prompt
            if not history and prompt:
                groq_messages.append({"role": "user", "content": prompt})
                
            groq_api_key = os.environ.get('GROQ_API_KEY')
            if not groq_api_key:
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({'error': 'GROQ_API_KEY is not set in AWS Environment Variables'})
                }
            
            # 4. 🔥 NEW: Replaced Gemini URL with Groq API endpoint    
            url = "https://api.groq.com/openai/v1/chat/completions"
            
            # 5. 🔥 NEW: Exact Groq Payload using llama-3.1-8b-instant
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": groq_messages,
                "temperature": 0.7,
                "max_tokens": 1024 
            }
            
            # 6. 🔥 NEW: Required Groq Headers with User-Agent added to bypass WAF
            req_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {groq_api_key}",
                "User-Agent": "KalingaSync/1.0" # Prevents Groq from blocking the request as a bot
            }
            
            req = urllib.request.Request(
                url, 
                data=json.dumps(payload).encode('utf-8'), 
                headers=req_headers
            )
            
            try:
                # AWS Lambda timeout buffer (28s)
                with urllib.request.urlopen(req, timeout=28) as response:
                    # 7. 🔥 NEW: Groq JSON Parsing
                    ai_data = json.loads(response.read().decode('utf-8'))
                    ai_text = ai_data['choices'][0]['message']['content']
                    
                    return {
                        'statusCode': 200,
                        'headers': headers,
                        'body': json.dumps({'reply': ai_text})
                    }
            except urllib.error.HTTPError as e:
                # 🛡️ FIX: Read the actual error message from Groq so we know exactly why it failed
                try:
                    error_info = e.read().decode('utf-8')
                except Exception:
                    error_info = "Unable to read error details."
                
                return {
                    'statusCode': e.code,
                    'headers': headers,
                    'body': json.dumps({'error': f"Groq API Error ({e.code}): {error_info}"})
                }
            except Exception as e:
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({'error': f"AI Engine Failure: {str(e)}"})
                }

        else:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({"error": "Unknown Action"})}

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({"error": str(e)})}