# =============================
# IA FINANCEIRA WEB APP (NÍVEL PROFISSIONAL)
# =============================

import streamlit as st
import json
import re
import pickle
import os
from datetime import datetime
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="IA Financeira", layout="wide")

# =============================
# SUPABASE
# =============================
from supabase import create_client, Client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =============================
# LOGIN
# =============================
if "user" not in st.session_state:
    st.session_state.user = None

def tela_login():
    st.title("🔐 Login")

    email = st.text_input("E-mail")
    senha = st.text_input("Senha", type="password")

    col1, col2 = st.columns(2)

    if col1.button("Entrar"):
        try:
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": senha
            })

            if res and res.user:
                st.session_state.user = res.user
                st.success("Login realizado!")
                st.rerun()  # ✅ CORREÇÃO
            else:
                st.error("E-mail ou senha inválidos")

        except:
            st.error("Erro no login")

    if col2.button("Cadastrar"):
        try:
            supabase.auth.sign_up({
                "email": email,
                "password": senha,
                "options": {
                    "email_redirect_to": "https://ia-financeira-hcpjnmqrierowuvyu9upy3.streamlit.app/"
                }
            })
            st.success("Conta criada! Verifique seu e-mail.")
        except:
            st.error("Erro ao cadastrar")

if not st.session_state.user:
    tela_login()
    st.stop()

# =============================
# USER
# =============================
def get_user_id():
    return str(st.session_state.user.id)

# =============================
# DADOS
# =============================
def carregar_dados():
    res = supabase.table("usuarios").select("*").eq("user_id", get_user_id()).execute()

    if not res.data:
        dados = {
            "user_id": get_user_id(),
            "saldo": 0,
            "historico": [],
            "metas": [],
            "aprendizado": {}
        }
        try:
            supabase.table("usuarios").insert(dados).execute()
        except Exception as e:
            st.error(f"Erro ao inserir: {e}")
        return dados

    dados = res.data[0]

    if dados.get("historico") is None:
        dados["historico"] = []
    if dados.get("metas") is None:
        dados["metas"] = []
    if dados.get("aprendizado") is None:
        dados["aprendizado"] = {}

    return dados

def salvar_dados(dados):
    supabase.table("usuarios").update(dados).eq("user_id", get_user_id()).execute()

dados = carregar_dados()

# =============================
# 🔥 LIMPEZA DE DADOS (CORREÇÃO)
# =============================
if isinstance(dados.get("historico"), list):
    dados["historico"] = [i for i in dados["historico"] if isinstance(i, dict)]
else:
    dados["historico"] = []

# =============================
# STYLE
# =============================
st.markdown("""
<style>
body {background-color: #0e1117; color: white;}
.stButton>button {background-color: #00c853; color: white; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

# =============================
# MODELO IA
# =============================
def treinar_modelo():
    frases = ["gastei com lanche","comprei comida","paguei uber","ganhei salario","recebi dinheiro"]
    categorias = ["alimentacao","alimentacao","transporte","receita","receita"]

    vectorizer = CountVectorizer()
    X = vectorizer.fit_transform(frases)

    modelo = MultinomialNB()
    modelo.fit(X, categorias)

    with open("modelo.pkl", "wb") as f:
        pickle.dump((modelo, vectorizer), f)

def carregar_modelo():
    try:
        with open("modelo.pkl", "rb") as f:
            return pickle.load(f)
    except:
        treinar_modelo()
        return carregar_modelo()

modelo, vectorizer = carregar_modelo()

# =============================
# SIDEBAR
# =============================
if st.sidebar.button("Sair"):
    st.session_state.user = None
    st.rerun()

# =============================
# IA
# =============================
def prever_categoria(texto):
    if "lanche" in texto or "comida" in texto:
        return "alimentacao"
    if "uber" in texto:
        return "transporte"
    if "ganhei" in texto or "recebi" in texto:
        return "receita"

    if texto in dados["aprendizado"]:
        return dados["aprendizado"][texto]

    return modelo.predict(vectorizer.transform([texto]))[0]

def extrair_valor(texto):
    numeros = re.findall(r"\d+(?:\.\d+)?", texto)
    return float(numeros[0]) if numeros else 0

# =============================
# APP
# =============================
st.title("💰 IA Financeira Inteligente")

if "entrada" not in st.session_state:
    st.session_state.entrada = ""

def processar_entrada():
    texto = st.session_state.entrada.lower()
    valor = extrair_valor(texto)
    categoria = prever_categoria(texto)

    if "gastei" in texto or "paguei" in texto:
        dados["saldo"] -= valor
        dados["historico"].append({
            "texto": texto,
            "valor": valor,
            "categoria": categoria,
            "tipo": "despesa",
            "data": datetime.now().strftime("%Y-%m")
        })

    elif "ganhei" in texto or "recebi" in texto:
        dados["saldo"] += valor
        dados["historico"].append({
            "texto": texto,
            "valor": valor,
            "categoria": categoria,
            "tipo": "receita",
            "data": datetime.now().strftime("%Y-%m")
        })

    salvar_dados(dados)
    st.success("Registro salvo!")
    st.session_state.entrada = ""

with st.form("form_entrada"):
    st.text_input("Digite (ex: gastei 50 com lanche)", key="entrada")
    st.form_submit_button("Registrar", on_click=processar_entrada)

# =============================
# ENSINAR IA
# =============================
st.subheader("🧠 Ensinar IA")

col1, col2 = st.columns(2)

with col1:
    texto_ensinar = st.text_input("Frase para ensinar", key="ensinar_texto")

with col2:
    categoria_ensinar = st.selectbox(
        "Categoria",
        ["alimentacao", "transporte", "receita", "outros"],
        key="ensinar_categoria"
    )

if st.button("Ensinar IA"):
    if texto_ensinar and categoria_ensinar:
        dados["aprendizado"][texto_ensinar.lower()] = categoria_ensinar
        salvar_dados(dados)
        st.success("IA aprendeu!")

# =============================
# LIMPAR
# =============================
st.subheader("⚠️ Zona de Perigo")

if st.button("🧹 Limpar Tudo"):
    dados["saldo"] = 0
    dados["historico"] = []
    dados["metas"] = []
    dados["aprendizado"] = {}
    salvar_dados(dados)
    st.success("Dados zerados!")
    st.rerun()

# =============================
# SALDO
# =============================
st.subheader("💵 Saldo Atual")
st.metric("Saldo", f"R$ {dados['saldo']}")

# =============================
# GRÁFICO (CORRIGIDO)
# =============================
st.subheader("📊 Gastos por Categoria")

categorias = {}

for item in dados["historico"]:
    if isinstance(item, dict):
        tipo = item.get("tipo")
        categoria = item.get("categoria")
        valor = item.get("valor", 0)

        if tipo == "despesa" and categoria:
            categorias[categoria] = categorias.get(categoria, 0) + valor

if categorias:
    fig, ax = plt.subplots()
    ax.pie(categorias.values(), labels=categorias.keys(), autopct='%1.1f%%')
    st.pyplot(fig)
    fig.savefig("grafico.png")
else:
    st.info("Sem dados para gráfico")

# =============================
# HISTÓRICO
# =============================
st.subheader("📜 Histórico")
st.write(dados["historico"])
