import streamlit as st
import random
import string
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import sqlite3
import streamlit.components.v1 as components
import hashlib

# --- Veritabanı Bağlantısı ---
conn = sqlite3.connect("guvenbank.db", detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
cursor = conn.cursor()

# Kullanıcılar tablosu
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    fullname TEXT,
    email TEXT UNIQUE,
    phone TEXT,
    account_number TEXT UNIQUE,
    balance REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# OTP tablosu
cursor.execute("""
CREATE TABLE IF NOT EXISTS otps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    otp TEXT,
    expiration TIMESTAMP
)
""")

# Giriş kayıtları tablosu
cursor.execute("""
CREATE TABLE IF NOT EXISTS giris_kayitlari (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    login_time TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
)
""")

conn.commit()

# --- Şifre hashleme fonksiyonu ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Hesap numarası oluşturma fonksiyonu ---
def generate_account_number():
    return ''.join(random.choices(string.digits, k=16))

# --- Şifre oluşturma fonksiyonu ---
def generate_password(length):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))

# --- E-posta gönderme fonksiyonu ---
def send_email(to_email, password, expiration_time):
    your_email = "guvennbankk@gmail.com"
    your_app_password = "vtcwztskgrbupsux"

    subject = "Tek Kullanımlık Şifreniz"
    body = f"""
Merhaba,

İstediğiniz tek kullanımlık şifreniz aşağıdadır:

Şifre: {password}
Geçerlilik süresi: {expiration_time.strftime('%H:%M:%S')}

Lütfen bu şifreyi kimseyle paylaşmayın. Şifre 10 dakika sonra geçersiz olacaktır.

GüvenBank
"""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = your_email
    msg["To"] = to_email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(your_email, your_app_password)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"E-posta gönderimi başarısız: {e}")
        return False

# --- Arayüz Stili ---
st.markdown("""
    <style>
    body {
        background-color: black;
    }
    .main {
        background-color: black;
    }
    .bank-container {
        padding: 30px;
        border-radius: 15px;
        box-shadow: none;
        max-width: 600px;
        margin: auto;
        margin-top: 40px;
        font-family: 'Segoe UI', sans-serif;
        color: black;
        background-color: transparent;
    }
    .bank-title {
        font-size: 32px;
        font-weight: bold;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    .stButton>button {
        background-color: #003366;
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 16px;
    }
    </style>
""", unsafe_allow_html=True)

# --- Başlık ---
st.markdown('<div class="bank-container">', unsafe_allow_html=True)
st.markdown('<div class="bank-title">GüvenBank Giriş Paneli</div>', unsafe_allow_html=True)

# Oturum Değişkenleri
if "otp" not in st.session_state:
    st.session_state.otp = None
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "show_otp_option" not in st.session_state:
    st.session_state.show_otp_option = False
if "otp_sent" not in st.session_state:
    st.session_state.otp_sent = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# --- Kullanıcı Kayıt Formu ---
st.subheader("Yeni Hesap Oluştur")
with st.form("register_form"):
    reg_username = st.text_input("Kullanıcı Adı")
    reg_password = st.text_input("Şifre", type="password")
    reg_fullname = st.text_input("Ad Soyad")
    reg_email = st.text_input("E-posta")
    reg_phone = st.text_input("Telefon")
    
    if st.form_submit_button("Kayıt Ol"):
        if reg_username and reg_password and reg_fullname and reg_email:
            try:
                hashed_password = hash_password(reg_password)
                account_number = generate_account_number()
                
                cursor.execute("""
                    INSERT INTO users (username, password, fullname, email, phone, account_number)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (reg_username, hashed_password, reg_fullname, reg_email, reg_phone, account_number))
                conn.commit()
                
                st.success("Hesabınız başarıyla oluşturuldu!")
            except sqlite3.IntegrityError:
                st.error("Bu kullanıcı adı veya e-posta zaten kullanımda!")
        else:
            st.warning("Lütfen tüm alanları doldurun!")

# --- Kullanıcı Girişi ---
st.subheader("Giriş Yap")
with st.form("login_form"):
    username = st.text_input("Kullanıcı Adı")
    password = st.text_input("Şifre", type="password")
    
    if st.form_submit_button("Giriş Yap"):
        if username and password:
            hashed_password = hash_password(password)
            cursor.execute("SELECT id, fullname FROM users WHERE username = ? AND password = ?",
                         (username, hashed_password))
            user = cursor.fetchone()
            
            if user:
                user_id, fullname = user
                st.session_state.user_id = user_id
                st.session_state.authenticated = True
                
                # Giriş kaydı oluştur
                cursor.execute("INSERT INTO giris_kayitlari (user_id, name, login_time) VALUES (?, ?, ?)",
                             (user_id, fullname, datetime.now()))
                conn.commit()
                
                st.success(f"Hoş geldiniz, {fullname}!")
                
                # Kullanıcı paneline yönlendir
                st.markdown(f"""
                    <h2 style='text-align:center; color:green;'>✔ Giriş Yaptınız!</h2>
                    <p style='text-align:center;'>
                        <a href='user_dashboard.html?user_id={user_id}' target='_blank' style='
                            font-size:18px;
                            color:#003366;
                            text-decoration:none;
                            font-weight:bold;
                        '>👉 Kullanıcı Paneline Git</a>
                    </p>
                """, unsafe_allow_html=True)
            else:
                st.error("Geçersiz kullanıcı adı veya şifre!")
        else:
            st.warning("Lütfen tüm alanları doldurun!")

# --- Tek Kullanımlık Şifre Seçeneği ---
st.subheader("Tek Kullanımlık Şifre")
if st.button("Şifre Al (Tek Kullanımlık)"):
    st.session_state.show_otp_option = True

# --- Şifre Al Formu ---
if st.session_state.show_otp_option and not st.session_state.otp_sent:
    name2 = st.text_input("Ad Soyad (Tek Kullanımlık Şifre için)")
    email = st.text_input("E-posta Adresiniz")
    length = st.slider("Şifre uzunluğu:", 6, 20, 10)

    if st.button("Gönder"):
        if name2 and email:
            otp = generate_password(length)
            expiration = datetime.now() + timedelta(minutes=10)
            st.session_state.otp = otp
            st.session_state.otp_expiration = expiration
            st.session_state.otp_sent = True

            cursor.execute("INSERT INTO otps (name, email, otp, expiration) VALUES (?, ?, ?, ?)",
                           (name2, email, otp, expiration))
            conn.commit()

            if send_email(email, otp, expiration):
                st.success(f"Şifre başarıyla {email} adresine gönderildi!")
            else:
                st.error("Şifre gönderilemedi.")
        else:
            st.warning("Lütfen tüm alanları doldurun.")

# --- Tek Kullanımlık Şifre ile Giriş ---
if st.session_state.otp_sent:
    otp_input = st.text_input("E-posta ile Gelen Şifreyi Girin")
    if st.button("Şifreyle Giriş Yap"):
        cursor.execute("SELECT id, name, expiration FROM otps WHERE otp = ?", (otp_input,))
        result = cursor.fetchone()

        if result:
            otp_id, user_name, expiration_db = result
            if isinstance(expiration_db, str):
                expiration_db = datetime.strptime(expiration_db, '%Y-%m-%d %H:%M:%S.%f')
            if datetime.now() < expiration_db:
                cursor.execute("DELETE FROM otps WHERE id = ?", (otp_id,))
                conn.commit()

                cursor.execute("INSERT INTO giris_kayitlari (name, login_time) VALUES (?, ?)", (user_name, datetime.now()))
                conn.commit()

                st.success("Giriş Başarılı!")
                st.session_state.authenticated = True
                st.session_state.otp_sent = False

                js_code = f"""
                <script>
                    localStorage.setItem('fullname', '{user_name}');
                </script>
                """
                st.components.v1.html(js_code)

            else:
                st.error("Şifrenizin süresi dolmuş!")
        else:
            st.error("Geçersiz şifre!")

# --- Başarılı Giriş Sonrası ---
if st.session_state.authenticated:
    st.markdown("""
        <h2 style='text-align:center; color:green;'>✔ Giriş Yaptınız!</h2>
        <p style='text-align:center;'>
            <a href='https://beyza-cmd.github.io/guvenbank-app.py/' target='_blank' style='
                font-size:18px;
                color:#003366;
                text-decoration:none;
                font-weight:bold;
            '>👉 GüvenBank Uygulamasına Git</a>
        </p>
    """, unsafe_allow_html=True)
