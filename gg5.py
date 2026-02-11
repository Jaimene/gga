import streamlit as st
import pandas as pd
import gspread
from datetime import date

# ========== CONFIGURAÇÕES ==========
SPREADSHEET_NAME = "GGApp25"

st.set_page_config(
    page_title="Pedidos",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ========== GOOGLE SHEETS ==========
class SheetsManager:
    def __init__(self, spreadsheet_name=SPREADSHEET_NAME):
        if "GOOGLE_CREDENTIALS" not in st.secrets:
            st.error("Credenciais do Google não encontradas em Streamlit secrets.")
            st.stop()
        try:
            self._gc = gspread.service_account_from_dict(st.secrets["GOOGLE_CREDENTIALS"])
            self._spreadsheet = self._gc.open(spreadsheet_name)
        except Exception as e:
            st.error(f"Erro ao conectar ao Google Sheets: {e}")
            st.stop()

    def _ensure_worksheet(self, worksheet_name, columns=None):
        try:
            worksheet = self._spreadsheet.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = self._spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=20)
            if columns:
                worksheet.append_row(columns)
        return worksheet

    def get_dataframe(self, worksheet_name, columns=None):
        worksheet = self._ensure_worksheet(worksheet_name, columns=columns)
        data = worksheet.get_all_records()
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame(columns=columns if columns else [])

    def append_row(self, worksheet_name, row_dict):
        worksheet = self._ensure_worksheet(worksheet_name, columns=list(row_dict.keys()))
        try:
            worksheet.append_row(list(row_dict.values()))
            return True
        except Exception as e:
            st.error(f"Erro ao adicionar linha em '{worksheet_name}': {e}")
            return False


SHEETS_MANAGER = SheetsManager(SPREADSHEET_NAME)

# ========== ABA PEDIDOS ==========
def aba_pedidos():
    st.header("🧾 Novo Pedido")

    df_clientes = SHEETS_MANAGER.get_dataframe("clientes", columns=["Nome"])
    if df_clientes.empty:
        st.info("Cadastre clientes antes de registrar pedidos.")
        return

    nomes_clientes = df_clientes["Nome"].tolist()

    with st.form("form_pedidos"):
        data_pedido = st.date_input("📅 Data do Pedido", value=date.today())
        cliente = st.selectbox("👤 Cliente", nomes_clientes)
        qnt_cartelas = st.number_input("📦 Qt Cartelas", min_value=1, step=1, value=1)
        valor_base = st.number_input("💰 Valor Base da Cartela (R$)", min_value=0.0, format="%.2f")
        forma_pgto = st.selectbox("💳 Forma de Pagamento", ["Dinheiro", "Cartão", "Pix"])
        pago = st.checkbox("✅ Pago")
        submit = st.form_submit_button("Salvar Pedido")

    if submit:
        valor_total = round(qnt_cartelas * valor_base, 2)

        novo = {
            "Pago": "Sim" if pago else "Não",
            "Data": data_pedido.strftime("%d-%m-%Y"),
            "Cliente": cliente,
            "Qt Cartelas": int(qnt_cartelas),
            "Valor Base": float(valor_base),
            "Valor Total": float(valor_total),
            "Forma de Pagamento": forma_pgto,
        }

        if SHEETS_MANAGER.append_row("pedidos", novo):
            st.success("✅ Pedido salvo!")
            st.rerun()

# ========== ABA VER PEDIDOS ==========
def aba_visualizar_pedidos():
    st.header("📂 Pedidos Salvos (Editar)")

    df = SHEETS_MANAGER.get_dataframe(
        "pedidos",
        columns=["Data","Cliente","Quantidade de Cartelas","Valor Base","Valor Total","Forma de Pagamento","Pago"]
    )

    if df.empty:
        st.info("Nenhum pedido encontrado.")
        return

    # Normalizar valores
    df["Quantidade de Cartelas"] = pd.to_numeric(df["Quantidade de Cartelas"], errors="coerce").fillna(0).astype(int)
    df["Valor Base"] = pd.to_numeric(df["Valor Base"], errors="coerce").fillna(0.0)
    df["Valor Total"] = pd.to_numeric(df["Valor Total"], errors="coerce").fillna(0.0)
    df["Pago"] = df["Pago"].apply(lambda x: True if str(x).lower() in ["sim","true","1"] else False)

    # Lista clientes
    df_clientes = SHEETS_MANAGER.get_dataframe("clientes", columns=["Nome"])
    nomes_clientes = df_clientes["Nome"].tolist() if not df_clientes.empty else []

    st.caption("Toque nos campos, edite e salve individualmente")

    for i, row in df.iterrows():
        with st.container(border=True):
            st.markdown(f"### 🧾 Pedido #{i+1}")

            col1, col2 = st.columns(2)
            with col1:
                nova_data = st.date_input(
                    "📅 Data",
                    value=pd.to_datetime(row["Data"], errors="coerce") or date.today(),
                    key=f"data_{i}"
                )

                novo_cliente = st.selectbox(
                    "👤 Cliente",
                    options=nomes_clientes,
                    index=nomes_clientes.index(row["Cliente"]) if row["Cliente"] in nomes_clientes else 0,
                    key=f"cliente_{i}"
                )

            with col2:
                nova_qtd = st.number_input(
                    "📦 Quantidade",
                    min_value=0,
                    value=int(row["Quantidade de Cartelas"]),
                    step=1,
                    key=f"qtd_{i}"
                )

                novo_pagamento = st.selectbox(
                    "💳 Forma de Pagamento",
                    ["Dinheiro","Cartão","Pix"],
                    index=["Dinheiro","Cartão","Pix"].index(row["Forma de Pagamento"]) if row["Forma de Pagamento"] in ["Dinheiro","Cartão","Pix"] else 0,
                    key=f"pgto_{i}"
                )

            novo_pago = st.checkbox(
                "✅ Pago",
                value=row["Pago"],
                key=f"pago_{i}"
            )

            novo_valor_total = round(nova_qtd * float(row["Valor Base"]), 2)

            st.markdown(f"💰 **Valor Total:** R$ {novo_valor_total:.2f}")

            if st.button("💾 Salvar alterações", key=f"save_{i}"):
                df.loc[i, "Pago"] = "Sim" if novo_pago else "Não"
                df.loc[i, "Data"] = nova_data.strftime("%d-%m-%Y")
                df.loc[i, "Cliente"] = novo_cliente
                df.loc[i, "Qt Cartelas"] = nova_qtd
                df.loc[i, "Forma de Pagamento"] = novo_pagamento
                df.loc[i, "Valor Total"] = novo_valor_total

                if SHEETS_MANAGER.overwrite("pedidos", df):
                    st.success("✅ Pedido atualizado!")
                    st.rerun()


# ========== APP ==========
st.title("📱 Sistema de Pedidos")

menu = st.sidebar.radio("Menu", [
    "🧾 Pedidos",
    "📂 Ver Pedidos"
])

if menu == "🧾 Pedidos":
    aba_pedidos()
elif menu == "📂 Ver Pedidos":
    aba_visualizar_pedidos()


