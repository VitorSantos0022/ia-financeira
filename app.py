# =============================
# IA FINANCEIRA PRO - COMPLETO
# =============================

import streamlit as st
import re
from datetime import datetime
from collections import defaultdict
import matplotlib.pyplot as plt
from io import BytesIO

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
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

    col1, col2 = st.columns(2)

    if col1.button("Entrar"):
        try:
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": senha
            })

            if res and res.user:
                st.session_state.user = res.user
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Login inválido")

        except Exception as e:
            st.error(f"Erro no login: {e}")

    if col2.button("Cadastrar"):
        try:
            supabase.auth.sign_up({
                "email": email,
                "password": senha
            })
            st.success("Conta criada! Verifique seu e-mail.")
        except Exception as e:
            st.error(f"Erro ao cadastrar: {e}")


if not st.session_state.user:
    tela_login()
    st.stop()


# =============================
# USER ID
# =============================
def get_user_id():
    return str(st.session_state.user.id)


# =============================
# CARREGAR DADOS
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
# IA SIMPLES
# =============================
def prever_categoria(texto):
    texto = texto.lower()

    if "uber" in texto:
        return "transporte"
    if "comida" in texto or "lanche" in texto:
        return "alimentacao"
    if "recebi" in texto or "ganhei" in texto:
        return "receita"

    return dados["aprendizado"].get(texto, "outros")


def extrair_valor(texto):
    numeros = re.findall(r"\d+(?:\.\d+)?", texto)
    return float(numeros[0]) if numeros else 0.0


# =============================
# PROCESSAR ENTRADA
# =============================
def processar_entrada():
    texto = st.session_state.entrada.lower()
    valor = extrair_valor(texto)
    categoria = prever_categoria(texto)

    mes = datetime.now().strftime("%Y-%m")
    ano = datetime.now().strftime("%Y")

    if "gastei" in texto or "paguei" in texto:
        dados["saldo"] -= valor

        dados["historico"].append({
            "texto": texto,
            "valor": valor,
            "categoria": categoria,
            "tipo": "despesa",
            "mes": mes,
            "ano": ano
        })

    elif "ganhei" in texto or "recebi" in texto:
        dados["saldo"] += valor

        dados["historico"].append({
            "texto": texto,
            "valor": valor,
            "categoria": categoria,
            "tipo": "receita",
            "mes": mes,
            "ano": ano
        })

    # metas automáticas
    for meta in dados["metas"]:
        meta["valor_atual"] = meta.get("valor_atual", 0)
        if categoria == "receita":
            meta["valor_atual"] += valor

    salvar_dados(dados)
    st.success("Registro salvo!")


# =============================
# UI PRINCIPAL
# =============================
st.title("💰 IA Financeira PRO")

with st.form("form"):
    st.text_input("Digite (ex: gastei 50 com lanche)", key="entrada")
    st.form_submit_button("Registrar", on_click=processar_entrada)


# =============================
# METAS
# =============================
st.subheader("🎯 Metas Financeiras")

nome = st.text_input("Nome da meta")
valor_meta = st.number_input("Valor da meta", min_value=0.0)

if st.button("Criar Meta"):
    dados["metas"].append({
        "nome": nome,
        "valor": valor_meta,
        "valor_atual": 0
    })
    salvar_dados(dados)
    st.success("Meta criada!")

for meta in dados["metas"]:
    progresso = meta.get("valor_atual", 0) / meta["valor"] if meta["valor"] > 0 else 0

    st.write(f"📌 {meta['nome']}")
    st.progress(min(progresso, 1.0))
    st.write(f"{meta.get('valor_atual',0)} / {meta['valor']}")


# =============================
# DASHBOARD
# =============================
st.subheader("📊 Dashboard")

despesas = defaultdict(float)
receitas = defaultdict(float)

for i in dados["historico"]:
    if i["tipo"] == "despesa":
        despesas[i["mes"]] += i["valor"]
    else:
        receitas[i["mes"]] += i["valor"]

meses = sorted(set(list(despesas.keys()) + list(receitas.keys())))

if meses:
    fig, ax = plt.subplots()
    ax.plot(meses, [receitas[m] for m in meses], label="Receitas")
    ax.plot(meses, [despesas[m] for m in meses], label="Despesas")
    ax.legend()
    st.pyplot(fig)


# =============================
# HISTÓRICO
# =============================
st.subheader("📜 Histórico")

filtro = st.selectbox("Filtrar mês", ["Todos"] + sorted(set(i["mes"] for i in dados["historico"])))

for i in dados["historico"]:
    if filtro == "Todos" or i["mes"] == filtro:
        st.write(i)


# =============================
# PDF EXPORT (FUNCIONANDO)
# =============================
st.subheader("📄 Exportar PDF")


def gerar_pdf():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Relatório Financeiro", styles["Title"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"Saldo: R$ {dados['saldo']:.2f}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Histórico:", styles["Heading2"]))

    for i in dados["historico"]:
        story.append(Paragraph(str(i), styles["Normal"]))

    doc.build(story)
    buffer.seek(0)
    return buffer


if st.button("📄 Gerar PDF"):
    pdf = gerar_pdf()

    st.download_button(
        "⬇️ Baixar PDF",
        data=pdf,
        file_name="relatorio_financeiro.pdf",
        mime="application/pdf"
    )
