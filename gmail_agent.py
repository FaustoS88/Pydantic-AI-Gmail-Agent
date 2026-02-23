# First import dotenv to load environment variables
from dotenv import load_dotenv
import os

# Load environment variables before anything else
load_dotenv()

# Check if API key is set
api_key = os.getenv("MY_OPENROUTER_API_KEY")
if not api_key or api_key == "your_openrouter_api_key_here":
    print("\nERROR: You need to set your OpenRouter API key in the .env file!")
    print("Please edit the .env file and replace 'your_openrouter_api_key_here' with your actual API key.\n")

# Import required modules
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import httpx
import base64
import html
import re
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel  # Correct import for OpenAIModel
from google.oauth2.credentials import Credentials as GoogleCredentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import time
import aiohttp
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# Import MemoryIntegration from the local memory package
from memory import MemoryIntegration
# Gmail API Setup
@dataclass
class GmailDependencies:
    credentials: GoogleCredentials
    client: httpx.AsyncClient
    memory: MemoryIntegration = field(default_factory=lambda: MemoryIntegration())

    async def get_gmail_service(self):
        """Get authenticated Gmail service instance"""
        if self.credentials and self.credentials.expired and self.credentials.refresh_token:
            self.credentials.refresh(Request())
        return build('gmail', 'v1', credentials=self.credentials)

# Define result structure
class GmailResult(BaseModel):
    processed_emails: int = Field(description="Number of emails processed")
    sent_replies: int = Field(description="Number of replies sent")
    cleaned_emails: int = Field(description="Number of emails cleaned")

# Replace the OpenAIModel initialization with a custom class
# First, create our custom OpenRouterAPI class
class OpenRouterAPI:
    def __init__(self, api_key, model="google/gemini-2.0-flash-001"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"

    async def generate_response(self, prompt):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"API Error: Status {response.status}, Response: {error_text}")
                        return f"Error: API returned status {response.status}"
                    
                    result = await response.json()
                    
                    # Check if the response has the expected structure
                    if 'choices' not in result or not result['choices'] or 'message' not in result['choices'][0]:
                        print(f"Unexpected API response format: {result}")
                        return "Error: Unexpected API response format"
                    
                    return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"Error calling OpenRouter API: {e}")
            return f"Error: {str(e)}"

# Load environment variables before creating the OpenRouter instance
api_key = os.getenv("MY_OPENROUTER_API_KEY")

# Create the OpenRouter instance with explicit API key checking
if api_key and api_key != "your_openrouter_api_key_here":
    router_api = OpenRouterAPI(api_key)
else:
    # Create a mock API for testing that returns a placeholder message
    class MockAPI:
        async def generate_response(self, prompt):
            return "[API KEY NOT SET] This is a placeholder response. Please set your OpenRouter API key in the .env file."
    router_api = MockAPI()

# Create a custom model class that extends OpenAIModel
class OpenRouterModel(OpenAIModel):
    def __init__(self):
        super().__init__(
            "google/gemini-2.0-flash-001",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("MY_OPENROUTER_API_KEY")
        )

    async def __call__(self, prompt: str, **kwargs) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get('temperature', 0.7),
            "max_tokens": kwargs.get('max_tokens', 1000)
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"API Error: Status {response.status}, Response: {error_text}")
                        return f"Error: API returned status {response.status}"
                    
                    result = await response.json()
                    
                    # Check if the response has the expected structure
                    if 'choices' not in result or not result['choices'] or 'message' not in result['choices'][0]:
                        print(f"Unexpected API response format: {result}")
                        return "Error: Unexpected API response format"
                    
                    return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"Error calling OpenRouter API: {e}")
            return f"Error: {str(e)}"

# No need to initialize OpenRouter API again since we already did it above

# Initialize the agent with a string model name
gmail_agent = Agent(
    model="openai:gpt-4",  # Use a standard model name that pydantic_ai recognizes
    deps_type=GmailDependencies,
    output_type=GmailResult,
    system_prompt=(
        "You are Sofia, an AI assistant managing Gmail accounts. "
        "Your tasks are to: "
        "1. Process starred emails with unread messages, "
        "2. Generate personalized, helpful replies, "
        "3. Clean spam and unwanted emails."
    ),
    model_settings={
        "temperature": 0.7,
        "max_tokens": 1500,
        "base_url": "https://openrouter.ai/api/v1",  # Override with OpenRouter URL
        "api_key": os.getenv("MY_OPENROUTER_API_KEY")  # Use OpenRouter API key
    }
)

# Dynamic system prompt tool
@gmail_agent.system_prompt
async def add_style_prompt(ctx: RunContext[GmailDependencies]) -> str:
    return (
        "When generating replies as Sofia, follow these guidelines: "
        "1. Be comprehensive and detailed in your responses (3-5 sentences minimum) "
        "2. Maintain a warm, friendly, and positive tone throughout "
        "3. Be professional but conversational, not overly formal "
        "4. Provide helpful, solution-oriented information "
        "5. Respond in the same language as the original email "
        "6. Use appropriate greetings and sign-offs based on the context "
        "7. For questions, provide thorough answers with examples when relevant "
        "8. For requests, acknowledge them clearly and provide next steps "
        "9. For statements or updates, acknowledge the information appropriately "
        "10. Always maintain a positive tone even when addressing problems"
    )

# Tool to fetch starred emails
@gmail_agent.tool
async def fetch_starred_emails(ctx: RunContext[GmailDependencies]) -> List[dict]:
    service = await ctx.deps.get_gmail_service()
    results = service.users().messages().list(
        userId='me',
        labelIds=['STARRED'],
        maxResults=10
    ).execute()
    messages = results.get('messages', [])
    
    # Fetch full details for each message to ensure we have content
    detailed_messages = []
    for msg in messages:
        full_msg = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='full'
        ).execute()
        detailed_messages.append(full_msg)
    
    return detailed_messages

# Helper function to get sent messages
@gmail_agent.tool
async def get_sent_messages(ctx: RunContext[GmailDependencies], thread_id: str, max_results: int = 1) -> List[dict]:
    """Get the most recent sent messages in a thread"""
    service = await ctx.deps.get_gmail_service()
    
    # Query for sent messages in this thread
    query = f"threadId:{thread_id} label:sent"
    results = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=max_results
    ).execute()
    
    messages = results.get('messages', [])
    
    # Fetch full details for each message
    detailed_messages = []
    for msg in messages:
        full_msg = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='full'
        ).execute()
        detailed_messages.append(full_msg)
    
    return detailed_messages

# Tool to generate a reply for an email
@gmail_agent.tool
async def generate_reply(ctx: RunContext[GmailDependencies], email_content: str, thread_id: str) -> str:
    # Get memory context for this thread
    memory_context = ctx.deps.memory.get_memory_context(thread_id)
    
    # Use our API directly rather than ctx.model
    prompt = f"""You are Sofia, a helpful and professional assistant. You're responding to an email from a user.
        
Your responses should be:
- Comprehensive and detailed (at least 3-5 sentences for most emails)
- Warm, friendly, and positive in tone
- Professional but conversational
- Helpful and solution-oriented
- Written in the same language as the original email (e.g., Italian, Spanish, English)

When responding:
1. If it's a question, provide a thorough answer with examples or steps when relevant
2. If it's a request, acknowledge it clearly and provide next steps or confirmation
3. If it's a statement or update, acknowledge the information and respond appropriately
4. Always maintain a positive, supportive tone even when addressing problems
5. Use appropriate greetings and sign-offs based on the formality of the original email
6. If the email is in a language other than English, respond in that same language

CONVERSATION CONTEXT AND MEMORY:
{memory_context}

Here is the email to respond to:
{email_content}

Write a complete, helpful response as Sofia that references relevant past conversations and shows understanding of the people and projects mentioned:"""
    
    # Use the API directly via the model method
    if hasattr(ctx, 'api') and ctx.api:
        return await ctx.api.generate_response(prompt)
    elif hasattr(ctx, 'model') and callable(ctx.model):
        return await ctx.model(prompt)
    else:
        raise ValueError("No API or model available to generate a response")

# Tool to create a draft reply instead of sending immediately
@gmail_agent.tool
async def create_reply_draft(ctx: RunContext[GmailDependencies], message_id: str, reply_content: str) -> bool:
    """Create a draft reply instead of sending it immediately"""
    service = await ctx.deps.get_gmail_service()
    
    # Get the original message to extract headers and thread ID for reply
    original_message = service.users().messages().get(userId='me', id=message_id).execute()
    thread_id = original_message.get('threadId')
    
    # Get the recipient email and subject
    to_email = None
    subject = "Re: Email"
    from_email = None
    message_id_header = None
    references_header = None
    in_reply_to_header = None
    
    headers = original_message.get('payload', {}).get('headers', [])
    for header in headers:
        header_name = header.get('name', '').lower()
        if header_name == 'from':
            from_email = header.get('value', '')
        elif header_name == 'to':
            # This is who the original message was sent to (likely the user's email)
            user_email = header.get('value', '')
        elif header_name == 'subject':
            # Don't add another "Re:" if it already has one
            subject_value = header.get('value', 'Email')
            if subject_value.lower().startswith('re:'):
                subject = subject_value
            else:
                subject = f"Re: {subject_value}"
        elif header_name == 'message-id':
            message_id_header = header.get('value', '')
        elif header_name == 'references':
            references_header = header.get('value', '')
        elif header_name == 'in-reply-to':
            in_reply_to_header = header.get('value', '')
    
    # For messages sent by the user (SENT label), we need to use the 'To' field as recipient
    # For messages received by the user, we use the 'From' field as recipient
    labels = original_message.get('labelIds', [])
    if 'SENT' in labels:
        # This is a message sent by the user, so reply to the recipient of the original message
        print(f"Message {message_id} has SENT label, extracting recipient from 'To' header")
        
        # Re-examine headers to find the 'To' field
        for header in headers:
            if header.get('name', '').lower() == 'to':
                to_email = header.get('value', '')
                break
    else:
        # This is a message received by the user, so reply to the sender
        to_email = from_email
    
    print(f"Creating draft reply to: {to_email}")
    
    if not to_email:
        print(f"Could not find recipient email for message {message_id}")
        return False
    
    # Create properly formatted email with threading headers
    raw_message = create_email_reply(to_email, subject, reply_content, thread_id, message_id_header, references_header, in_reply_to_header)
    
    # Create a draft email in the same thread instead of sending immediately
    draft = {
        'message': {
            'raw': raw_message,
            'threadId': thread_id
        }
    }
    
    draft = service.users().drafts().create(userId='me', body=draft).execute()
    print(f"Draft created in thread: {thread_id}")
    return True

# Tool to send a reply email
@gmail_agent.tool
async def send_reply(ctx: RunContext[GmailDependencies], message_id: str, reply_content: str) -> bool:
    """Send a reply email directly"""
    service = await ctx.deps.get_gmail_service()
    
    # Get the original message to extract headers and thread ID for reply
    original_message = service.users().messages().get(userId='me', id=message_id).execute()
    thread_id = original_message.get('threadId')
    
    # Get the recipient email and subject
    to_email = None
    subject = "Re: Email"
    from_email = None
    message_id_header = None
    references_header = None
    in_reply_to_header = None
    
    headers = original_message.get('payload', {}).get('headers', [])
    for header in headers:
        header_name = header.get('name', '').lower()
        if header_name == 'from':
            from_email = header.get('value', '')
        elif header_name == 'to':
            # This is who the original message was sent to (likely the user's email)
            user_email = header.get('value', '')
        elif header_name == 'subject':
            # Don't add another "Re:" if it already has one
            subject_value = header.get('value', 'Email')
            if subject_value.lower().startswith('re:'):
                subject = subject_value
            else:
                subject = f"Re: {subject_value}"
        elif header_name == 'message-id':
            message_id_header = header.get('value', '')
        elif header_name == 'references':
            references_header = header.get('value', '')
        elif header_name == 'in-reply-to':
            in_reply_to_header = header.get('value', '')
    
    # For messages sent by the user (SENT label), we need to use the 'To' field as recipient
    # For messages received by the user, we use the 'From' field as recipient
    labels = original_message.get('labelIds', [])
    if 'SENT' in labels:
        # This is a message sent by the user, so reply to the recipient of the original message
        print(f"Message {message_id} has SENT label, extracting recipient from 'To' header")
        
        # Re-examine headers to find the 'To' field
        for header in headers:
            if header.get('name', '').lower() == 'to':
                to_email = header.get('value', '')
                break
    else:
        # This is a message received by the user, so reply to the sender
        to_email = from_email
    
    print(f"Sending reply to: {to_email}")
    
    if not to_email:
        print(f"Could not find recipient email for message {message_id}")
        return False
    
    # Create properly formatted email with threading headers
    raw_message = create_email_reply(to_email, subject, reply_content, thread_id, message_id_header, references_header, in_reply_to_header)
    
    # Send the email as a reply in the same thread
    message = {'raw': raw_message, 'threadId': thread_id}
    service.users().messages().send(
        userId='me',
        body=message
    ).execute()
    
    print(f"Reply sent in thread: {thread_id}")
    return True

# Helper function to extract and decode email content
def extract_email_content(email_message: dict) -> str:
    """Extract and decode email content from Gmail API message format"""
    # First try to get content from snippet
    content = email_message.get('snippet', '')
    
    # If no snippet, try to get from payload
    if not content:
        try:
            payload = email_message.get('payload', {})
            
            # Try to get content from body data
            body_data = payload.get('body', {}).get('data')
            if body_data:
                # Decode base64 content
                decoded_data = base64.urlsafe_b64decode(body_data).decode('utf-8')
                content = decoded_data
            
            # If still no content, try to get from parts
            if not content:
                parts = payload.get('parts', [])
                for part in parts:
                    mime_type = part.get('mimeType', '')
                    if mime_type == 'text/plain' or mime_type == 'text/html':
                        part_body = part.get('body', {})
                        part_data = part_body.get('data')
                        if part_data:
                            # Decode base64 content
                            decoded_part = base64.urlsafe_b64decode(part_data).decode('utf-8')
                            content = decoded_part
                            break
        except Exception as e:
            print(f"Error extracting email content: {e}")
    
    # Decode HTML entities
    if content:
        content = html.unescape(content)
        
        # Remove HTML tags if present
        content = re.sub(r'<[^>]+>', ' ', content)
        
        # Clean up whitespace
        content = re.sub(r'\s+', ' ', content).strip()
    
    return content

# Helper function to create a properly formatted email
def create_email_reply(to: str, subject: str, body: str, thread_id: str = None, 
                      message_id_header: str = None, references_header: str = None, 
                      in_reply_to_header: str = None) -> str:
    """Create a properly formatted email reply with threading headers"""
    message = MIMEMultipart()
    message['to'] = to
    message['subject'] = subject
    
    # Add threading headers to ensure the email appears in the same thread
    if message_id_header:
        # If we have the original message ID, add it to References and In-Reply-To
        if references_header:
            # If References already exists, append the new message ID
            message['References'] = f"{references_header} {message_id_header}"
        else:
            # Otherwise, create a new References header
            message['References'] = message_id_header
        
        # Set In-Reply-To to the original message ID
        message['In-Reply-To'] = message_id_header
    
    # Add body as text
    message.attach(MIMEText(body, 'plain'))
    
    # Encode as base64url string
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    return raw

# Tool to clean the mailbox by deleting spam/promotions
@gmail_agent.tool
async def clean_mailbox(ctx: RunContext[GmailDependencies]) -> int:
    service = await ctx.deps.get_gmail_service()
    results = service.users().messages().list(
        userId='me',
        labelIds=['SPAM', 'CATEGORY_PROMOTIONS'],
        maxResults=100
    ).execute()
    messages = results.get('messages', [])
    for msg in messages:
        service.users().messages().delete(
            userId='me',
            id=msg['id']
        ).execute()
    return len(messages)

# Define a RunContext wrapper to supply the dependencies and API.
class DummyRunContext(RunContext[GmailDependencies]):
    def __init__(self, deps: GmailDependencies, api=None):
        self.deps = deps
        self.api = api
        self.model = api
        self.prompt = "Gmail Assistant"
        self.usage = None
        self.messages = []
        self.run_step = 0
        self.retry = 0
        self.tool_name = None
        
    async def model(self, prompt: str, **kwargs) -> str:
        if self.api:
            return await self.api.generate_response(prompt)
        raise ValueError("API not set in DummyRunContext")

# Tool to remove star from an email
@gmail_agent.tool
async def remove_star_from_email(ctx: RunContext[GmailDependencies], message_id: str) -> bool:
    """Remove the star from an email after processing it"""
    service = await ctx.deps.get_gmail_service()
    try:
        # Remove STARRED label
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabelIds': ['STARRED']}
        ).execute()
        print(f"Removed star from email ID: {message_id}")
        return True
    except Exception as e:
        print(f"Error removing star from email ID {message_id}: {e}")
        return False

# Function to get the latest message in a thread
async def get_latest_message_in_thread(ctx: RunContext[GmailDependencies], message_id: str) -> tuple:
    """Get the latest message in a thread and determine if it should be processed
    
    Returns:
        tuple: (latest_message, should_process) where:
               - latest_message is the most recent message object
               - should_process is a boolean indicating if the message should be processed
    """
    service = await ctx.deps.get_gmail_service()
    try:
        # Get the thread ID for the message
        message = service.users().messages().get(userId='me', id=message_id, format='metadata').execute()
        thread_id = message.get('threadId')
        print(f"Thread ID: {thread_id}")
        
        # Get all messages in the thread
        thread = service.users().threads().get(userId='me', id=thread_id).execute()
        messages = thread.get('messages', [])
        print(f"Found {len(messages)} messages in thread")
        
        # Sort messages by internalDate (newest first)
        messages.sort(key=lambda x: int(x.get('internalDate', 0)), reverse=True)
        
        if not messages:
            print("No messages found in thread")
            return (None, False)
        
        # Get the latest message
        latest_message = messages[0]
        latest_message_id = latest_message.get('id')
        
        # Check if the latest message is from the agent (sent by 'me')
        # If it is, we don't need to process this thread again
        headers = latest_message.get('payload', {}).get('headers', [])
        for header in headers:
            if header.get('name', '').lower() == 'from':
                from_value = header.get('value', '').lower()
                if 'me@' in from_value or 'your.email@' in from_value or 'sofia' in from_value:
                    print(f"Latest message in thread (ID: {latest_message_id}) is from the agent; skipping.")
                    return (latest_message, False)
        
        # Check if any message in the thread is unread
        has_unread = False
        is_recent = False
        
        # Debug: Print all messages in the thread with their labels
        for i, msg in enumerate(messages):
            msg_id = msg.get('id')
            labels = msg.get('labelIds', [])
            print(f"Message {i+1} (ID: {msg_id}): Labels = {labels}")
            
            # Check if this message is unread
            if 'UNREAD' in labels:
                print(f"Found unread message: {msg_id}")
                has_unread = True
        
        # Check if the latest message is recent (within the last 24 hours)
        current_time = int(time.time() * 1000)  # Current time in milliseconds
        message_time = int(latest_message.get('internalDate', 0))
        time_diff = current_time - message_time
        
        # 24 hours = 86400000 milliseconds
        if time_diff < 86400000:
            is_recent = True
            print(f"Message is recent (within last 24 hours): {time_diff/3600000:.2f} hours old")
        else:
            print(f"Message is not recent: {time_diff/3600000:.2f} hours old")
        
        # Determine if we should process this message
        # Process if it has unread messages
        # We no longer process based on recency alone to avoid duplicate replies
        should_process = has_unread
        
        print(f"Final selection - Message ID: {latest_message_id}, Should process: {should_process}")
        print(f"Reason: has_unread={has_unread}, is_recent={is_recent}, is_starred={'STARRED' in latest_message.get('labelIds', [])}")
        
        # Get the full message details
        full_message = service.users().messages().get(
            userId='me',
            id=latest_message_id,
            format='full'
        ).execute()
        
        return (full_message, should_process)
    except Exception as e:
        print(f"Error getting messages in thread: {e}")
        return (None, False)

# Function to check if an email has been replied to by the agent
async def has_been_replied_to_by_agent(ctx: RunContext[GmailDependencies], message_id: str) -> bool:
    """Check if an email has already been replied to by the agent"""
    service = await ctx.deps.get_gmail_service()
    try:
        # Get the thread ID for the message
        message = service.users().messages().get(userId='me', id=message_id, format='metadata').execute()
        thread_id = message.get('threadId')
        
        # Get all messages in the thread
        thread = service.users().threads().get(userId='me', id=thread_id).execute()
        messages = thread.get('messages', [])
        
        # Sort messages by internalDate (newest first)
        messages.sort(key=lambda x: int(x.get('internalDate', 0)), reverse=True)
        
        # If there's only one message, it hasn't been replied to
        if len(messages) <= 1:
            return False
        
        # Check if the latest message is from the agent (sent by 'me')
        latest_message = messages[0]
        
        # Get the headers to check the 'From' field
        headers = latest_message.get('payload', {}).get('headers', [])
        for header in headers:
            if header.get('name', '').lower() == 'from':
                # If the latest message is from 'me', it means the agent has replied
                if 'me@' in header.get('value', '').lower() or 'your.email@' in header.get('value', '').lower():
                    print(f"Email ID {message_id} has already been replied to by the agent")
                    return True
        
        # If we get here, the latest message is not from the agent
        return False
    except Exception as e:
        print(f"Error checking if email ID {message_id} has been replied to by the agent: {e}")
        return False

# Helper functions for processing emails
async def is_message_from_agent(message):
    """Check if a message is from the agent"""
    headers = message.get('payload', {}).get('headers', [])
    for header in headers:
        if header.get('name', '').lower() == 'from':
            from_value = header.get('value', '').lower()
            if 'me@' in from_value or 'your.email@' in from_value or 'sofia' in from_value:
                return True
    return False

async def has_unread_messages(message):
    """Check if a message has the UNREAD label"""
    labels = message.get('labelIds', [])
    return 'UNREAD' in labels

async def find_message_to_respond(ctx: RunContext[GmailDependencies], thread_id: str):
    """Find the most recent unread message in a thread"""
    service = await ctx.deps.get_gmail_service()
    thread = service.users().threads().get(userId='me', id=thread_id).execute()
    messages = thread.get('messages', [])
    
    # Sort messages by internalDate (newest first)
    messages.sort(key=lambda x: int(x.get('internalDate', 0)), reverse=True)
    
    for message in messages:
        labels = message.get('labelIds', [])
        if 'UNREAD' in labels:
            # Get the full message
            full_message = service.users().messages().get(
                userId='me',
                id=message['id'],
                format='full'
            ).execute()
            return full_message
    
    return None

async def remove_star(ctx: RunContext[GmailDependencies], message_id: str):
    """Remove the star from an email"""
    return await remove_star_from_email(ctx, message_id)

# Main execution
async def main():
    """Main function to process emails"""
    # Check if we have a valid API key
    api_key = os.getenv("MY_OPENROUTER_API_KEY")
    if not api_key or api_key == "your_openrouter_api_key_here":
        print("\n---------------------------------------")
        print("WARNING: No valid OpenRouter API key found!")
        print("The app will run with placeholder responses.")
        print("Please set your API key in the .env file.")
        print("---------------------------------------\n")
    token_path = os.getenv('GMAIL_TOKEN_PATH', 'token.json')
    current_dir = os.path.dirname(os.path.abspath(__file__))
    absolute_token_path = os.path.join(current_dir, token_path)
    
    print(f"Current directory: {current_dir}")
    print(f"Looking for token file at: {absolute_token_path}")
    
    if not os.path.exists(absolute_token_path):
        raise FileNotFoundError(f"Token file not found at {absolute_token_path}. Please make sure token.json exists in this location.")
    
    creds = GoogleCredentials.from_authorized_user_file(absolute_token_path)
    
    async with httpx.AsyncClient() as client:
        # Initialize memory system
        memory = MemoryIntegration()
        deps = GmailDependencies(credentials=creds, client=client, memory=memory)
        
        # Use the DummyRunContext we defined earlier instead of RunContext directly
        ctx = DummyRunContext(deps=deps, api=router_api)
        
        # Process starred emails
        starred_emails = await fetch_starred_emails(ctx)
        print(f"Found {len(starred_emails)} starred emails")
        sent_replies = 0
        processed_count = 0
        
        for email in starred_emails:
            email_id = email['id']
            thread_id = email.get('threadId', '')
            print(f"Processing email ID: {email_id}")
            
            # Get the latest message in the thread and determine if it should be processed
            latest_message, should_process = await get_latest_message_in_thread(ctx, email_id)
            if not latest_message:
                print(f"Could not get messages for email ID {email_id}; skipping.")
                continue
            
            latest_message_id = latest_message['id']
            
            # Store message in memory system
            memory.process_email(latest_message, is_from_agent=False)
            
            # Skip if the message should not be processed
            if not should_process:
                print(f"Message (ID: {latest_message_id}) should not be processed; skipping.")
                await remove_star_from_email(ctx, email_id)
                continue
            
            # Extract email content using the helper function
            email_content = extract_email_content(latest_message)
            
            if not email_content:
                print(f"Email ID {email_id} has no content; skipping reply generation.")
                await remove_star_from_email(ctx, email_id)
                continue
            
            # Generate and send reply
            print(f"Email content: {email_content[:100]}...")  # Print first 100 chars
            try:
                # Generate reply with memory context
                reply = await generate_reply(ctx, email_content, thread_id)
                print(f"Generated reply: {reply[:100]}...")  # Print first 100 chars
                
                # Get the operation mode from environment variables
                operation_mode = os.getenv('OPERATION_MODE', 'draft').lower()
                
                # Either create a draft or send reply based on operation mode
                if operation_mode == 'auto':
                    print("Operating in AUTO mode: sending reply directly")
                    success = await send_reply(ctx, latest_message_id, reply)
                    action_description = "Reply sent"
                else:  # default to draft mode
                    print("Operating in DRAFT mode: creating draft for review")
                    success = await create_reply_draft(ctx, latest_message_id, reply)
                    action_description = "Draft created"
                
                if success:
                    sent_replies += 1
                    print(f"{action_description} for message ID: {latest_message_id}")
                    
                    # Get our sent message and add it to memory
                    sent_messages = await get_sent_messages(ctx, thread_id, 1)
                    if sent_messages:
                        memory.process_email(sent_messages[0], is_from_agent=True)
                    
                # Always remove the star after processing to prevent duplicate replies
                await remove_star_from_email(ctx, email_id)
                print(f"Removed star from email ID: {email_id} after processing")
                
                processed_count += 1
            except Exception as e:
                print(f"Error processing email ID {email_id}: {e}")
                continue
        
        # Clean mailbox
        cleaned_count = await clean_mailbox(ctx)
        print(f"Cleaned {cleaned_count} emails")
        
        result = GmailResult(
            processed_emails=processed_count,
            sent_replies=sent_replies,
            cleaned_emails=cleaned_count
        )
        print("Final result:", result)
        return result

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(main())
    print(result)

# Scheduling (to be implemented)
# For example, use APScheduler or a cron job to run main() daily.
