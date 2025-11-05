import streamlit as st
import pandas as pd
import gspread
import openrouteservice
import folium
from datetime import date
from streamlit_folium import st_folium

# ========== CONFIGURAÇÕES ==========
SPREADSHEET_NAME = "GGApp"
ENDERECO_PARTIDA = "Rua Doutor Clemente Ferreira, São Caetano do Sul,SP,Brasil"
ORS_API_KEY = st.secrets.get("ORS_API_KEY", None)
ors = None
if ORS_API_KEY:
    try:
        ors = openrouteservice.Client(key=ORS_API_KEY)
    except Exception:
        ors = None

class SheetsManager:
    def __init__(self, spreadsheet_name=SPREADSHEET_NAME):
        if "GOOGLE_CREDENTIALS" not in st.secrets:
            st.error("Credenciais do Google não encontradas em Streamlit secrets. Configure GOOGLE_CREDENTIALS.")
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
        else:
            return pd.DataFrame(columns=columns if columns else [])

    def append_row(self, worksheet_name, row_dict):
        worksheet = self._ensure_worksheet(worksheet_name, columns=list(row_dict.keys()))
        try:
            first_row = worksheet.row_values(1)
            if not first_row:
                worksheet.append_row(list(row_dict.keys()))
        except Exception:
            worksheet.append_row(list(row_dict.keys()))
        try:
            worksheet.append_row(list(row_dict.values()))
            return True
        except Exception as e:
            st.error(f"Erro ao adicionar linha em '{worksheet_name}': {e}")
            return False

    def overwrite(self, worksheet_name, dataframe):
        worksheet = self._ensure_worksheet(worksheet_name, columns=list(dataframe.columns))
        try:
            worksheet.clear()
            worksheet.update([dataframe.columns.values.tolist()] + dataframe.values.tolist())
            return True
        except Exception as e:
            st.error(f"Erro ao sobrescrever aba '{worksheet_name}': {e}")
            return False

    def list_worksheets(self):
        try:
            return [ws.title for ws in self._spreadsheet.worksheets()]
        except Exception:
            return []

SHEETS_MANAGER = SheetsManager(SPREADSHEET_NAME)

def aba_producao():
    st.header("📅 Registro Diário de Produção")
    columns = ["Data", "Ovos", "Galinhas em Postura", "Vendas (R$)", "Mortes"]
    df = SHEETS_MANAGER.get_dataframe("producao", columns=columns)

    with st.form("form_producao"):
        data = st.date_input("Data", value=date.today(), format="DD-MM-YYYY")
        ovos = st.number_input("Ovos coletados", min_value=0)
        galinhas = st.number_input("Galinhas em postura", min_value=0, max_value=1000, value=200)
        vendas = st.number_input("Valor das vendas (R$)", min_value=0.0, format="%.2f")
        mortes = st.number_input("Número de galinhas mortas", min_value=0)
        submit = st.form_submit_button("Salvar produção")

    if submit:
        novo = {
            "Data": data.strftime("%d-%m-%Y"),
            "Ovos": int(ovos),
            "Galinhas em Postura": int(galinhas),
            "Vendas (R$)": float(vendas),
            "Mortes": int(mortes)
        }
        if SHEETS_MANAGER.append_row("producao", novo):
            st.success("✅ Registro salvo!")
            st.rerun()

    st.subheader("📋 Histórico de Produção")
    st.dataframe(df, use_container_width=True)

def aba_custos():
    st.header("💰 Lançamento de Custos")
    columns = ["Data", "Categoria", "Descrição", "Valor (R$)"]
    df = SHEETS_MANAGER.get_dataframe("custos", columns=columns)

    with st.form("form_custos"):
        data = st.date_input("Data do custo", value=date.today(), format="DD-MM-YYYY")
        categoria = st.selectbox("Categoria", ["Ração", "Vacinas", "Mão de obra", "Energia", "Outros"])
        descricao = st.text_input("Descrição")
        valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        submit = st.form_submit_button("Salvar custo")

    if submit:
        novo = {
            "Data": data.strftime("%d-%m-%Y"),
            "Categoria": categoria,
            "Descrição": descricao,
            "Valor (R$)": float(valor)
        }
        if SHEETS_MANAGER.append_row("custos", novo):
            st.success("✅ Custo registrado!")
            st.rerun()

    st.subheader("📋 Histórico de Custos")
    st.dataframe(df, use_container_width=True)

def aba_clientes():
    st.header("📋 Cadastro de Clientes")
    columns = ["nome", "endereco", "observacoes"]
    df = SHEETS_MANAGER.get_dataframe("clientes", columns=columns)

    with st.form("form_clientes"):
        nome = st.text_input("Nome do Cliente")
        endereco = st.text_input("Endereço Completo")
        observacoes = st.text_input("Observações (ex.: Apto 42, Bloco B)")
        submit = st.form_submit_button("Adicionar Cliente")

    if submit:
        if nome and endereco:
            novo = {
                "nome": nome,
                "endereco": endereco,
                "observacoes": observacoes.strip()
            }
            if SHEETS_MANAGER.append_row("clientes", novo):
                st.success("Cliente adicionado!")
                st.rerun()
        else:
            st.warning("Preencha nome e endereço.")

    st.subheader("📁 Lista de Clientes")
    df = SHEETS_MANAGER.get_dataframe("clientes", columns=columns)
    if not df.empty:
        for _, row in df.iterrows():
            obs_txt = f" — Obs.: {row.get('Obs','')}" if row.get("Obs") else ""
            st.write(f"**{row.get('Nome','')}** — {row.get('Endereço','')}{obs_txt}")
    else:
        st.info("Nenhum cliente cadastrado.")

def aba_relatorios():
    st.header("📊 Indicadores Gerais")
    df_producao = SHEETS_MANAGER.get_dataframe("producao", columns=["Data","Ovos","Galinhas em Postura","Vendas (R$)"])
    df_custos = SHEETS_MANAGER.get_dataframe("custos", columns=["Data","Categoria","Descrição","Valor (R$)"])

    if not df_producao.empty:
        df_producao["Ovos"] = pd.to_numeric(df_producao["Ovos"], errors="coerce").fillna(0)
        df_producao["Galinhas em Postura"] = pd.to_numeric(df_producao["Galinhas em Postura"], errors="coerce").fillna(0)
        df_producao["Vendas (R$)"] = pd.to_numeric(df_producao["Vendas (R$)"], errors="coerce").fillna(0)

        media_ovos = df_producao["Ovos"].mean()
        taxa = (df_producao["Ovos"].sum() / df_producao["Galinhas em Postura"].replace(0,1).sum()) * 100 if df_producao["Galinhas em Postura"].sum() > 0 else 0
        total_vendas = df_producao["Vendas (R$)"].sum()

        st.metric("Produção Média de Ovos", f"{media_ovos:.1f}")
        st.metric("Taxa de Postura Média", f"{taxa:.1f}%")
        st.metric("Total de Vendas", f"R$ {total_vendas:.2f}")
    else:
        st.info("Nenhum dado de produção disponível para relatório.")

    if not df_custos.empty:
        df_custos["Valor (R$)"] = pd.to_numeric(df_custos["Valor (R$)"], errors="coerce").fillna(0)
        total_custos = df_custos["Valor (R$)"].sum()
        st.metric("Total de Custos", f"R$ {total_custos:.2f}")

def aba_fechamento():
    st.header("📆 Fechamento do Mês")
    df_producao = SHEETS_MANAGER.get_dataframe("producao", columns=["Data","Ovos","Galinhas em Postura","Vendas (R$)"])
    df_custos = SHEETS_MANAGER.get_dataframe("custos", columns=["Data","Categoria","Descrição","Valor (R$)"])

    if not df_producao.empty:
        df_producao["Data"] = pd.to_datetime(df_producao["Data"], errors="coerce")
        df_producao["Ano-Mês"] = df_producao["Data"].dt.to_period("M")
        resumo_prod = df_producao.groupby("Ano-Mês").agg({
            "Ovos": ["sum","mean"],
            "Galinhas em Postura": "max",
            "Vendas (R$)": "sum"
        }).reset_index()
        resumo_prod.columns = ["Ano-Mês","Total Ovos","Média Ovos","Galinhas em Postura","Total Vendas"]
        resumo_prod["Taxa de Postura (%)"] = (resumo_prod["Total Ovos"] / resumo_prod["Galinhas em Postura"].replace(0,1)) * 100

        if not df_custos.empty:
            df_custos["Data"] = pd.to_datetime(df_custos["Data"], errors="coerce")
            df_custos["Ano-Mês"] = df_custos["Data"].dt.to_period("M")
            resumo_custos = df_custos.groupby("Ano-Mês")["Valor (R$)"].sum().reset_index()
            resumo_custos.columns = ["Ano-Mês","Total Custos"]
            fechamento = pd.merge(resumo_prod, resumo_custos, on="Ano-Mês", how="left").fillna(0)
            fechamento["Lucro (R$)"] = fechamento["Total Vendas"] - fechamento["Total Custos"]
        else:
            fechamento = resumo_prod.copy()
            fechamento["Total Custos"] = 0.0
            fechamento["Lucro (R$)"] = fechamento["Total Vendas"]

        st.dataframe(fechamento, use_container_width=True)
    else:
        st.info("Nenhum dado de produção encontrado.")

def geocodificar_endereco(endereco, nome):
    if not ors:
        st.error("OpenRouteService não configurado. Adicione ORS_API_KEY em Streamlit secrets para usar rotas.")
        return None
    try:
        resposta = ors.pelias_search(text=endereco)
        coords = resposta["features"][0]["geometry"]["coordinates"]
        return coords
    except Exception:
        st.warning(f"Erro ao localizar endereço: {nome}")
        return None

def aba_rota():
    st.header("🚚 Geração de Rota de Entrega")
    df_clientes = SHEETS_MANAGER.get_dataframe("clientes", columns=["Nome","Endereço","Obs"])
    if df_clientes.empty:
        st.info("Cadastre clientes antes de gerar a rota.")
        return

    selecionados = st.multiselect("Selecione os clientes com pedido:", [f"{row['nome']} – {row['endereco']}" for _, row in df_clientes.iterrows()])
    if not selecionados:
        if st.session_state.get("mostrar_rota", False):
            _mostrar_rota_persistente()
        return

    partida = st.text_input("Endereço de partida:", value=ENDERECO_PARTIDA)

    if st.button("Gerar Rota Otimizada"):
        coordenadas = []
        nomes = []

        coord_partida = geocodificar_endereco(partida, "Partida")
        if not coord_partida:
            st.stop()
        coordenadas.append(coord_partida)
        nomes.append("Partida")

        for s in selecionados:
            c = df_clientes[df_clientes.apply(lambda row: f"{row['nome']} – {row['endereco']}" == s, axis=1)].iloc[0]
            coord = geocodificar_endereco(c["endereco"], c["nome"])
            if coord:
                coordenadas.append(coord)
                nomes.append(c["nome"])

        st.session_state["rota_coords"] = coordenadas
        st.session_state["rota_nomes"] = nomes
        st.session_state["mostrar_rota"] = True

    if st.session_state.get("mostrar_rota", False):
        _mostrar_rota_persistente()

def _mostrar_rota_persistente():
    try:
        coordenadas = st.session_state["rota_coords"]
        nomes = st.session_state["rota_nomes"]

        rotas = ors.directions(
            coordinates=coordenadas,
            profile="driving-car",
            format="geojson",
            optimize_waypoints=len(coordenadas) >= 4
        )

        distancia = rotas["features"][0]["properties"]["segments"][0]["distance"] / 1000
        duracao = rotas["features"][0]["properties"]["segments"][0]["duration"] / 60
        st.success(f"Distância: {distancia:.2f} km | Tempo: {duracao:.1f} min")

        m = folium.Map(location=coordenadas[0][::-1], zoom_start=12)
        folium.Marker(coordenadas[0][::-1], tooltip="Partida", icon=folium.Icon(color="green")).add_to(m)
        for i, coord in enumerate(coordenadas[1:], 1):
            folium.Marker(coord[::-1], tooltip=nomes[i], icon=folium.Icon(color="blue")).add_to(m)
        folium.PolyLine([c[::-1] for c in coordenadas], color="blue").add_to(m)
        st_folium(m, width=700, height=500)

        if len(coordenadas) >= 2:
            # monta URLs com coordenadas (ordem otimizada)
            google_maps_url = (
                f"https://www.google.com/maps/dir/{coordenadas[0][1]},{coordenadas[0][0]}"
                + "".join([f"/{coord[1]},{coord[0]}" for coord in coordenadas[1:]])
            )
            waze_url = f"https://waze.com/ul?ll={coordenadas[-1][1]},{coordenadas[-1][0]}&navigate=yes"

            st.markdown(f"**🗺️ Google Maps:** [Abrir Rota]({google_maps_url})", unsafe_allow_html=True)
            st.markdown(f"**🚗 Waze (último destino):** [Abrir Rota]({waze_url})", unsafe_allow_html=True)

            # Botão copiar link (JS) — usamos f-string para inserir a URL com segurança
            st.markdown(f'''
                <input type="text" value="{google_maps_url}" id="linkRota" readonly style="opacity:0; position:absolute;">
                <button onclick="navigator.clipboard.writeText(document.getElementById('linkRota').value)" 
                        style="padding:8px 14px; background-color:#ffc107; border:none; border-radius:5px; cursor:pointer;">
                    📋 Copiar Link do Google Maps
                </button>
            ''', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Erro ao gerar rota: {e}")

def aba_pedidos():
    st.header("🧾 Pedidos")
    columns = ["Cliente","Quantidade de Cartelas","Valor Base","Valor Total","Forma de Pagamento","Pago"]
    df_clientes = SHEETS_MANAGER.get_dataframe("clientes", columns=["Nome","Endereço","Obs"])
    if df_clientes.empty:
        st.info("Cadastre clientes antes de registrar pedidos.")
        return
    nomes_clientes = df_clientes["Nome"].tolist()

    with st.form("form_pedidos"):
        data_pedido = st.date_input("Data do Pedido", value=date.today(), format="DD-MM-YYYY")
        cliente = st.selectbox("Cliente", nomes_clientes)
        qnt_cartelas = st.number_input("Quantidade de Cartelas", min_value=1, step=1, value=1)
        valor_base = st.number_input("Valor Base da Cartela (R$)", min_value=0.0, format="%.2f", value=0.0)
        forma_pgto = st.selectbox("Forma de Pagamento", ["Dinheiro","Cartão","Pix"])
        pago = st.checkbox("✅ Pago")
        submit = st.form_submit_button("Salvar Pedido")


    if submit:
        valor_total = round(qnt_cartelas * valor_base, 2)
        novo = {
            "Data": data_pedido.strftime("%d-%m-%Y"),
            "Cliente": cliente,
            "Quantidade de Cartelas": int(qnt_cartelas),
            "Valor Base": float(valor_base),
            "Valor Total": float(valor_total),
            "Forma de Pagamento": forma_pgto,
            "Pago": "Sim" if pago else "Não"
        }
        if SHEETS_MANAGER.append_row("pedidos", novo):
            st.success("✅ Pedido salvo!")

    st.subheader("📋 Lista de Pedidos")
    df = SHEETS_MANAGER.get_dataframe("pedidos", columns=columns)

    if not df.empty:
        # Converter tipos
        df["Quantidade de Cartelas"] = pd.to_numeric(df["Quantidade de Cartelas"], errors="coerce").fillna(0).astype(int)
        df["Valor Base"] = pd.to_numeric(df["Valor Base"], errors="coerce").fillna(0.0)
        df["Valor Total"] = pd.to_numeric(df["Valor Total"], errors="coerce").fillna(0.0)

        # Normalizar campo Pago para booleano
        df["Pago"] = df["Pago"].apply(lambda x: True if str(x).strip().lower() in ["sim","true","1"] else False)

        # Adicionar coluna de remoção (inicialmente False)
        df["Remover"] = False

        editados = st.data_editor(
            df,
            use_container_width=True,
            num_rows="fixed",
            column_config={
                "Cliente": st.column_config.SelectboxColumn(
                    "Cliente",
                    options=nomes_clientes,
                    help="Selecione o cliente (ou digite para filtrar)"
                ),
                "Quantidade de Cartelas": st.column_config.NumberColumn("Quantidade de Cartelas", min_value=0, step=1),
                "Valor Base": st.column_config.NumberColumn("Valor Base", format="%.2f", min_value=0.0, step=0.5),
                "Forma de Pagamento": st.column_config.SelectboxColumn("Forma de Pagamento", options=["Dinheiro","Cartão","Pix"]),
                "Pago": st.column_config.CheckboxColumn("Pago"),
                "Remover": st.column_config.CheckboxColumn("Remover")
            }
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Salvar alterações"):
                # Atualizar valor total com base em Qtd * Valor Base
                editados["Valor Total"] = editados["Quantidade de Cartelas"] * editados["Valor Base"]
                # Converter "Pago" para Sim/Não
                editados["Pago"] = editados["Pago"].apply(lambda x: "Sim" if x else "Não")

                # Remover linhas marcadas
                if "Remover" in editados.columns:
                    editados = editados[~editados["Remover"]].drop(columns=["Remover"], errors="ignore")

                if SHEETS_MANAGER.overwrite("pedidos", editados):
                    st.success("Alterações salvas com sucesso!")
                    st.rerun()
    else:
        st.info("Nenhum pedido registrado ainda.")


    if not df.empty:
        # Converter colunas numéricas
        df["Quantidade de Cartelas"] = pd.to_numeric(df["Quantidade de Cartelas"], errors="coerce").fillna(0)
        df["Valor Total"] = pd.to_numeric(df["Valor Total"], errors="coerce").fillna(0)

        # Adicionar coluna de mês/ano
        # (precisamos de uma coluna de Data no futuro; como ainda não temos, vamos usar a data de hoje no momento do registro)
        if "Data" not in df.columns:
            # Caso não exista, cria vazia (isso evita erro)
            df["Data"] = pd.Timestamp.today().strftime("%d-%m-%Y")

        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
        df["Ano-Mês"] = df["Data"].dt.to_period("M")

        resumo = df.groupby("Ano-Mês").agg({
            "Quantidade de Cartelas": "sum",
            "Valor Total": "sum"
        }).reset_index()

        resumo["Ano-Mês"] = resumo["Ano-Mês"].dt.strftime("%m/%Y")

        st.subheader("📊 Resumo Mensal de Pedidos")
        st.dataframe(resumo, use_container_width=True)

def aba_visualizar_pedidos():
    st.header("📂 Visualizar Pedidos Salvos")
    worksheets = SHEETS_MANAGER.list_worksheets()
    if "pedidos" not in worksheets:
        st.info("Nenhum pedido salvo ainda.")
        return
    df = SHEETS_MANAGER.get_dataframe("pedidos", columns=["Cliente","Quantidade de Cartelas","Valor Base","Valor Total","Forma de Pagamento","Pago"])
    if df.empty:
        st.info("Nenhum pedido encontrado.")
    else:
        st.dataframe(df, use_container_width=True)

def aba_relatorio_pedidos():
    st.header("📈 Relatório de Pedidos")

    df = SHEETS_MANAGER.get_dataframe(
        "pedidos",
        columns=["Data", "Cliente", "Quantidade de Cartelas", "Valor Base", "Valor Total", "Forma de Pagamento", "Pago"]
    )

    if df.empty:
        st.info("Nenhum pedido registrado ainda.")
        return

    # Converter e tratar dados
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df["Quantidade de Cartelas"] = pd.to_numeric(df["Quantidade de Cartelas"], errors="coerce").fillna(0)
    df["Valor Total"] = pd.to_numeric(df["Valor Total"], errors="coerce").fillna(0.0)

    # Filtros
    st.subheader("🔍 Filtros")
    col1, col2, col3 = st.columns(3)
    with col1:
        tipo_agrupamento = st.selectbox("Agrupar por:", ["Mês", "Semana", "Período Personalizado"])
    with col2:
        data_inicial = st.date_input("Data inicial", value=df["Data"].min().date())
    with col3:
        data_final = st.date_input("Data final", value=df["Data"].max().date())

    # Filtrar o DataFrame pelo período
    df_filtrado = df[(df["Data"] >= pd.Timestamp(data_inicial)) & (df["Data"] <= pd.Timestamp(data_final))]

    if df_filtrado.empty:
        st.warning("Nenhum pedido encontrado para o período selecionado.")
        return

    # Agrupamentos
    if tipo_agrupamento == "Mês":
        df_filtrado["Ano-Mês"] = df_filtrado["Data"].dt.to_period("M")
        resumo = df_filtrado.groupby("Ano-Mês").agg({
            "Quantidade de Cartelas": "sum",
            "Valor Total": "sum",
            "Cliente": "count"
        }).reset_index()
        resumo.columns = ["Período", "Total Cartelas", "Total Valor (R$)", "Nº de Pedidos"]
        resumo["Período"] = resumo["Período"].astype(str)

    elif tipo_agrupamento == "Semana":
        df_filtrado["Ano-Semana"] = df_filtrado["Data"].dt.strftime("%Y-%U")
        resumo = df_filtrado.groupby("Ano-Semana").agg({
            "Quantidade de Cartelas": "sum",
            "Valor Total": "sum",
            "Cliente": "count"
        }).reset_index()
        resumo.columns = ["Período", "Total Cartelas", "Total Valor (R$)", "Nº de Pedidos"]

    else:  # Período personalizado — mostra apenas o total consolidado
        resumo = pd.DataFrame([{
            "Período": f"{data_inicial.strftime('%d/%m/%Y')} a {data_final.strftime('%d/%m/%Y')}",
            "Total Cartelas": df_filtrado["Quantidade de Cartelas"].sum(),
            "Total Valor (R$)": df_filtrado["Valor Total"].sum(),
            "Nº de Pedidos": len(df_filtrado)
        }])

    st.subheader("📊 Resumo de Pedidos")
    st.dataframe(resumo, use_container_width=True)

    # Exibir gráfico
    if tipo_agrupamento in ["Mês", "Semana"] and len(resumo) > 1:
        st.subheader("📈 Evolução do Faturamento")
        st.line_chart(resumo.set_index("Período")["Total Valor (R$)"])


st.set_page_config(page_title="Gestão de Galinheiro e Entregas", layout="wide")
st.title("🐔 Gerenciamento de Granja (Cloud)")

menu = st.sidebar.radio("📚 Navegar entre seções:", [
    "📅 Produção Diária",
    "💰 Lançamento de Custos",
    "📊 Relatórios",
    "📆 Fechamento do Mês",
    "📋 Clientes",
    "🚚 Rota",
    "🧾 Pedidos",
    "📂 Ver Pedidos",
    "📈 Relatório de Pedidos"
])

if menu == "📅 Produção Diária":
    aba_producao()
elif menu == "💰 Lançamento de Custos":
    aba_custos()
elif menu == "📊 Relatórios":
    aba_relatorios()
elif menu == "📆 Fechamento do Mês":
    aba_fechamento()
elif menu == "📋 Clientes":
    aba_clientes()
elif menu == "🚚 Rota":
    aba_rota()
elif menu == "🧾 Pedidos":
    aba_pedidos()
elif menu == "📂 Ver Pedidos":
    aba_visualizar_pedidos()
elif menu == "📈 Relatório de Pedidos":
    aba_relatorio_pedidos()




