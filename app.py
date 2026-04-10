# =============================
# IA FINANCEIRA WEB APP (NÍVEL PROFISSIONAL)
# =============================

import streamlit as st
import json
import re
import pickle
import os
import hashlib
from datetime import datetime
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

# =============================
# SUPABASE CONFIG
# =============================
from supabase import create_client, Client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)



# =============================
# =============================
# LOGIN SUPABASE
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
            st.session_state.user = res.user
            st.success("Login realizado!")
            st.rerun()
        except:
            st.error("Erro no login")

    if col2.button("Cadastrar"):
        try:
            supabase.auth.sign_up({
                "email": email,
                "password": senha
            })
            st.success("Conta criada!")
        except:
            st.error("Erro ao cadastrar")

if not st.session_state.user:
    tela_login()
    st.stop()

# =============================
# CONFIG VISUAL
# =============================
st.set_page_config(page_title="IA Financeira", layout="wide")

st.markdown("""
    <style>
    body {background-color: #0e1117; color: white;}
    .stButton>button {background-color: #00c853; color: white; border-radius: 10px;}
    .stTextInput>div>div>input {border-radius: 10px;}
    </style>
""", unsafe_allow_html=True)

# =============================
# MODELO
# =============================
def treinar_modelo():
    frases = [
        "gastei com lanche",
        "comprei comida",
        "paguei uber",
        "ganhei salario",
        "recebi dinheiro"
    ]

    categorias = [
        "alimentacao",
        "alimentacao",
        "transporte",
        "receita",
        "receita"
    ]

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
        with open("modelo.pkl", "rb") as f:
            return pickle.load(f)

modelo, vectorizer = carregar_modelo()

# =============================
# =============================
# DADOS SUPABASE
# =============================
def get_user_id():
    return st.session_state.user.id

def carregar_dados():
    res = supabase.table("usuarios").select("*").eq("id", get_user_id()).execute()

    if res.data:
        return res.data[0]
    else:
        dados = {
            "id": get_user_id(),
            "saldo": 0,
            "historico": [],
            "metas": [],
            "aprendizado": {}
        }
        supabase.table("usuarios").insert(dados).execute()
        return dados

def salvar_dados(dados):
    supabase.table("usuarios").update(dados).eq("id", get_user_id()).execute()


# =============================
# SIDEBAR (USUÁRIO)
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
    if "uber" in texto or "transporte" in texto:
        return "transporte"
    if "salario" in texto or "ganhei" in texto or "recebi" in texto:
        return "receita"

    if texto in dados["aprendizado"]:
        return dados["aprendizado"][texto]

    X = vectorizer.transform([texto])
    return modelo.predict(X)[0]

def extrair_valor(texto):
    numeros = re.findall(r"\d+(?:\.\d+)?", texto)
    return float(numeros[0]) if numeros else 0

# =============================
# UI
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
        salvar_dados(dados)
        st.success(f"Despesa registrada: R${valor}")

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
        st.success(f"Receita registrada: R${valor}")

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
# RESET POR USUÁRIO
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
# METAS
# =============================
st.subheader("🎯 Metas")

meta_input = st.text_input("Ex: viagem praia, 200")

if st.button("Adicionar Meta"):
    try:
        nome, valor = meta_input.split(",")
        dados["metas"].append({
            "nome": nome.strip(),
            "valor": float(valor)
        })
        salvar_dados(dados)
        st.success("Meta adicionada")
    except:
        st.error("Formato inválido")

# =============================
# SALDO
# =============================
st.subheader("💵 Saldo Atual")
st.metric("Saldo", f"R$ {dados['saldo']}")

# =============================
# GRÁFICOS
# =============================
categorias = {}
for item in dados["historico"]:
    if item["tipo"] == "despesa":
        categorias[item["categoria"]] = categorias.get(item["categoria"], 0) + item["valor"]

if categorias:
    fig, ax = plt.subplots()
    ax.pie(categorias.values(), labels=categorias.keys(), autopct='%1.1f%%')
    st.pyplot(fig)
    fig.savefig("grafico.png")

# =============================
# PDF
# =============================
def gerar_pdf():
    doc = SimpleDocTemplate("relatorio.pdf")
    styles = getSampleStyleSheet()
    elementos = []

    elementos.append(Paragraph("Relatório Financeiro", styles['Title']))
    elementos.append(Spacer(1, 12))
    elementos.append(Paragraph(f"Saldo: R$ {dados['saldo']}", styles['Normal']))
    elementos.append(Spacer(1, 12))

    if os.path.exists("grafico.png"):
        elementos.append(Image("grafico.png", width=300, height=200))

    doc.build(elementos)

if st.button("📄 Gerar PDF"):
    gerar_pdf()
    with open("relatorio.pdf", "rb") as f:
        st.download_button("Baixar PDF", f, file_name="relatorio.pdf")

# =============================
# HISTÓRICO
# =============================
st.subheader("📜 Histórico")
st.write(dados["historico"])
