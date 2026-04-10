# =============================
# IA FINANCEIRA WEB APP (NÍVEL PROFISSIONAL)
# =============================

import streamlit as st
import json
import re
import pickle
from datetime import datetime
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

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
# DADOS
# =============================
def carregar_dados():
    try:
        with open("dados.json", "r") as f:
            dados = json.load(f)
    except:
        dados = {}

    if "saldo" not in dados:
        dados["saldo"] = 0
    if "historico" not in dados:
        dados["historico"] = []
    if "metas" not in dados:
        dados["metas"] = []
    if "aprendizado" not in dados:
        dados["aprendizado"] = {}

    return dados


def salvar_dados(dados):
    with open("dados.json", "w") as f:
        json.dump(dados, f, indent=4)


dados = carregar_dados()

# =============================
# IA
# =============================
def prever_categoria(texto):

    # REGRAS INTELIGENTES (antes da IA)
    if "lanche" in texto or "comida" in texto:
        return "alimentacao"
    if "uber" in texto or "transporte" in texto:
        return "transporte"
    if "salario" in texto or "ganhei" in texto or "recebi" in texto:
        return "receita"

    # IA (fallback)
    if texto in dados["aprendizado"]:
        return dados["aprendizado"][texto]

    X = vectorizer.transform([texto])
    return modelo.predict(X)[0]


def extrair_valor(texto):
    numeros = re.findall(r"\d+", texto)
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

    # DELETE COM CONFIRMAÇÃO
    if "deletar gasto" in texto:
        for item in reversed(dados["historico"]):
            if item["categoria"] in texto:
                st.session_state["confirmar_delete"] = item
                return

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

# =============================
# FORMULÁRIO (CORRETO)
# =============================
with st.form("form_entrada"):
    st.text_input("Digite (ex: gastei 50 com lanche)", key="entrada")
    st.form_submit_button("Registrar", on_click=processar_entrada)

# =============================
# ENSINAR IA (FORA DO FORM)
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

if st.button("Ensinar IA", key="btn_ensinar"):
    if texto_ensinar and categoria_ensinar:
        dados["aprendizado"][texto_ensinar.lower()] = categoria_ensinar
        salvar_dados(dados)
        st.success("IA aprendeu com sucesso!")

    st.text_input("Digite (ex: gastei 50 com lanche)", key="entrada")
    st.form_submit_button("Registrar", on_click=processar_entrada)

# =============================
# CONFIRMAR DELETE
# =============================
if "confirmar_delete" in st.session_state:
    item = st.session_state["confirmar_delete"]
    st.warning(f"Deseja deletar: {item['texto']} - R$ {item['valor']}?")

    col1, col2 = st.columns(2)
    if col1.button("✅ Confirmar"):
        dados["historico"].remove(item)
        salvar_dados(dados)
        del st.session_state["confirmar_delete"]
        st.success("Deletado com sucesso")

    if col2.button("❌ Cancelar"):
        del st.session_state["confirmar_delete"]

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
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors

    doc = SimpleDocTemplate("relatorio.pdf")
    styles = getSampleStyleSheet()
    elementos = []

    # TÍTULO
    elementos.append(Paragraph("Relatório Financeiro", styles['Title']))
    elementos.append(Spacer(1, 12))

    # SALDO
    elementos.append(Paragraph(f"Saldo: R$ {dados['saldo']}", styles['Normal']))
    elementos.append(Spacer(1, 12))

    # METAS
    elementos.append(Paragraph("Metas:", styles['Heading2']))
    elementos.append(Spacer(1, 10))

    if dados["metas"]:
        for m in dados["metas"]:
            elementos.append(Paragraph(f"{m['nome']} - R$ {m['valor']}", styles['Normal']))
    else:
        elementos.append(Paragraph("Nenhuma meta cadastrada", styles['Normal']))

    elementos.append(Spacer(1, 20))

    # HISTÓRICO EM TABELA
    elementos.append(Paragraph("Histórico:", styles['Heading2']))
    elementos.append(Spacer(1, 10))

    if dados["historico"]:
        tabela_dados = [["Data", "Descrição", "Valor"]]

        for item in dados["historico"]:
            tabela_dados.append([
                item["data"],
                item["texto"],
                f"R$ {item['valor']}"
            ])

        tabela = Table(tabela_dados)

        tabela.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR',(0,0),(-1,0),colors.white),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
        ]))

        elementos.append(tabela)
    else:
        elementos.append(Paragraph("Nenhum registro encontrado", styles['Normal']))

    elementos.append(Spacer(1, 20))

    # GRÁFICO
    try:
        elementos.append(Paragraph("Resumo de Gastos:", styles['Heading2']))
        elementos.append(Spacer(1, 10))
        elementos.append(Image("grafico.png", width=300, height=200))
    except:
        elementos.append(Paragraph("Gráfico não disponível", styles['Normal']))

    # FINAL
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