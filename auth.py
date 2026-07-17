import streamlit as st
import hashlib
import json
from datetime import datetime
import os

# ========================
# Configuration d'authentification
# ========================

# Base de données d'utilisateurs (à remplacer par une vraie base de données)
# Format: {username: {password_hash, role, email}}
USERS_DB = {
    "supervisor": {
        "password_hash": hashlib.sha256("supervisor123".encode()).hexdigest(),
        "role": "Superviseur GIRE",
        "email": "supervisor@sanaga.cm"
    },
    "engineer": {
        "password_hash": hashlib.sha256("engineer123".encode()).hexdigest(),
        "role": "Ingénieur Barrage (NHPC/EDC)",
        "email": "engineer@sanaga.cm"
    },
    "chemist": {
        "password_hash": hashlib.sha256("chemist123".encode()).hexdigest(),
        "role": "Hydrochimiste / Labo",
        "email": "chemist@sanaga.cm"
    },
    "field_agent": {
        "password_hash": hashlib.sha256("agent123".encode()).hexdigest(),
        "role": "Agent de Terrain",
        "email": "field@sanaga.cm"
    },
    "minister": {
        "password_hash": hashlib.sha256("minister123".encode()).hexdigest(),
        "role": "Décideur / Ministère",
        "email": "minister@sanaga.cm"
    }
}


def hash_password(password: str) -> str:
    """Hash un mot de passe avec SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def check_credentials(username: str, password: str) -> bool:
    """Vérifie les identifiants de l'utilisateur"""
    if username not in USERS_DB:
        return False
    
    password_hash = hash_password(password)
    stored_hash = USERS_DB[username]["password_hash"]
    
    return password_hash == stored_hash


def get_user_role(username: str) -> str:
    """Récupère le rôle de l'utilisateur"""
    if username in USERS_DB:
        return USERS_DB[username]["role"]
    return None


def login_user(username: str, password: str) -> bool:
    """Authentifie l'utilisateur et stocke les infos en session"""
    if check_credentials(username, password):
        st.session_state.authenticated = True
        st.session_state.username = username
        st.session_state.role = get_user_role(username)
        st.session_state.email = USERS_DB[username]["email"]
        st.session_state.login_time = datetime.now()
        return True
    return False


def logout_user():
    """Déconnecte l'utilisateur"""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.email = None
    st.session_state.login_time = None


def init_session_state():
    """Initialise l'état de session"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "role" not in st.session_state:
        st.session_state.role = None
    if "email" not in st.session_state:
        st.session_state.email = None
    if "login_time" not in st.session_state:
        st.session_state.login_time = None


def login_page():
    """Page de connexion"""
    # Centre le contenu
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <style>
            .login-container {
                background: linear-gradient(135deg, #0A1929 0%, #10233A 100%);
                border-radius: 12px;
                padding: 40px;
                border: 1px solid #23425F;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }
            .login-title {
                font-family: 'Space Grotesk', sans-serif;
                font-size: 32px;
                font-weight: 700;
                color: #E7EEF6;
                text-align: center;
                margin-bottom: 10px;
            }
            .login-subtitle {
                font-family: 'IBM Plex Mono', monospace;
                font-size: 13px;
                color: #8FA6BE;
                text-align: center;
                margin-bottom: 30px;
                letter-spacing: 0.5px;
                text-transform: uppercase;
            }
            .login-demo {
                background: rgba(22, 163, 74, 0.12);
                border-left: 3px solid #16A34A;
                padding: 12px 14px;
                border-radius: 6px;
                margin-bottom: 25px;
                font-size: 12px;
                color: #8FA6BE;
            }
            .login-demo-title {
                color: #16A34A;
                font-weight: 600;
                margin-bottom: 8px;
            }
            </style>
            <div class="login-container">
                <div class="login-title">🌊 JUMEAU SANAGA</div>
                <div class="login-subtitle">Système d'authentification</div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Formulaire de connexion
        with st.form("login_form"):
            username = st.text_input("Nom d'utilisateur", key="username_input")
            password = st.text_input("Mot de passe", type="password", key="password_input")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                submit_button = st.form_submit_button("🔓 Se connecter", use_container_width=True)
            
            if submit_button:
                if not username or not password:
                    st.error("⚠️ Veuillez remplir tous les champs")
                elif login_user(username, password):
                    st.success(f"✅ Connexion réussie ! Bienvenue {username}")
                    st.rerun()
                else:
                    st.error("❌ Identifiants incorrects. Veuillez réessayer.")
        
        st.markdown("---")
        
        # Section démo
        st.markdown("""
            <div class="login-demo">
                <div class="login-demo-title">📋 Comptes de démonstration :</div>
                <strong>supervisor</strong> → supervisor123<br>
                <strong>engineer</strong> → engineer123<br>
                <strong>chemist</strong> → chemist123<br>
                <strong>field_agent</strong> → agent123<br>
                <strong>minister</strong> → minister123
            </div>
        """, unsafe_allow_html=True)
        
        st.info("💡 Cette interface est sécurisée. En production, utilisez une vraie base de données et HTTPS.")
