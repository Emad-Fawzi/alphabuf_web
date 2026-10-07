"""
قراءة مفاتيح الـ API من environment variables - بديل st.secrets بتاع Streamlit، لأن السيرفر
هنا مش تطبيق Streamlit، فبيعتمد على متغيرات البيئة العادية (.env أو إعدادات الاستضافة).
نفس أسامي المفاتيح المستخدمة في نسخة Streamlit، عشان لو نقلت مفاتيحك مش محتاج تغيّر حاجة.
"""
import os


def get_secret(key):
    return os.environ.get(key)
