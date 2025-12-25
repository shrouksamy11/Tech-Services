import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import re
import time
import uuid
import logging
import altair as alt
from datetime import datetime, timedelta
from functools import wraps
from textwrap import dedent

# ==================== LOGGING SETUP ====================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== CHATBOT CLASS ====================
class Chatbot:
    def __init__(self, services):
        self.services = services
        self.context = {}

    def update_context(self, user_role, current_page):
        self.context['role'] = user_role
        self.context['page'] = current_page

    def get_response(self, user_input):
        user_input = user_input.lower().strip()
        # Greetings
        if any(word in user_input for word in ['hello', 'hi', 'hey', 'start', 'hola', 'marhaba']):
            return "مرحباً! 👋 أنا مساعد خدمة الربط. يمكنني مساعدتك في:\n- استعراض الخدمات والأسعار\n- حجز خدمة\n- التحقق من حالة الطلب\n- مساعدة الحساب\nType 'ar' للغة العربية"
        # Arabic support
        if any(word in user_input for word in ['عربي', 'arabic', 'ar', 'arab']):
            return "مرحباً! 👋 أنا مساعد خدمة الربط. يمكنني مساعدتك في:\n- استعراض الخدمات والأسعار\n- حجز خدمة\n- التحقق من حالة الطلب\n- مساعدة الحساب\nType 'en' للإنجليزية"
        # Services & Pricing
        if any(word in user_input for word in ['service', 'price', 'cost', 'how much', 'list', 'offer', 'cleaning', 'plumbing', 'tech', 'خدمة', 'سعر', 'كم']):
            response = "📋 **الخدمات المتاحة:**\n"
            for s in self.services[:5]:  # Show first 5 services
                response += f"📍 **{s['name']}** - ${s['price']} ({s['category']})\n"
            response += "\n💡 سجل الدخول كمستخدم لحجز أي خدمة!"
            response += "\nلعرض المزيد من الخدمات، انتقل إلى صفحة 'الخدمات'"
            return response
        # Booking / How to Order
        if any(word in user_input for word in ['book', 'order', 'reserve', 'buy', 'schedule', 'how', 'حجز', 'اطلب']):
            if self.context.get('role') == 'user':
                return "📝 **لحجز خدمة:**\n1. انتقل إلى صفحة الخدمات\n2. اضغط على 'اختر' بجانب الخدمة\n3. املأ نموذج الحجز\n4. تأكيد!"
            elif self.context.get('role') == 'technical':
                return "⚠️ كخبير فني، تقدم الخدمات ولا تحجزها. تحقق من صفحة الطلبات المعلقة."
            else:
                return "🔐 الرجاء **تسجيل الدخول** أو **التسجيل** كمستخدم لحجز الخدمات."
        # Technical / Orders
        if any(word in user_input for word in ['pending', 'job', 'work', 'task', 'order', 'طلب', 'عمل']):
            if self.context.get('role') == 'technical':
                return "🛠️ اعرض جميع المهام في **الطلبات المعلقة**. اضغط على 'تم الإنجاز' عند الانتهاء."
            elif self.context.get('role') == 'user':
                return "📦 تحقق من حجوزاتك في صفحة **طلباتي**."
            else:
                return "🔐 الرجاء تسجيل الدخول لعرض الطلبات."
        # Chat with technician
        if any(word in user_input for word in ['chat', 'message', 'talk', 'contact', 'technician', 'fani', 'شات', 'رسالة']):
            if self.context.get('role') == 'user':
                return "💬 **للتواصل مع الفني:**\n1. انتقل إلى صفحة 'طلباتي'\n2. اختر الطلب\n3. اضغط على '💬 التواصل مع الفني'\n4. ابدأ المحادثة مباشرة"
            elif self.context.get('role') == 'technical':
                return "💬 **للتواصل مع العميل:**\n1. انتقل إلى صفحة 'الطلبات المعلقة'\n2. اختر الطلب\n3. اضغط على '💬 التواصل مع العميل'\n4. ابدأ المحادثة مباشرة"
            else:
                return "🔐 الرجاء تسجيل الدخول للتواصل مع مقدمي الخدمة."
        # Account
        if any(word in user_input for word in ['login', 'sign in', 'register', 'sign up', 'account', 'حساب', 'تسجيل']):
            return "👤 **خيارات الحساب:**\n- **مستخدم**: حجز الخدمات\n- **فني**: تقديم الخدمات\nانتقل إلى الصفحة الرئيسية لتسجيل الدخول أو التسجيل."
        # About
        if any(word in user_input for word in ['about', 'who', 'company', 'mission', 'من', 'شركة']):
            return "🏢 **خدمة الربط** - ربط المحترفين المحليين مع العملاء. خدمات المنزل، التقنية، السيارات والصيانة."
        # Contact
        if any(word in user_input for word in ['contact', 'help', 'support', 'اتصال', 'مساعدة']):
            return "📞 **اتصل بنا:**\n- البريد الإلكتروني: support@serviceconnect.com\n- الهاتف: +1-234-567-8900\n- ساعات العمل: 9 صباحاً - 6 مساءً (بتوقيت المنطقة الزمنية الشرقية)\nيمكنك أيضًا استخدام نموذج الاتصال في صفحة 'اتصل بنا'."
        # Default Fallback
        return "❓ يمكنني المساعدة في:\n- الخدمات والأسعار\n- كيفية الحجز\n- مساعدة الحساب\n- حالة الطلب\nاسألني عن أي شيء!"

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="Service Connect Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

def md(html):
    st.markdown(dedent(html).strip(), unsafe_allow_html=True)

# ==================== MODERN DARK THEME CSS ====================
md("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
    background-color: #0b0f19;
    color: #ffffff !important;
}
.stApp {
    background: linear-gradient(135deg, #0b0f19 0%, #1a1f35 50%, #251e3e 100%);
    background-attachment: fixed;
}
.block-container {
    padding-top: 2rem;
    padding-right: 2rem;
    padding-left: 2rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}
/* Top Navigation Bar */
.nav-container {
    display: flex;
    justify-content: center;
    gap: 20px;
    padding: 15px 30px;
    background: rgba(20, 25, 45, 0.98);
    backdrop-filter: blur(15px);
    border-radius: 15px;
    box-shadow: 0 4px 25px rgba(0,0,0,0.6);
    margin-bottom: 30px;
    position: sticky;
    top: 10px;
    z-index: 1000;
    border: 1px solid rgba(255, 255, 255, 0.2);
}
/* Animations */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.05); }
    100% { transform: scale(1); }
}
@keyframes slideIn {
    from { opacity: 0; transform: translateX(-20px); }
    to { opacity: 1; transform: translateX(0); }
}
@keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-10px); }
}
.animate-enter {
    animation: fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
.animate-slide {
    animation: slideIn 0.5s ease-out forwards;
}
.pulse-animation {
    animation: pulse 2s infinite;
}
.bounce-animation {
    animation: bounce 0.5s infinite;
}
/* Chat System Styles */
.chat-container {
    background: rgba(20, 25, 45, 0.95);
    border-radius: 20px;
    padding: 25px;
    box-shadow: 0 15px 50px rgba(0,0,0,0.5);
    border: 1px solid rgba(108, 92, 231, 0.3);
    margin-bottom: 30px;
}
.chat-header {
    background: linear-gradient(135deg, #6c5ce7 0%, #8e44ad 100%);
    padding: 20px;
    border-radius: 15px;
    text-align: center;
    margin-bottom: 25px;
    position: relative;
    overflow: hidden;
}
.chat-header::before {
    content: '💬';
    position: absolute;
    top: 10px;
    right: 10px;
    font-size: 2rem;
    opacity: 0.3;
}
.chat-header h2 {
    color: white !important;
    margin: 0;
    font-size: 24px;
    font-weight: 700;
}
.chat-header p {
    color: rgba(255,255,255,0.9) !important;
    margin: 8px 0 0 0;
    font-size: 14px;
}
.chat-messages {

    max-height: 500px;
    overflow-y: auto;
    padding: 20px;
    background: rgba(26, 31, 53, 0.8);
    border-radius: 15px;
    margin-bottom: 20px;
    border: 1px solid rgba(255,255,255,0.1);
    scroll-behavior: smooth;
}
.chat-message {
    margin-bottom: 20px;
    padding: 15px;
    border-radius: 15px;
    max-width: 80%;
    position: relative;
    word-wrap: break-word;
}
.chat-message.user {
    background: linear-gradient(135deg, #6c5ce7 0%, #8e44ad 100%);
    margin-left: auto;
    border-bottom-right-radius: 5px;
}
.chat-message.tech {
    background: rgba(255, 255, 255, 0.1);
    margin-right: auto;
    border-bottom-left-radius: 5px;
    border: 1px solid rgba(255,255,255,0.2);
}
.chat-message-content {
    color: white !important;
    font-size: 15px;
    line-height: 1.5;
}
.chat-message-time {
    font-size: 11px;
    color: rgba(255,255,255,0.6) !important;
    text-align: right;
    margin-top: 5px;
}
.chat-message-sender {
    font-size: 12px;
    font-weight: bold;
    margin-bottom: 5px;
    color: rgba(255,255,255,0.9) !important;
}
/* Chat Input */
.chat-input-container {
    display: flex;
    gap: 10px;
    margin-top: 15px;
}
.chat-input-container textarea {
    flex-grow: 1;
    background: rgba(26, 31, 53, 0.9);
    border: 1px solid rgba(108, 92, 231, 0.5);
    border-radius: 12px;
    padding: 15px;
    color: white !important;
    font-size: 15px;
    resize: none;
    height: 70px;
}
.chat-input-container textarea:focus {
    border-color: #6c5ce7;
    box-shadow: 0 0 0 3px rgba(108, 92, 231, 0.2);
    outline: none;
}
/* Order Chat Badge */
.order-chat-badge {
    position: absolute;
    top: -8px;
    right: -8px;
    background: #e74c3c;
    color: white !important;
    font-size: 12px;
    font-weight: bold;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: bounce 1s infinite;
}
/* Chat Notification */
.chat-notification {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: linear-gradient(135deg, #6c5ce7 0%, #8e44ad 100%);
    color: white !important;
    padding: 15px 25px;
    border-radius: 12px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.4);
    z-index: 9999;
    animation: slideIn 0.5s ease-out;
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    transition: transform 0.3s ease;
}
.chat-notification:hover {
    transform: scale(1.05);
}
.chat-notification-close {
    background: none;
    border: none;
    color: white !important;
    font-size: 20px;
    cursor: pointer;
    padding: 0;
    margin-left: 10px;
}
/* Chat List */
.chat-list-container {
    background: rgba(20, 25, 45, 0.95);
    border-radius: 15px;
    padding: 20px;
    margin-bottom: 20px;
    border: 1px solid rgba(255,255,255,0.1);
}
.chat-list-item {
    background: rgba(30, 35, 60, 0.8);
    border-radius: 12px;
    padding: 15px;
    margin-bottom: 10px;
    border: 1px solid rgba(255,255,255,0.1);
    cursor: pointer;
    transition: all 0.3s ease;
    position: relative;
}
.chat-list-item:hover {
    background: rgba(108, 92, 231, 0.2);
    border-color: #6c5ce7;
    transform: translateX(5px);
}
.chat-list-item.active {
    background: rgba(108, 92, 231, 0.3);
    border-color: #6c5ce7;
}
.chat-list-item-unread {
    position: absolute;
    top: 15px;
    right: 15px;
    background: #e74c3c;
    color: white !important;
    font-size: 11px;
    font-weight: bold;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
}
.chat-list-info h4 {
    margin: 0 0 5px 0;
    color: #ffffff !important;
}
.chat-list-info p {
    margin: 0;
    color: rgba(255,255,255,0.7) !important;
    font-size: 13px;
}
.chat-list-time {
    font-size: 11px;
    color: rgba(255,255,255,0.5) !important;
    margin-top: 5px;
}
/* Hero Section */
.hero-section {
    text-align: center;
    padding: 80px 50px !important;
    background: rgba(30, 35, 60, 0.5);
    border-radius: 25px !important;
    box-shadow: 0 15px 50px rgba(0,0,0,0.7) !important;
    border: 1px solid #6c5ce7;
    margin-bottom: 50px;
    background-image: radial-gradient(circle at 10% 20%, rgba(108, 92, 231, 0.1) 0%, transparent 50%),
                      radial-gradient(circle at 90% 80%, rgba(142, 68, 173, 0.1) 0%, transparent 50%);
}
.hero-section h1 {
    color: #a29bfe !important;
    font-size: 3.5rem;
    margin-bottom: 20px;
    background: linear-gradient(135deg, #6c5ce7 0%, #a29bfe 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 5px 15px rgba(108, 92, 231, 0.3);
}
.hero-section p {
    color: #e0e0e0 !important;
    font-size: 1.2rem;
}
/* Service Cards */
.service-card {
    background: linear-gradient(135deg, #1e233c 0%, #252947 100%);
    border-radius: 18px;
    padding: 28px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.4);
    transition: all 0.3s ease;
    border: 1px solid rgba(255, 255, 255, 0.15);
    height: 320px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    margin-bottom: 20px;
    position: relative;
    overflow: hidden;
}
.service-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, #6c5ce7, #8e44ad);
}
.service-card:hover {
    transform: translateY(-10px) scale(1.02);
    box-shadow: 0 20px 50px rgba(108, 92, 231, 0.4);
    border-color: #6c5ce7;
}
.card-icon {
    font-size: 50px;
    margin-bottom: 10px;
    text-align: center;
    filter: drop-shadow(0 5px 10px rgba(108, 92, 231, 0.5));
}
.card-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: #ffffff !important;
    margin-bottom: 5px;
}
.card-category {
    display: inline-block;
    background: linear-gradient(135deg, #6c5ce7 0%, #8e44ad 100%);
    color: #ffffff !important;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 10px;
    width: fit-content;
    box-shadow: 0 4px 10px rgba(108, 92, 231, 0.3);
}
.card-desc {
    color: #e0e0e0 !important;
    flex-grow: 1;
    margin-bottom: 15px;
    font-size: 14px;
    line-height: 1.5;
}
.card-price {
    font-size: 1.8rem;
    font-weight: 700;
    color: #a29bfe !important;
    margin-top: 10px;
    text-shadow: 0 3px 10px rgba(108, 92, 231, 0.5);
}
.card-rating {
    color: #f1c40f !important;
    font-size: 14px;
    margin-top: 5px;
}
/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #6c5ce7 0%, #8e44ad 100%);
    color: white !important;
    border: none;
    padding: 14px 28px;
    border-radius: 14px;
    font-weight: 700;
    transition: all 0.3s ease;
    width: 100%;
    box-shadow: 0 6px 20px rgba(108, 92, 231, 0.5);
    font-size: 17px;
    letter-spacing: 0.5px;
    position: relative;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
}
.stButton > button::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    transition: 0.5s;
}
.stButton > button:hover {
    transform: scale(1.05);
    background: linear-gradient(135deg, #8e44ad 0%, #6c5ce7 100%) !important;
    color: white !important;
    box-shadow: 0 0 35px rgba(108, 92, 231, 0.9);
}
.stButton > button:hover::before {
    left: 100%;
}
/* Special Button Styles */
.btn-primary {
    background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%) !important;
}
.btn-secondary {
    background: linear-gradient(135deg, #ff7e5f 0%, #feb47b 100%) !important;
}
/* Form Elements */
div[data-testid="stForm"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stSelectbox"] label,
div[data-testid="stDateInput"] label {
    color: #ffffff !important;
    font-weight: 600;
}
input[type="text"],
input[type="password"],
input[type="email"],
textarea {
    background-color: #1a1f35 !important;
    color: #ffffff !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 12px;
    padding: 12px 16px !important;
    font-size: 16px;
    transition: all 0.3s ease;
}
input[type="text"]:focus,
input[type="password"]:focus,
input[type="email"]:focus,
textarea:focus {
    border-color: #6c5ce7 !important;
    box-shadow: 0 0 0 3px rgba(108, 92, 231, 0.3) !important;
    outline: none;
}
/* Select Box */
div[data-baseweb="select"] > div {
    background-color: #1a1f35 !important;
    color: #ffffff !important;
    border: 1px solid #6c5ce7 !important;
    border-radius: 12px;
    padding: 4px 12px !important;
}
div[data-baseweb="select"] span {
    color: #ffffff !important;
}
/* Text Colors */
h1, h2, h3, h4, h5, h6 {
    color: #ffffff !important;
    font-weight: 700 !important;
}
h1 {
    font-size: 2.8rem !important;
    margin-bottom: 1rem !important;
    background: linear-gradient(135deg, #6c5ce7 0%, #a29bfe 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
h2 {
    font-size: 2.2rem !important;
    margin-bottom: 1rem !important;
}
/* Chatbot Container */
.chatbot-container {
    background: rgba(30, 35, 60, 0.95);
    border-radius: 15px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    border: 1px solid rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
}
.chatbot-header {
    background: linear-gradient(135deg, #6c5ce7 0%, #8e44ad 100%);
    padding: 20px;
    border-radius: 10px;
    text-align: center;
    margin-bottom: 20px;
    position: relative;
    overflow: hidden;
}
.chatbot-header::before {
    content: '🤖';
    position: absolute;
    top: 10px;
    right: 10px;
    font-size: 2rem;
    opacity: 0.3;
}
.chatbot-header h2 {
    color: white !important;
    margin: 0;
    font-size: 24px;
    font-weight: 700;
}
.chatbot-header p {
    color: rgba(255,255,255,0.9) !important;
    margin: 8px 0 0 0;
    font-size: 14px;
}
.chat-messages-area {
    min-height: 300px;
    max-height: 400px;
    overflow-y: auto;
    padding: 15px;
    background: linear-gradient(135deg, #1a1f35 0%, #252947 100%);
    border-radius: 10px;
    margin-bottom: 15px;
    border: 1px solid rgba(255,255,255,0.1);
    scroll-behavior: smooth;
}
.chat-messages-area * {
    color: #ffffff !important;
}
/* Custom scrollbar */
.chat-messages-area::-webkit-scrollbar {
    width: 6px;
}
.chat-messages-area::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 3px;
}
.chat-messages-area::-webkit-scrollbar-thumb {
    background: linear-gradient(135deg, #6c5ce7 0%, #8e44ad 100%);
    border-radius: 3px;
}
/* Status Badges */
.status-badge {
    display: inline-block;
    padding: 5px 12px;
    border-radius: 12px;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.status-pending {
    background: #f1c40f20;
    color: #f1c40f;
    border: 1px solid #f1c40f;
    box-shadow: 0 3px 10px rgba(241, 196, 15, 0.2);
}
.status-done {
    background: #2ecc7120;
    color: #2ecc71;
    border: 1px solid #2ecc71;
    box-shadow: 0 3px 10px rgba(46, 204, 113, 0.2);
}
.status-cancelled {
    background: #e74c3c20;
    color: #e74c3c;
    border: 1px solid #e74c3c;
    box-shadow: 0 3px 10px rgba(231, 76, 60, 0.2);
}
/* Stats Cards */
.stats-card {
    background: linear-gradient(135deg, #1e233c 0%, #252947 100%);
    border-radius: 15px;
    padding: 25px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.4);
    border: 1px solid rgba(255, 255, 255, 0.1);
    text-align: center;
    transition: all 0.3s ease;
}
.stats-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 15px 40px rgba(108, 92, 231, 0.3);
}
.stats-card h3 {
    font-size: 2rem !important;
    margin-bottom: 5px !important;
    color: #a29bfe !important;
}
.stats-card p {
    color: #e0e0e0 !important;
    font-size: 14px;
    margin: 0 !important;
}
/* Notification */
.notification {
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 15px 25px;
    border-radius: 10px;
    background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
    color: white !important;
    box-shadow: 0 10px 25px rgba(0,0,0,0.3);
    z-index: 10000;
    animation: slideIn 0.5s ease-out;
    display: flex;
    align-items: center;
    gap: 10px;
}
.notification.error {
    background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
}
.notification.warning {
    background: linear-gradient(135deg, #f1c40f 0%, #f39c12 100%);
}
/* Loading Animation */
.loading {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100px;
}
.loading-spinner {
    width: 40px;
    height: 40px;
    border: 4px solid rgba(108, 92, 231, 0.3);
    border-top: 4px solid #6c5ce7;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}
@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
/* Feature Cards */
.feature-card {
    background: rgba(30, 35, 60, 0.8);
    border-radius: 15px;
    padding: 30px;
    text-align: center;
    border: 1px solid rgba(255, 255,255, 0.1);
    transition: all 0.3s ease;
    height: 250px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}
.feature-card:hover {
    transform: translateY(-10px);
    border-color: #6c5ce7;
    box-shadow: 0 15px 40px rgba(108, 92, 231, 0.3);
}
.feature-icon {
    font-size: 3rem;
    margin-bottom: 20px;
    background: linear-gradient(135deg, #6c5ce7 0%, #8e44ad 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
/* Profile Card */
.profile-card {
    background: linear-gradient(135deg, #1e233c 0%, #252947 100%);
    border-radius: 20px;
    padding: 40px;
    box-shadow: 0 15px 50px rgba(0,0,0,0.5);
    border: 1px solid rgba(255, 255, 255, 0.1);
    text-align: center;
}
.profile-avatar {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    background: linear-gradient(135deg, #6c5ce7 0%, #8e44ad 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 3rem;
    margin: 0 auto 20px;
    box-shadow: 0 10px 30px rgba(108, 92, 231, 0.5);
}
</style>
""")

# ==================== DATABASE MANAGER ====================
class DatabaseManager:
    def __init__(self, db_path="service_connect.db"):
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._create_tables()
        self._seed_initial_data()

    def _connect(self):
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.execute("PRAGMA foreign_keys = ON")
            logger.info("Database connection established")
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            st.error("Failed to connect to database")

    def _create_tables(self):
        if not self.conn:
            return
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'technical', 'admin')),
                status TEXT DEFAULT 'Active',
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                phone TEXT,
                bio TEXT
            )
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                description TEXT,
                icon TEXT,
                rating REAL DEFAULT 4.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                booking_date TEXT NOT NULL,
                status TEXT DEFAULT 'Pending',
                payment_method TEXT,
                notes TEXT,
                price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (service_id) REFERENCES services(id)
            )
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS contact_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'Unread',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            # New table for chat messages
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                sender_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (sender_id) REFERENCES users(id)
            )
            ''')
            # New table for order technicians assignment
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_technicians (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                technician_id INTEGER NOT NULL,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (technician_id) REFERENCES users(id)
            )
            ''')
            self.conn.commit()
            logger.info("Database tables created successfully")
        except sqlite3.Error as e:
            logger.error(f"Error creating tables: {e}")

    def _seed_initial_data(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            if cursor.fetchone()[0] == 0:
                admin_hash = self._hash_password("admin123")
                cursor.execute('''
                INSERT INTO users (email, password_hash, name, role, bio)
                VALUES (?, ?, ?, ?, ?)
                ''', ('admin@serviceconnect.com', admin_hash, 'Admin', 'admin', 'System Administrator'))
                cursor.execute('''
                INSERT INTO users (email, password_hash, name, role, bio)
                VALUES (?, ?, ?, ?, ?)
                ''', ('user@example.com', self._hash_password('user'), 'Demo User', 'user', 'Regular user account for testing'))
                cursor.execute('''
                INSERT INTO users (email, password_hash, name, role, bio)
                VALUES (?, ?, ?, ?, ?)
                ''', ('tech@example.com', self._hash_password('tech'), 'Demo Tech', 'technical', 'Professional service provider'))
                # Add more technicians
                technicians = [
                    ('ahmed@example.com', 'tech123', 'Ahmed Hassan', 'Professional plumber with 10 years experience', '+201234567890'),
                    ('mohamed@example.com', 'tech123', 'Mohamed Ali', 'Electrical engineer specialist', '+201234567891'),
                    ('sara@example.com', 'tech123', 'Sara Mahmoud', 'Cleaning service expert', '+201234567892'),
                ]
                for email, password, name, bio, phone in technicians:
                    cursor.execute('''
                    INSERT INTO users (email, password_hash, name, role, bio, phone)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (email, self._hash_password(password), name, 'technical', bio, phone))
            cursor.execute("SELECT COUNT(*) FROM services")
            if cursor.fetchone()[0] == 0:
                services = [
                    ('House Cleaning', 'Home', 50, 'Deep cleaning service for your entire home', '🧹', 4.7),
                    ('Plumbing Repair', 'Maintenance', 80, 'Fix leaks and drainage issues', '🔧', 4.8),
                    ('Tech Support', 'Tech', 60, 'Computer troubleshooting and setup', '💻', 4.9),
                    ('Mobile Mechanic', 'Auto', 90, 'Car repair at your location', '🚗', 4.6),
                    ('Locksmith', 'Maintenance', 60, 'Lock replacement and key making', '🔑', 4.8),
                    ('Lighting Install', 'Maintenance', 80, 'Professional light fixture installation', '💡', 4.7),
                    ('Air Conditioning', 'Home', 120, 'AC installation and repair', '❄️', 4.9),
                    ('Electrical Wiring', 'Maintenance', 100, 'Safe electrical wiring solutions', '⚡', 4.8),
                    ('Carpet Cleaning', 'Home', 70, 'Deep carpet cleaning and stain removal', '🧽', 4.6),
                    ('Painting Service', 'Home', 200, 'Interior and exterior painting', '🎨', 4.7),
                ]
                cursor.executemany('''
                INSERT INTO services (name, category, price, description, icon, rating)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', services)
            self.conn.commit()
            logger.info("Initial data seeded")
        except sqlite3.Error as e:
            logger.error(f"Error seeding data: {e}")

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate_user(self, email, password):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT id, email, name, role, password_hash
            FROM users WHERE email = ? AND is_active = 1
            ''', (email,))
            user = cursor.fetchone()
            if not user:
                return False, "Invalid credentials"
            user_id, db_email, name, role, db_hash = user
            if self._hash_password(password) == db_hash:
                cursor.execute('UPDATE users SET last_login = ? WHERE id = ?',
                               (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id))
                self.conn.commit()
                return True, {"id": user_id, "email": db_email, "name": name, "role": role}
            return False, "Invalid credentials"
        except sqlite3.Error as e:
            logger.error(f"Auth error: {e}")
            return False, "System error"

    def register_user(self, email, password, name, role, phone=None, bio=None):
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users WHERE email = ?', (email,))
            if cursor.fetchone()[0] > 0:
                return False, "Email already exists"
            password_hash = self._hash_password(password)
            cursor.execute('''
            INSERT INTO users (email, password_hash, name, role, phone, bio)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (email, password_hash, name, role, phone, bio))
            self.conn.commit()
            return True, "Registration successful"
        except sqlite3.Error as e:
            logger.error(f"Registration error: {e}")
            return False, "System error"

    def get_services(self, category=None):
        try:
            cursor = self.conn.cursor()
            if category and category != "All":
                cursor.execute('SELECT * FROM services WHERE category = ?', (category,))
            else:
                cursor.execute('SELECT * FROM services')
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            return [dict(zip(columns, row)) for row in data]
        except sqlite3.Error as e:
            logger.error(f"Error getting services: {e}")
            return []

    def create_order(self, user_id, service_id, booking_date, payment_method, notes, price):
        try:
            order_id = str(uuid.uuid4())
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO orders (id, user_id, service_id, booking_date, payment_method, notes, price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (order_id, user_id, service_id, booking_date, payment_method, notes, price))
            self.conn.commit()
            return True, order_id
        except sqlite3.Error as e:
            logger.error(f"Error creating order: {e}")
            return False, None

    def get_user_orders(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT o.*, s.name as service_name, s.icon
            FROM orders o
            JOIN services s ON o.service_id = s.id
            WHERE o.user_id = ?
            ORDER BY o.created_at DESC
            ''', (user_id,))
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            return [dict(zip(columns, row)) for row in data]
        except sqlite3.Error as e:
            logger.error(f"Error getting orders: {e}")
            return []

    def get_pending_orders(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT o.*, s.name as service_name, u.name as user_name,
                   u.email as user_email, u.phone as user_phone,
                   (SELECT COUNT(*) FROM chat_messages WHERE order_id = o.id AND is_read = 0 AND sender_id != ?) as unread_count
            FROM orders o
            JOIN services s ON o.service_id = s.id
            JOIN users u ON o.user_id = u.id
            WHERE o.status = 'Pending'
            ORDER BY o.created_at DESC
            ''', (user_id,))
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            return [dict(zip(columns, row)) for row in data]
        except sqlite3.Error as e:
            logger.error(f"Error getting pending orders: {e}")
            return []

    def update_order_status(self, order_id, status):
        try:
            cursor = self.conn.cursor()
            cursor.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error updating order: {e}")
            return False

    def get_dashboard_stats(self):
        try:
            cursor = self.conn.cursor()
            stats = {}
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'user'")
            stats['total_users'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'technical'")
            stats['total_techs'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM orders")
            stats['total_orders'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'Pending'")
            stats['pending_orders'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'Done'")
            stats['completed_orders'] = cursor.fetchone()[0]
            cursor.execute("SELECT SUM(price) FROM orders WHERE status = 'Done'")
            stats['revenue'] = cursor.fetchone()[0] or 0
            cursor.execute("SELECT COUNT(*) FROM services")
            stats['total_services'] = cursor.fetchone()[0]
            return stats
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

    def get_all_orders(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT o.*, s.name as service_name, u.name as user_name
            FROM orders o
            JOIN services s ON o.service_id = s.id
            JOIN users u ON o.user_id = u.id
            ORDER BY o.created_at DESC
            ''')
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting all orders: {e}")
            return []

    def get_user_profile(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT name, email, role, join_date, last_login, phone, bio
            FROM users WHERE id = ?
            ''', (user_id,))
            columns = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
            if row:
                return dict(zip(columns, row))
            return None
        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            return None

    def update_user_profile(self, user_id, name, phone, bio):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            UPDATE users SET name = ?, phone = ?, bio = ? WHERE id = ?
            ''', (name, phone, bio, user_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating profile: {e}")
            return False

    def save_contact_message(self, name, email, subject, message):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO contact_messages (name, email, subject, message)
            VALUES (?, ?, ?, ?)
            ''', (name, email, subject, message))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving contact: {e}")
            return False

    # ==================== CHAT SYSTEM METHODS ====================
    def save_chat_message(self, order_id, sender_id, message):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO chat_messages (order_id, sender_id, message)
            VALUES (?, ?, ?)
            ''', (order_id, sender_id, message))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error saving chat message: {e}")
            return False

    def get_chat_messages(self, order_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT cm.*, u.name as sender_name, u.role as sender_role
            FROM chat_messages cm
            JOIN users u ON cm.sender_id = u.id
            WHERE cm.order_id = ?
            ORDER BY cm.created_at ASC
            ''', (order_id,))
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            return [dict(zip(columns, row)) for row in data]
        except sqlite3.Error as e:
            logger.error(f"Error getting chat messages: {e}")
            return []

    def mark_messages_as_read(self, order_id, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            UPDATE chat_messages
            SET is_read = 1
            WHERE order_id = ? AND sender_id != ? AND is_read = 0
            ''', (order_id, user_id))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error marking messages as read: {e}")
            return False

    def get_unread_message_count(self, user_id, role):
        try:
            cursor = self.conn.cursor()
            if role == 'user':
                cursor.execute('''
                SELECT COUNT(*)
                FROM chat_messages cm
                JOIN orders o ON cm.order_id = o.id
                JOIN users u ON cm.sender_id = u.id
                WHERE o.user_id = ? AND cm.is_read = 0 AND u.role = 'technical'
                ''', (user_id,))
            else:
                cursor.execute('''
                SELECT COUNT(*)
                FROM chat_messages cm
                JOIN users u ON cm.sender_id = u.id
                JOIN orders o ON cm.order_id = o.id
                WHERE cm.is_read = 0 AND u.role = 'user' AND o.status = 'Pending'
                ''')
            return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Error getting unread count: {e}")
            return 0

    def get_user_chats(self, user_id, role):
        try:
            cursor = self.conn.cursor()
            if role == 'user':
                cursor.execute('''
                SELECT DISTINCT o.id as order_id, s.name as service_name,
                       o.status, o.created_at, o.booking_date,
                       (SELECT COUNT(*) FROM chat_messages
                        WHERE order_id = o.id AND is_read = 0 AND sender_id != ?) as unread_count
                FROM orders o
                JOIN services s ON o.service_id = s.id
                WHERE o.user_id = ?
                ORDER BY o.created_at DESC
                ''', (user_id, user_id))
            else:  # technician
                cursor.execute('''
                SELECT DISTINCT o.id as order_id, s.name as service_name,
                       u.name as user_name, o.status, o.created_at, o.booking_date,
                       (SELECT COUNT(*) FROM chat_messages
                        WHERE order_id = o.id AND is_read = 0 AND sender_id != ?) as unread_count
                FROM orders o
                JOIN services s ON o.service_id = s.id
                JOIN users u ON o.user_id = u.id
                WHERE o.status = 'Pending'
                ORDER BY o.created_at DESC
                ''', (user_id,))
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            return [dict(zip(columns, row)) for row in data]
        except sqlite3.Error as e:
            logger.error(f"Error getting user chats: {e}")
            return []

    def get_order_details(self, order_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT o.*, s.name as service_name, s.icon,
                   u.name as user_name, u.email as user_email, u.phone as user_phone,
                   t.name as technician_name, t.email as technician_email, t.phone as technician_phone
            FROM orders o
            JOIN services s ON o.service_id = s.id
            JOIN users u ON o.user_id = u.id
            LEFT JOIN order_technicians ot ON o.id = ot.order_id
            LEFT JOIN users t ON ot.technician_id = t.id
            WHERE o.id = ?
            ''', (order_id,))
            columns = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
            if row:
                return dict(zip(columns, row))
            return None
        except sqlite3.Error as e:
            logger.error(f"Error getting order details: {e}")
            return None

    def assign_technician_to_order(self, order_id, technician_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM order_technicians WHERE order_id = ?', (order_id,))
            cursor.execute('''
            INSERT INTO order_technicians (order_id, technician_id)
            VALUES (?, ?)
            ''', (order_id, technician_id))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error assigning technician: {e}")
            return False

    def get_available_technicians(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT id, name, email, phone, bio
            FROM users
            WHERE role = 'technical' AND is_active = 1
            ORDER BY name
            ''')
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            return [dict(zip(columns, row)) for row in data]
        except sqlite3.Error as e:
            logger.error(f"Error getting technicians: {e}")
            return []

    def close(self):
        if self.conn:
            self.conn.close()

# ==================== SESSION STATE ====================
@st.cache_resource
def get_db_manager():
    return DatabaseManager()

db = get_db_manager()

# Initialize session state
if 'current_user' not in st.session_state:
    st.session_state['current_user'] = None
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'Home'
if 'selected_service' not in st.session_state:
    st.session_state['selected_service'] = None
if 'selected_role_reg' not in st.session_state:
    st.session_state['selected_role_reg'] = 'user'
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []
if 'chatbot' not in st.session_state:
    st.session_state['chatbot'] = Chatbot(db.get_services())
if 'current_chat_order' not in st.session_state:
    st.session_state['current_chat_order'] = None

# ==================== HELPER FUNCTIONS ====================
def logout():
    st.session_state['current_user'] = None
    st.session_state['current_page'] = 'Home'
    st.session_state['current_chat_order'] = None
    st.rerun()

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    pattern = r'^\+?[1-9]\d{1,14}$'
    return re.match(pattern, phone) is not None if phone else True

def show_notification(message, type='success'):
    if type == 'success':
        st.success(message)
    elif type == 'error':
        st.error(message)
    elif type == 'warning':
        st.warning(message)
    else:
        st.info(message)

def format_datetime(dt_string):
    if not dt_string:
        return "N/A"
    try:
        dt = datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%I:%M %p')
    except:
        return dt_string[:10]

# ==================== NAVIGATION ====================
def show_navigation():
    user = st.session_state['current_user']
    if not user:
        return
    menu_items = {
        'user': ["Home", "Services", "My Orders", "My Chats", "Profile", "About", "Contact Us", "Logout"],
        'technical': ["Home", "Pending Orders", "My Chats", "Profile", "About", "Contact Us", "Logout"],
        'admin': ["Home", "Dashboard", "All Orders", "Analytics", "Profile", "About", "Contact Us", "Logout"]
    }
    menu = menu_items.get(user['role'], [])
    unread_count = db.get_unread_message_count(user['id'], user['role'])
    # ✅ Fixed: now <div> and </div> are inside a single md() call — no broken HTML
    html_nav = '<div class="nav-container">'
    cols = st.columns(len(menu))
    for i, item in enumerate(menu):
        button_text = item
        if item == "My Chats" and unread_count > 0:
            button_text = f"💬 My Chats ({unread_count})"
        with cols[i]:
            if st.button(button_text, key=f"nav_{item}", use_container_width=True):
                if item == "Logout":
                    logout()
                else:
                    st.session_state['current_page'] = item
                    st.session_state['selected_service'] = None
                    st.session_state['current_chat_order'] = None
                    st.rerun()
    html_nav += '</div>'
    md(html_nav)

# ==================== CHAT SYSTEM PAGES ====================
def chat_page():
    user = st.session_state['current_user']
    if not user:
        show_notification("Please login first", 'error')
        st.session_state['current_page'] = 'Home'
        st.rerun()
        return
    st.title("💬 My Chats")
    chats = db.get_user_chats(user['id'], user['role'])
    if not chats:
        st.info("No chats yet. Start by booking a service or accepting a pending order!")
        return
    # Display chat list
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Conversations")
        for chat in chats:
            is_active = st.session_state.get('current_chat_order') == chat['order_id']
            # ✅ Fixed: all HTML in one md() — no partial <div> outside
            md(f"""
            <div class="chat-list-item {'active' if is_active else ''}"
                 style="position: relative; cursor: pointer;">
            {f"<span class='order-chat-badge'>{chat['unread_count']}</span>" if chat.get('unread_count', 0) > 0 else ""}
            <div class="chat-list-info">
            <h4>{chat['service_name']}</h4>
            <p>Status: {chat['status']}</p>
            <p>Date: {chat['booking_date']}</p>
            {('<p style="color: #f1c40f;">👤 ' + chat.get('user_name', 'User') + '</p>' if 'user_name' in chat else '')}
            </div>
            </div>
            """)
            if st.button(f"Select Chat", key=f"select_{chat['order_id']}",
                         use_container_width=True, help=f"Select chat for {chat['service_name']}"):
                st.session_state['current_chat_order'] = chat['order_id']
                db.mark_messages_as_read(chat['order_id'], user['id'])
                st.rerun()
    with col2:
        if st.session_state.get('current_chat_order'):
            order_id = st.session_state['current_chat_order']
            user = st.session_state['current_user']
            order = db.get_order_details(order_id)
            if not order:
                st.error("Order not found")
                return
            messages = db.get_chat_messages(order_id)
            other_party_name = order['technician_name'] if user['role'] == 'user' else order['user_name']
            other_party_role = "Technician" if user['role'] == 'user' else "Client"
            md(f"""
            <div class="chat-header">
                <h2>{order['service_name']}</h2>
                <p>Chat with {other_party_name} ({other_party_role})</p>
                <p style="font-size: 12px; margin-top: 5px;">Order ID: {order_id[:8]}...</p>
            </div>
            <div class="chat-messages">
            """)
            if not messages:
                md("""
                <div style="text-align: center; padding: 40px; color: rgba(255,255,255,0.5);">
                    <p style="font-size: 1.2rem;">💬 No messages yet</p>
                    <p>Start the conversation by sending a message below!</p>
                </div>
                """)
            else:
                for msg in messages:
                    is_current_user = msg['sender_id'] == user['id']
                    message_class = "user" if is_current_user else "tech"
                    md(f"""
                    <div class="chat-message {message_class}">
                    <div class="chat-message-sender">
                    {msg['sender_name']} ({'You' if is_current_user else msg['sender_role'].capitalize()})
                    </div>
                    <div class="chat-message-content">
                    {msg['message']}
                    </div>
                    <div class="chat-message-time">
                    {format_datetime(msg['created_at'])}
                    </div>
                    </div>
                    """)
            md('</div>')
            # Send message form
            with st.form(key="chat_message_form"):
                message = st.text_area("Type your message...", height=80,
                                       placeholder="Write your message here...")
                col1, col2 = st.columns([3, 1])
                with col2:
                    if st.form_submit_button("Send", use_container_width=True):
                        if message.strip():
                            if db.save_chat_message(order_id, user['id'], message.strip()):
                                db.mark_messages_as_read(order_id, user['id'])
                                st.rerun()
                            else:
                                show_notification("Failed to send message", 'error')
                        else:
                            st.warning("Message cannot be empty.")
        else:
            st.info("👈 Select a conversation from the list")

# ==================== PAGES ====================
def home_page():
    if st.session_state['current_user']:
        role = st.session_state['current_user']['role']
        if role == 'user':
            st.session_state['current_page'] = 'Services'
        elif role == 'technical':
            st.session_state['current_page'] = 'Pending Orders'
        elif role == 'admin':
            st.session_state['current_page'] = 'Dashboard'
        st.rerun()
        return
    md("""
    <div class="hero-section animate-enter">
        <h1>⚡ Service Connect Platform</h1>
        <p>Your reliable partner for booking and providing local services</p>
    </div>
    """)
    # Features Section
    md("<h2 style='text-align: center; margin: 40px 0 20px;'>🌟 Why Choose Us?</h2>")
    features = st.columns(3)
    with features[0]:
        md("""
        <div class="feature-card">
            <div class="feature-icon">⚡</div>
            <h3>Fast Service</h3>
            <p>Quick response and efficient service delivery</p>
        </div>
        """)
    with features[1]:
        md("""
        <div class="feature-card">
            <div class="feature-icon">🛡️</div>
            <h3>Verified Experts</h3>
            <p>All technicians are verified and experienced</p>
        </div>
        """)
    with features[2]:
        md("""
        <div class="feature-card">
            <div class="feature-icon">💬</div>
            <h3>Direct Chat</h3>
            <p>Communicate directly with service providers</p>
        </div>
        """)
    # Quick Stats
    stats = db.get_dashboard_stats()
    md("<h2 style='text-align: center; margin: 50px 0 20px;'>📊 Quick Stats</h2>")
    stats_cols = st.columns(4)
    with stats_cols[0]:
        md(f"""
        <div class="stats-card">
            <h3>{stats.get('total_services', 0)}+</h3>
            <p>Services</p>
        </div>
        """)
    with stats_cols[1]:
        md(f"""
        <div class="stats-card">
            <h3>{stats.get('total_orders', 0)}+</h3>
            <p>Orders</p>
        </div>
        """)
    with stats_cols[2]:
        md(f"""
        <div class="stats-card">
            <h3>{stats.get('total_techs', 0)}+</h3>
            <p>Experts</p>
        </div>
        """)
    with stats_cols[3]:
        md(f"""
        <div class="stats-card">
            <h3>${stats.get('revenue', 0):.0f}+</h3>
            <p>Saved</p>
        </div>
        """)
    # Action Buttons
    md("<br>")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("🔐 LOGIN", key="home_login", use_container_width=True):
            st.session_state['current_page'] = "Login"
            st.rerun()
    with col3:
        if st.button("🚀 REGISTER", key="home_register", use_container_width=True):
            st.session_state['current_page'] = "Register"
            st.rerun()

def login_page():
    if st.button("← Back to Home"):
        st.session_state['current_page'] = 'Home'
        st.rerun()
    md("<h2 style='text-align: center;'>Welcome Back! 👋</h2>")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login", use_container_width=True):
            success, result = db.authenticate_user(email, password)
            if success:
                st.session_state['current_user'] = result
                show_notification(f"✅ Welcome {result['name']}!", 'success')
                time.sleep(0.5)
                # Redirect based on role
                if result['role'] == 'user':
                    st.session_state['current_page'] = 'Services'
                elif result['role'] == 'technical':
                    st.session_state['current_page'] = 'Pending Orders'
                elif result['role'] == 'admin':
                    st.session_state['current_page'] = 'Dashboard'
                st.rerun()
            else:
                show_notification(result, 'error')

def register_page():
    if st.button("← Back to Home"):
        st.session_state['current_page'] = 'Home'
        st.rerun()
    md("<h2 style='text-align: center;'>Join Service Connect! 🚀</h2>")
    # Role selection with better UX
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👤 Register as User", key="reg_user", use_container_width=True,
                     type="primary" if st.session_state['selected_role_reg'] == 'user' else "secondary"):
            st.session_state['selected_role_reg'] = 'user'
            st.rerun()
    with col2:
        if st.button("🔧 Register as Technician", key="reg_tech", use_container_width=True,
                     type="primary" if st.session_state['selected_role_reg'] == 'technical' else "secondary"):
            st.session_state['selected_role_reg'] = 'technical'
            st.rerun()
    role = st.session_state['selected_role_reg']
    st.info(f"📝 Registering as: **{role.capitalize()}** - {'Book services' if role == 'user' else 'Provide services'}")
    with st.form("register_form"):
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone Number (Optional)")
        password = st.text_input("Password", type="password", help="Minimum 6 characters")
        confirm = st.text_input("Confirm Password", type="password")
        if role == 'technical':
            bio = st.text_area("Professional Bio (Optional)", placeholder="Brief description of your skills and experience...")
        if st.form_submit_button("Create Account", use_container_width=True):
            if not name or not email or not password:
                show_notification("All fields are required", 'error')
            elif not validate_email(email):
                show_notification("Invalid email format", 'error')
            elif password != confirm:
                show_notification("Passwords don't match", 'error')
            elif len(password) < 6:
                show_notification("Password must be at least 6 characters", 'error')
            elif phone and not validate_phone(phone):
                show_notification("Invalid phone number format", 'error')
            else:
                bio_text = bio if role == 'technical' else None
                success, msg = db.register_user(email, password, name, role, phone, bio_text)
                if success:
                    show_notification("✅ Registration successful! Please login.", 'success')
                    time.sleep(1)
                    st.session_state['current_page'] = "Login"
                    st.rerun()
                else:
                    show_notification(msg, 'error')

def services_page():
    if not st.session_state['current_user'] or st.session_state['current_user']['role'] != 'user':
        show_notification("Access Denied", 'error')
        time.sleep(1)
        st.session_state['current_page'] = 'Home'
        st.rerun()
        return
    if st.session_state['selected_service']:
        show_service_details()
        return
    st.title("🛒 Available Services")
    # Search and filter
    col1, col2 = st.columns([1, 2])
    with col1:
        categories = ["All"] + sorted(list(set([s['category'] for s in db.get_services()])))
        selected_cat = st.selectbox("Filter by Category", categories)
    with col2:
        search = st.text_input("🔍 Search services...")
    services = db.get_services(selected_cat if selected_cat != "All" else None)
    # Filter by search
    if search:
        services = [s for s in services if search.lower() in s['name'].lower() or
                    search.lower() in s['description'].lower()]
    if not services:
        st.info("No services found matching your criteria.")
        return
    # Display services in grid
    cols = st.columns(3)
    for i, service in enumerate(services):
        with cols[i % 3]:
            md(f"""
            <div class="service-card animate-enter" style="animation-delay: {i*0.05}s">
            <div class="card-icon">{service['icon']}</div>
            <h3 class="card-title">{service['name']}</h3>
            <div class="card-category">{service['category']}</div>
            <p class="card-desc">{service['description']}</p>
            <div class="card-rating">⭐ {service['rating']}</div>
            <p class="card-price">${service['price']}</p>
            </div>
            """)
            if st.button("✨ Select Service", key=f"select_{service['id']}", use_container_width=True):
                st.session_state['selected_service'] = service
                st.rerun()

def show_service_details():
    service = st.session_state['selected_service']
    if st.button("← Back to Services"):
        st.session_state['selected_service'] = None
        st.rerun()
    md(f"""
    <div style="background: rgba(30, 35, 60, 0.95); padding: 40px; border-radius: 20px;
    border: 1px solid #6c5ce7; margin: 20px 0; box-shadow: 0 10px 40px rgba(0,0,0,0.5);
    position: relative; overflow: hidden;">
    <div style="position: absolute; top: -50px; right: -50px; font-size: 8rem; opacity: 0.1;">{service['icon']}</div>
    <div style="font-size: 4rem; text-align: center;">{service['icon']}</div>
    <h1 style="text-align: center; color: #a29bfe;">{service['name']}</h1>
    <div style="text-align: center; margin: 20px 0;">
        <span class="card-category">{service['category']}</span>
        <span style="margin-left: 10px; color: #f1c40f;">⭐ {service['rating']}</span>
    </div>
    <p style="text-align: center; font-size: 1.1rem; color: #e0e0e0; max-width: 800px; margin: 0 auto;">{service['description']}</p>
    <h2 style="text-align: center; margin-top: 30px; color: #a29bfe;">Price: ${service['price']}</h2>
    </div>
    """)
    st.subheader("📅 Complete Your Booking")
    with st.form("booking_form"):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Service Date", min_value=datetime.today())
        with col2:
            payment = st.selectbox("Payment Method", ["Credit Card", "Cash", "Digital Wallet", "Bank Transfer"])
        notes = st.text_area("Special Instructions (Optional)", placeholder="Any specific requirements or details...")
        if st.form_submit_button("Confirm Booking", use_container_width=True):
            success, order_id = db.create_order(
                st.session_state['current_user']['id'],
                service['id'],
                date.strftime('%Y-%m-%d'),
                payment,
                notes,
                service['price']
            )
            if success:
                show_notification("🎉 Booking Confirmed! You will receive a confirmation email.", 'success')
                time.sleep(1)
                st.session_state['selected_service'] = None
                st.session_state['current_page'] = "My Orders"
                st.rerun()
            else:
                show_notification("Booking failed. Please try again.", 'error')

def my_orders_page():
    if not st.session_state['current_user']:
        show_notification("Please login first", 'error')
        st.session_state['current_page'] = 'Home'
        st.rerun()
        return
    user = st.session_state['current_user']
    st.title("📋 My Orders")
    orders = db.get_user_orders(user['id'])
    if not orders:
        st.info("No orders yet. Browse services to make your first booking!")
        return
    for order in orders:
        status_color = "#2ecc71" if order['status'] == 'Done' else ("#f1c40f" if order['status'] == 'Pending' else "#3498db")
        status_icon = "✅" if order['status'] == 'Done' else ("⏳" if order['status'] == 'Pending' else "❌")
        # Get unread message count for this order
        unread_count = 0
        try:
            messages = db.get_chat_messages(order['id'])
            unread_count = sum(1 for msg in messages if not msg['is_read'] and msg['sender_id'] != user['id'])
        except:
            pass
        md(f"""
        <div style="background: rgba(30, 35, 60, 0.95); border-left: 5px solid {status_color};
        padding: 20px; margin: 15px 0; border-radius: 10px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1);
        transition: all 0.3s ease; position: relative;">
        <div style="display: flex; align-items: center; gap: 10px;">
        <div style="font-size: 1.5rem;">{order['icon']}</div>
        <div style="flex-grow: 1;">
        <h3 style="margin: 0;">{order['service_name']}</h3>
        <p style="margin: 5px 0; color: rgba(255,255,255,0.7); font-size: 0.9rem;">
        Order ID: {order['id'][:8]}...
        </p>
        </div>
        <span style="color: {status_color}; font-weight: bold;">{status_icon} {order['status']}</span>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px;">
        <div>
        <p><strong>📅 Service Date:</strong> {order['booking_date']}</p>
        <p><strong>💰 Price:</strong> ${order['price']}</p>
        </div>
        <div>
        <p><strong>💳 Payment Method:</strong> {order['payment_method']}</p>
        <p><strong>📝 Order Date:</strong> {order['created_at'][:10] if order['created_at'] else 'N/A'}</p>
        </div>
        </div>
        {f"<p><strong>📝 Special Instructions:</strong> {order['notes']}</p>" if order['notes'] else ""}
        </div>
        """)
        # Action buttons
        col1, col2 = st.columns([3, 1])
        with col2:
            chat_button_text = "💬 Chat with Technician"
            if unread_count > 0:
                chat_button_text = f"💬 Chat ({unread_count})"
            if st.button(chat_button_text, key=f"chat_{order['id']}", use_container_width=True):
                st.session_state['current_chat_order'] = order['id']
                st.session_state['current_page'] = 'My Chats'
                st.rerun()

def pending_orders_page():
    if not st.session_state['current_user'] or st.session_state['current_user']['role'] != 'technical':
        show_notification("Access Denied", 'error')
        st.session_state['current_page'] = 'Home'
        st.rerun()
        return
    user = st.session_state['current_user']
    st.title("🛠️ Pending Service Requests")
    orders = db.get_pending_orders(user['id'])
    if not orders:
        st.success("🎉 No pending orders!")
        return
    for order in orders:
        unread_count = order.get('unread_count', 0)
        md(f"""
        <div style="background: rgba(30, 35, 60, 0.95); padding: 20px; margin: 15px 0;
        border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        border: 1px solid rgba(255,255,255,0.1); border-left: 5px solid #f1c40f;
        position: relative;">
        {f"<span class='order-chat-badge'>{unread_count}</span>" if unread_count > 0 else ""}
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
        <div>
        <h3 style="margin: 0;">{order['service_name']}</h3>
        <p style="color: #e0e0e0; margin: 5px 0;">Order ID: {order['id'][:8]}...</p>
        </div>
        <span style="background: #f1c40f20; color: #f1c40f; padding: 5px 12px; border-radius: 12px; font-weight: bold;">⏳ Pending</span>
        </div>
        <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; margin: 15px 0;">
        <h4 style="margin: 0 0 10px 0;">👤 Client Details</h4>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
        <p style="margin: 5px 0;"><strong>Name:</strong> {order['user_name']}</p>
        <p style="margin: 5px 0;"><strong>📧 Email:</strong> {order['user_email']}</p>
        {f"<p style='margin: 5px 0;'><strong>📞 Phone:</strong> {order['user_phone']}</p>" if order['user_phone'] else ""}
        </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
        <div>
        <p><strong>📅 Service Date:</strong> {order['booking_date']}</p>
        <p><strong>💰 Price:</strong> ${order['price']}</p>
        </div>
        <div>
        <p><strong>💳 Payment Method:</strong> {order['payment_method']}</p>
        <p><strong>📝 Order Date:</strong> {order['created_at'][:10] if order['created_at'] else 'N/A'}</p>
        </div>
        </div>
        {f"<div style='margin-top: 15px;'><p><strong>📝 Special Instructions:</strong></p><p style='background: rgba(255,255,255,0.05); padding: 10px; border-radius: 5px;'>{order['notes']}</p></div>" if order['notes'] else ""}
        </div>
        """)
        # Action buttons
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            chat_button_text = "💬 Chat with Client"
            if unread_count > 0:
                chat_button_text = f"💬 Chat ({unread_count})"
            if st.button(chat_button_text, key=f"chat_{order['id']}", use_container_width=True):
                st.session_state['current_chat_order'] = order['id']
                st.session_state['current_page'] = 'My Chats'
                st.rerun()
        with col3:
            if st.button(f"✅ Complete", key=f"complete_{order['id']}", use_container_width=True):
                if db.update_order_status(order['id'], 'Done'):
                    show_notification("✅ Order completed successfully!", 'success')
                    time.sleep(1)
                    st.rerun()

def profile_page():
    user = st.session_state['current_user']
    st.title("👤 Your Profile")
    # Get profile data
    profile = db.get_user_profile(user['id'])
    if not profile:
        show_notification("Error loading profile", 'error')
        return
    # Display profile info
    col1, col2 = st.columns([1, 2])
    with col1:
        md(f"""
        <div class="profile-card">
            <div class="profile-avatar">
                {user['name'][0].upper() if user['name'] else 'U'}
            </div>
            <h2>{user['name']}</h2>
            <p style="color: #a29bfe;">{user['role'].capitalize()}</p>
            <p style="color: #e0e0e0; margin-top: 20px;">Member since: {profile['join_date'][:10] if profile['join_date'] else 'N/A'}</p>
        </div>
        """)
    with col2:
        md("""
        <div style="background: rgba(30, 35, 60, 0.95); padding: 30px; border-radius: 15px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.1);">
        """)
        st.subheader("Profile Information")
        with st.form("profile_form"):
            name = st.text_input("Full Name", value=profile['name'])
            email = st.text_input("Email", value=profile['email'], disabled=True)
            phone = st.text_input("Phone Number", value=profile['phone'] or "")
            bio = st.text_area("Bio", value=profile['bio'] or "",
                              placeholder="Tell us about yourself...")
            if st.form_submit_button("Update Profile", use_container_width=True):
                if db.update_user_profile(user['id'], name, phone, bio):
                    show_notification("✅ Profile updated successfully!", 'success')
                    # Update session
                    st.session_state['current_user']['name'] = name
                    time.sleep(1)
                    st.rerun()
                else:
                    show_notification("Failed to update profile", 'error')
        md("</div>")
    # Additional info
    md("<br>")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📧 Email", profile['email'])
    with col2:
        st.metric("👤 Role", profile['role'].capitalize())
    with col3:
        last_login = profile['last_login'][:19] if profile['last_login'] else 'Never'
        st.metric("🕒 Last Login", last_login)
    md("<br>")
    if st.button("🚪 Logout", use_container_width=True, type="primary"):
        logout()

def admin_dashboard():
    if not st.session_state['current_user'] or st.session_state['current_user']['role'] != 'admin':
        show_notification("Access Denied", 'error')
        st.session_state['current_page'] = 'Home'
        st.rerun()
        return
    st.title("📊 Admin Dashboard")
    stats = db.get_dashboard_stats()
    # Main stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        md(f"""
        <div class="stats-card">
            <h3>{stats.get('total_users', 0)}</h3>
            <p>👥 Total Users</p>
        </div>
        """)
    with col2:
        md(f"""
        <div class="stats-card">
            <h3>{stats.get('total_techs', 0)}</h3>
            <p>🔧 Technicians</p>
        </div>
        """)
    with col3:
        md(f"""
        <div class="stats-card">
            <h3>{stats.get('total_orders', 0)}</h3>
            <p>📦 Total Orders</p>
        </div>
        """)
    with col4:
        md(f"""
        <div class="stats-card">
            <h3>${stats.get('revenue', 0):,.0f}</h3>
            <p>💰 Revenue</p>
        </div>
        """)
    # Secondary stats
    md("<br>")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("⏳ Pending Orders", stats.get('pending_orders', 0))
    with col2:
        st.metric("✅ Completed Orders", stats.get('completed_orders', 0))
    with col3:
        st.metric("🛠️ Total Services", stats.get('total_services', 0))
    # Recent orders
    md("---")
    st.subheader("📋 Recent Orders")
    orders = db.get_all_orders()[:10]  # Get last 10 orders
    if orders:
        df = pd.DataFrame(orders)
        df = df[['id', 'service_name', 'user_name', 'status', 'booking_date', 'price']]
        df.columns = ['Order ID', 'Service', 'Customer', 'Status', 'Date', 'Price']
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No orders yet")

def all_orders_page():
    if not st.session_state['current_user'] or st.session_state['current_user']['role'] != 'admin':
        show_notification("Access Denied", 'error')
        st.session_state['current_page'] = 'Home'
        st.rerun()
        return
    st.title("📋 All Orders")
    orders = db.get_all_orders()
    if orders:
        df = pd.DataFrame(orders)
        # Add filters
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox("Filter by Status", ["All", "Pending", "Done"])
        with col2:
            date_filter = st.date_input("Filter by Date")
        with col3:
            service_filter = st.selectbox("Filter by Service", ["All"] + sorted(list(set(df['service_name'].tolist()))))
        # Apply filters
        if status_filter != "All":
            df = df[df['status'] == status_filter]
        if service_filter != "All":
            df = df[df['service_name'] == service_filter]
        if date_filter:
            df = df[df['booking_date'] == date_filter.strftime('%Y-%m-%d')]
        # Display
        st.dataframe(df[['id', 'service_name', 'user_name', 'status', 'booking_date', 'price', 'created_at']],
                     use_container_width=True)
        # Export option
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export as CSV",
            data=csv,
            file_name="orders_export.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("No orders yet")

def analytics_page():
    if not st.session_state['current_user'] or st.session_state['current_user']['role'] != 'admin':
        show_notification("Access Denied", 'error')
        st.session_state['current_page'] = 'Home'
        st.rerun()
        return
    st.title("📈 Analytics Dashboard")
    stats = db.get_dashboard_stats()
    # Charts
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Revenue Overview")
        revenue_data = pd.DataFrame({
            'Category': ['Completed', 'Pending', 'Total'],
            'Amount': [stats.get('revenue', 0),
                       stats.get('pending_orders', 0) * 50,
                       stats.get('revenue', 0) + (stats.get('pending_orders', 0) * 50)]
        })
        st.bar_chart(revenue_data.set_index('Category'))
    with col2:
        st.subheader("Orders Distribution")
        orders_data = pd.DataFrame({
            'Status': ['Completed', 'Pending'],
            'Count': [stats.get('completed_orders', 0), stats.get('pending_orders', 0)]
        })
        st.line_chart(orders_data.set_index('Status'))
    # Detailed stats
    st.subheader("Detailed Statistics")
    metrics_cols = st.columns(4)
    metrics = [
        ("📊 Total Orders", stats.get('total_orders', 0)),
        ("💰 Total Revenue", f"${stats.get('revenue', 0):,.2f}"),
        ("📈 Avg Order Value", f"${stats.get('revenue', 0)/max(1, stats.get('completed_orders', 1)):.2f}"),
        ("🏆 Completion Rate", f"{(stats.get('completed_orders', 0)/max(1, stats.get('total_orders', 1))*100):.1f}%")
    ]
    for col, (label, value) in zip(metrics_cols, metrics):
        col.metric(label, value)

def about_page():
    # Hero Section
    md("""
    <div style="text-align: center; padding: 60px 20px; background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
         border-radius: 20px; margin-bottom: 40px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1);">
        <h1 style="font-size: 3.5rem; background: linear-gradient(to right, #fff, #a29bfe); -webkit-background-clip: text;
                   -webkit-text-fill-color: transparent; margin-bottom: 15px;">Building Connections</h1>
        <p style="font-size: 1.2rem; color: #dcdde1; max-width: 700px; margin: 0 auto;">
            Empowering communities by bridging the gap between skilled professionals and those in need.
            Trust, Quality, and Reliability - delivered.
        </p>
    </div>
    """)

    # Quick Stats Bar
    cols = st.columns(4)
    stats = [
        ("🚀", "Founded", "2023"),
        ("👥", "Active Users", "10k+"),
        ("⭐", "5-Star Reviews", "5000+"),
        ("🏙️", "Cities Served", "15+")
    ]
    for col, (icon, label, value) in zip(cols, stats):
        with col:
            md(f"""
            <div style="background: rgba(255,255,255,0.03); padding: 15px; border-radius: 12px; text-align: center;
                 border: 1px solid rgba(255,255,255,0.05); transition: transform 0.3s; cursor: default;"
                 onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1.0)'">
                <div style="font-size: 1.5rem; margin-bottom: 5px;">{icon}</div>
                <div style="font-size: 1.2rem; font-weight: bold; color: #a29bfe;">{value}</div>
                <div style="font-size: 0.9rem; color: #aaa;">{label}</div>
            </div>
            """)

    md("<br>")

    # Mission and Story Cards
    col1, col2 = st.columns(2)
    with col1:
        md("""
        <div style="height: 100%; padding: 30px; background: rgba(30, 35, 60, 0.6); border-radius: 15px;
             border-left: 5px solid #6c5ce7; box-shadow: 0 5px 20px rgba(0,0,0,0.2);">
            <h2 style="color: #fff; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; margin-bottom: 20px;">
                🎯 Our Mission
            </h2>
            <p style="color: #dcdde1; line-height: 1.6;">
                Service Connect was founded with a simple yet powerful mission: to revolutionize how local services are discovered and delivered.
                We believe everyone deserves access to high-quality help, and every skilled professional deserves a platform to shine.
            </p>
            <div style="margin-top: 20px; display: flex; gap: 10px;">
                <span style="background: rgba(108, 92, 231, 0.2); color: #a29bfe; padding: 5px 12px; border-radius: 15px; font-size: 0.8rem;">Innovation</span>
                <span style="background: rgba(108, 92, 231, 0.2); color: #a29bfe; padding: 5px 12px; border-radius: 15px; font-size: 0.8rem;">Trust</span>
                <span style="background: rgba(108, 92, 231, 0.2); color: #a29bfe; padding: 5px 12px; border-radius: 15px; font-size: 0.8rem;">Community</span>
            </div>
        </div>
        """)
    with col2:
        md("""
        <div style="height: 100%; padding: 30px; background: rgba(30, 35, 60, 0.6); border-radius: 15px;
             border-left: 5px solid #e17055; box-shadow: 0 5px 20px rgba(0,0,0,0.2);">
            <h2 style="color: #fff; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; margin-bottom: 20px;">
                💡 Why Choose Us?
            </h2>
            <ul style="list-style: none; padding: 0; margin: 0; color: #dcdde1;">
                <li style="margin-bottom: 12px; display: flex; align-items: center;">
                    <span style="color: #e17055; margin-right: 10px;">✓</span> Verified Professionals
                </li>
                <li style="margin-bottom: 12px; display: flex; align-items: center;">
                    <span style="color: #e17055; margin-right: 10px;">✓</span> Secure & Transparent Payments
                </li>
                <li style="margin-bottom: 12px; display: flex; align-items: center;">
                    <span style="color: #e17055; margin-right: 10px;">✓</span> 24/7 Dedicated Support
                </li>
                <li style="display: flex; align-items: center;">
                    <span style="color: #e17055; margin-right: 10px;">✓</span> Seamless Booking Experience
                </li>
            </ul>
        </div>
        """)

    md("<br>")

    # Team Section
    st.subheader("👥 Meet the Leadership")
    md("<p style='color: #aaa; margin-bottom: 30px;'>The passionate team driving our vision forward.</p>")
    
    team = [
        ("👨‍💼", "John Doe", "CEO & Founder", "Visionary leader with 15y exp."),
        ("👩‍💻", "Jane Smith", "CTO", "Tech architect & AI enthusiast."),
        ("👨‍🔧", "Mike Johnson", "Head of Ops", "Ensuring smooth service delivery."),
        ("👩‍💼", "Sarah Lee", "Customer Success", "Champion of user happiness.")
    ]
    
    team_cols = st.columns(4)
    for col, (icon, name, role, bio) in zip(team_cols, team):
        with col:
            md(f"""
            <div style="background: linear-gradient(145deg, #1e233c, #252947); padding: 30px 20px; border-radius: 18px;
                 text-align: center; border: 1px solid rgba(255,255,255,0.05); height: 280px; position: relative; overflow: hidden;
                 transition: transform 0.3s ease, box-shadow 0.3s ease;"
                 onmouseover="this.style.transform='translateY(-10px)'; this.style.boxShadow='0 15px 30px rgba(0,0,0,0.4)';"
                 onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='none';">
                <div style="position: absolute; top: 0; left: 0; width: 100%; height: 5px; background: linear-gradient(90deg, #6c5ce7, #a29bfe);"></div>
                <div style="font-size: 3.5rem; margin-bottom: 15px; filter: drop-shadow(0 5px 10px rgba(0,0,0,0.3));">{icon}</div>
                <h3 style="margin: 0; font-size: 1.2rem; color: #fff;">{name}</h3>
                <p style="color: #6c5ce7; font-weight: 500; font-size: 0.9rem; margin: 5px 0 15px 0;">{role}</p>
                <p style="font-size: 0.85rem; color: #b2bec3; line-height: 1.5;">{bio}</p>
            </div>
            """)

def contact_page():
    st.title("📞 Contact Us")
    md("""
    <div style="background: rgba(30, 35, 60, 0.95); padding: 40px; border-radius: 20px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.1);">
    """)
    col1, col2 = st.columns(2)
    with col1:
        md("""
        ## Get in Touch
        We're here to help! Whether you have questions about our services,
        need technical support, or want to provide feedback, we'd love to hear from you.
        ### Contact Information
        - **📧 Email**: support@serviceconnect.com
        - **📞 Phone**: +1-234-567-8900
        - **📍 Address**: 123 Service St, Tech City
        - **🕒 Hours**: 9:00 AM - 6:00 PM (Mon-Fri)
        ### Quick Links
        - [FAQ](https://example.com/faq)
        - [Help Center](https://example.com/help)
        - [Terms of Service](https://example.com/terms)
        - [Privacy Policy](https://example.com/privacy)
        """)
    with col2:
        md("## 📝 Contact Form")
        with st.form("contact_form"):
            name = st.text_input("Your Name")
            email = st.text_input("Your Email")
            subject = st.selectbox("Subject", [
                "General Inquiry",
                "Technical Support",
                "Service Feedback",
                "Partnership",
                "Other"
            ])
            message = st.text_area("Your Message", height=150)
            if st.form_submit_button("Send Message", use_container_width=True):
                if not name or not email or not message:
                    show_notification("Please fill all required fields", 'error')
                elif not validate_email(email):
                    show_notification("Invalid email format", 'error')
                else:
                    if db.save_contact_message(name, email, subject, message):
                        show_notification("✅ Message sent successfully! We'll get back to you soon.", 'success')
                    else:
                        show_notification("Failed to send message. Please try again.", 'error')
    md("</div>")
    # Map and location
    md("<br>")
    st.subheader("📍 Our Location")
    # Simple map placeholder
    md("""
    <div style="background: rgba(30, 35, 60, 0.8); padding: 30px; border-radius: 15px;
    text-align: center; border: 1px solid rgba(255,255,255,0.1);">
        <h3>🗺️ Service Connect Headquarters</h3>
        <p>123 Service Street, Tech City, TC 12345</p>
        <p style="color: #a29bfe;">📍 Click the map below for directions</p>
        <div style="background: rgba(0,0,0,0.3); height: 200px; border-radius: 10px;
        display: flex; align-items: center; justify-content: center; margin-top: 20px;">
            <span style="font-size: 3rem;">🗺️</span>
        </div>
    </div>
    """)

# ==================== CHATBOT SIDEBAR ====================
def show_chatbot():
    with st.sidebar:
        md("""
        <div class="chatbot-container">
        <div class="chatbot-header">
        <h2>🤖 AI Assistant</h2>
        <p>Ask me anything about our services!</p>
        </div>
        """)
        # Chat messages area
        # Chat messages area

        if len(st.session_state['chat_history']) == 0:
            md("""
            **👋 Hi! I'm your AI assistant**
            I can help you with:
            - Service information & pricing
            - How to book services
            - Account assistance
            - Order status
            - Contact information
            Try asking me:
            - "What services do you offer?"
            - "How do I book a service?"
            - "Show me cleaning services"
            - "Contact support"
            - "Chat with technician"
            """)
        else:
            for msg in st.session_state['chat_history']:
                with st.chat_message(msg["role"]):
                    md(msg["content"])

        # Clear button
        if len(st.session_state['chat_history']) > 0:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state['chat_history'] = []
                st.rerun()

        # Input
        prompt = st.chat_input("Type your question...")
        if prompt:
            st.session_state['chat_history'].append({"role": "user", "content": prompt})
            user_role = st.session_state['current_user']['role'] if st.session_state['current_user'] else 'guest'
            st.session_state['chatbot'].update_context(user_role, st.session_state['current_page'])
            response = st.session_state['chatbot'].get_response(prompt)
            st.session_state['chat_history'].append({"role": "assistant", "content": response})
            st.rerun()


# ==================== MAIN APP ====================
def main():
    # Show navigation if logged in
    if st.session_state['current_user']:
        show_navigation()
    else:
        # Simple navigation for guests
        html_guest_nav = '<div class="nav-container">'
        cols = st.columns(5)
        menu_items = ["Home", "Login", "Register", "About", "Contact Us"]
        for i, item in enumerate(menu_items):
            with cols[i]:
                if st.button(item, key=f"guest_nav_{item}", use_container_width=True):
                    st.session_state['current_page'] = item
                    st.rerun()
        html_guest_nav += '</div>'
        md(html_guest_nav)
    # Route to correct page
    page = st.session_state['current_page']
    if page == 'Home':
        home_page()
    elif page == 'Login':
        login_page()
    elif page == 'Register':
        register_page()
    elif page == 'Services':
        services_page()
    elif page == 'My Orders':
        my_orders_page()
    elif page == 'My Chats':
        chat_page()
    elif page == 'Pending Orders':
        pending_orders_page()
    elif page == 'Profile':
        profile_page()
    elif page == 'Dashboard':
        admin_dashboard()
    elif page == 'All Orders':
        all_orders_page()
    elif page == 'Analytics':
        analytics_page()
    elif page == 'About':
        about_page()
    elif page == 'Contact Us':
        contact_page()
    # Show chatbot in sidebar
    show_chatbot()
    # Check for new chat messages and show notifications
    if st.session_state['current_user']:
        user = st.session_state['current_user']
        unread_count = db.get_unread_message_count(user['id'], user['role'])
        if unread_count > 0 and st.session_state['current_page'] != 'My Chats':
            # Notification container
            md(f"""
            <div class="chat-notification">
                💬 You have {unread_count} new message{'' if unread_count == 1 else 's'}
            </div>
            """)
            # Action buttons for the notification
            col_notif_1, col_notif_2 = st.columns([1, 1])
            with col_notif_1:
                 if st.button("Go to Chats", key="go_to_chats", use_container_width=True):
                    st.session_state['current_page'] = 'My Chats'
                    st.rerun()
            with col_notif_2:
                if st.button("Dismiss", key="dismiss_notification", use_container_width=True):
                    pass
    # Footer
    md("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        md("""
        <div style="text-align: center; color: #a29bfe; font-size: 0.9rem;">
            <p>© 2024 Service Connect. All rights reserved.</p>
            <p>Connecting professionals with clients since 2023</p>
        </div>
        """)

if __name__ == "__main__":
    main()
