# =============================
# IA FINANCEIRA PRO - COMPLETO RESTAURADO
# =============================

import streamlit as st
import re
from datetime import datetime
from collections import defaultdict
from io import BytesIO
import matplotlib.pyplot as plt

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

from supabase import create_client, Client

st.set_page_config(page_title="IA Financeira PRO", layout="wide")

# =============================
# SUPABASE
# =============================
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

    if st.button("Entrar"):
        try:
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": senha
            })
            if res and res.user:
                st.session_state.user = res.user
                st.rerun()
        except Exception as e:
            st.error(e)

    if st.button("Cadastrar"):
        supabase.auth.sign_up({"email": email, "password": senha})
        st.success("Conta criada!")

if not st.session_state.user:
    tela_login()
    st.stop()

# =============================
# LOGOUT
# =============================
if st.sidebar.button("🚪 Sair"):
    st.session_state.user = None
    st.rerun()

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
            "saldo": 0.0,
            "historico": [],
            "metas": [],
            "aprendizado": {}
        }
        supabase.table("usuarios").insert(dados).execute()
        return dados

    dados = res.data[0]

    dados["saldo"] = float(dados.get("saldo") or 0)
    dados["historico"] = dados.get("historico") or []
    dados["metas"] = dados.get("metas") or []
    dados["aprendizado"] = dados.get("aprendizado") or {}

    return dados

def salvar_dados(dados):
    supabase.table("usuarios").update(dados).eq("user_id", get_user_id()).execute()

dados = carregar_dados()

# =============================
# IA
# =============================
def prever_categoria(texto):
    texto = texto.lower()

    if texto in dados["aprendizado"]:
        return dados["aprendizado"][texto]

    if "uber" in texto:
        return "transporte"
    if "comida" in texto or "lanche" in texto:
        return "alimentacao"
    if "ganhei" in texto or "recebi" in texto:
        return "receita"

    return "outros"

def extrair_valor(texto):
    numeros = re.findall(r"\d+(?:\.\d+)?", texto)
    return float(numeros[0]) if numeros else 0.0

# =============================
# PROCESSAR
# =============================
def processar_entrada():
    texto = st.session_state.entrada.lower()
    valor = extrair_valor(texto)
    categoria = prever_categoria(texto)

    tipo = "despesa" if "gastei" in texto or "paguei" in texto else "receita"

    dados["saldo"] += valor if tipo == "receita" else -valor

    dados["historico"].append({
        "texto": texto,
        "valor": valor,
        "categoria": categoria,
        "tipo": tipo,
        "data": datetime.now().strftime("%Y-%m")
    })

    salvar_dados(dados)
    st.session_state.entrada = ""

# =============================
# UI
# =============================
st.title("💰 IA Financeira")

st.text_input("Digite", key="entrada")
st.button("Registrar", on_click=processar_entrada)

# =============================
# ENSINAR IA
# =============================
st.subheader("🧠 Ensinar IA")

texto = st.text_input("Frase")
categoria = st.selectbox("Categoria", ["alimentacao","transporte","receita","outros"])

if st.button("Ensinar"):
    dados["aprendizado"][texto.lower()] = categoria
    salvar_dados(dados)
    st.success("Aprendido!")

# =============================
# METAS
# =============================
st.subheader("🎯 Metas")

nome = st.text_input("Nome da meta")
valor = st.number_input("Valor")

if st.button("Criar Meta"):
    dados["metas"].append({"nome": nome, "valor": valor, "valor_atual": 0})
    salvar_dados(dados)

for m in dados["metas"]:
    progresso = m["valor_atual"] / m["valor"] if m["valor"] else 0
    st.write(m["nome"])
    st.progress(progresso)

# =============================
# HISTÓRICO + EXCLUIR
# =============================
st.subheader("📜 Histórico")

for i, item in enumerate(dados["historico"]):
    col1, col2 = st.columns([4,1])
    col1.write(item)

    if col2.button("❌", key=i):
        dados["historico"].pop(i)
        salvar_dados(dados)
        st.rerun()

# =============================
# PDF (FUNCIONANDO)
# =============================
def gerar_pdf():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    story = []
    story.append(Paragraph("Relatório Financeiro", styles["Title"]))

    tabela = [["Data","Tipo","Categoria","Valor"]]

    for i in dados["historico"]:
        tabela.append([
            i.get("data"),
            i.get("tipo"),
            i.get("categoria"),
            f"R$ {i.get('valor')}"
        ])

    t = Table(tabela)
    t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),1,colors.black)]))

    story.append(t)

    doc.build(story)
    buffer.seek(0)
    return buffer

if st.button("📄 Gerar PDF"):
    pdf = gerar_pdf()

    st.download_button("Baixar PDF", pdf, "relatorio.pdf")
