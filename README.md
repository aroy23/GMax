# GMax
**Recipient of the first-place prize at LA Hacks 2025 for the MSI Track**

## Overview
An AI-powered Chrome extension email assistant that automatically processes, organizes, analyzes, and responds to emails.<br>
![image](https://github.com/user-attachments/assets/3d79f5ad-cdf5-4cc5-94c7-ea0d9be1ae4c)

## Inspiration
GMax was created to address the growing problem of email overload. The average professional spends 28% of their workday reading and responding to emails, which amounts to 2.6 hours per day and 13 hours per week. This significant time investment reduces productivity and adds stress to daily work life. By leveraging AI to handle routine email interactions, GMax aims to give people back their time while ensuring important communications are still handled appropriately.

## What it does
GMax is a sophisticated email management system that uses AI to automatically process Gmail messages in real-time:

- **Real-time Email Processing**: Utilizes Gmail's push notification API and Google Cloud Pub/Sub to detect new emails as they arrive.
- **AI-powered Email Analysis**: Uses Google's Gemini AI to analyze email content, classify spam, and determine if a reply is needed.
- **Email Persona**: Indexes sent messages and creates and automatic "email persona" that generates emails in the same style as your emails
- **Automated Responses**: Generates high-quality, contextually appropriate replies to that follow your custom persona
- **Human-in-the-loop Confirmation**: Sends SMS notifications with email content and suggested replies for user approval.
- **Spam Protection**: Intelligently takes non spam emails out of the spam inbox, like those pesky job interviews.
- **Automatic Labeling**: Automatically label emails with the user created or AI generated labels.
- **Phishing Detection**: Automatically classify scam emails with AI powered phishing confidence.
- **Chrome Extension Interface**: Seamlessly integrates with Gmail through a user-friendly browser extension.
- **Toggleable Settings**: User controlled settings to customize your email experience.

## How we built it

### Backend
- **FastAPI Server**: Core API server handling requests, websocket connections, and background tasks.
- **Gmail API Integration**: Complete OAuth flow, email reading/sending, and watch notification management.
- **Email Processing Pipeline**: Multi-stage analysis system that extracts, processes, and categorizes email content. 
- **Database (Supabase)**: Stores user data, history, message confirmations, and automated actions.
- **Google Cloud Pub/Sub**: Manages real-time notifications from Gmail's push API.
- **SMS Confirmation System**: Sends text messages for approval of automated responses.

### Frontend
- **Chrome Extension**: A browser extension that injects UI components into Gmail.
- **Real-time Status Updates**: WebSocket connection for instant feedback on email processing.
- **Settings Management**: User interface for configuring automation preferences.
- **Quick Actions**: Quick buttons to perform important workflows

## Technologies

### Backend
- **FastAPI**: Web framework for building APIs with Python.
- **Google API Client**: For Gmail API integration.
- **Google Cloud Pub/Sub**: For real-time push notifications.
- **Google Generative AI**: Integration with Gemini for email analysis and response generation.
- **Supabase**: Database for storing user data and email processing history.
- **Selenium**: Automation for labeling emails
- **WebSockets**: For real-time communication with the frontend.
- **Textbelt**: SMS notifications and confirmations

### Frontend
- **React**: UI library for building the extension interface.
- **TypeScript**: For type-safe JavaScript code.
- **Axios**: HTTP client for API requests.
- **Chrome Extension API**: For browser extension functionality.
- **WebSockets**: For real-time updates from the backend.

## Key Features

### Email Intelligence
- Automatic classification of emails as spam or legitimate
- Intent recognition to determine if a reply is needed
- Smart prioritization based on content analysis

### Automation Workflow
- Real-time notification of new emails
- AI-generated draft replies
- SMS confirmation flow for user approval
- Automatic sending upon confirmation

### Security & Privacy
- Local token storage and secure API handling
- No permanent storage of email content
- Human-in-the-loop design for sensitive actions

### User Control
- Customizable settings for automation level
- Ability to review and modify AI-generated replies
- Complete history of automated actions

### Image Gallery

![image](https://github.com/user-attachments/assets/c277c1ad-0767-413a-98a2-d73dd3ef85fb)

![image](https://github.com/user-attachments/assets/89f430c6-0eb5-4b2f-9e6b-bc7f00619d3c)

![image](https://github.com/user-attachments/assets/a981bb72-0d6f-425b-b007-3ce453b040ee)

![image](https://github.com/user-attachments/assets/49e62cbf-269a-4f50-8e84-7726603da080)
