from xmlrpc.client import _binary
from docutils import Component
import streamlit as st
import pandas as pd
from sqlalchemy import DATETIME, create_engine, text
from streamlit import connection
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, session
from streamlit_option_menu import option_menu
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
import streamlit.components.v1 as components
import plotly.express as px
from datetime import datetime
from sqlalchemy import insert, select, text
from io import StringIO
from sqlalchemy import Column, Integer, String, TIMESTAMP, LargeBinary, func
import plotly.express as px



# Configurações da conexão
usuario = "pj"
senha = "loucoste9850053"
host = "localhost"
porta = "3306"
banco = "pet_store"

# String de conexão (usando pymysql como driver)
conexao = create_engine(f"mysql+pymysql://{usuario}:{senha}@{host}:{porta}/{banco}")

Base = declarative_base()
Session = sessionmaker(bind=conexao)
session = Session()
SessionLocal = sessionmaker(bind=conexao)

def importar_dados_compra():
    query = "SELECT * FROM compra"
    compras = pd.read_sql(query, conexao)
    compras['compra'] = compras['compra'].astype(str)
    compras['compra'] = pd.to_datetime(compras['compra'])
    compras['Ano'] = compras['compra'].dt.year
    # Mapeamento mês → nome do mês em português
    mapa_meses = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    compras['Mes'] = compras['compra'].dt.month.map(mapa_meses)
    

    
    return compras

def limpar_dados_loja():
    st.session_state["dados_loja"] = pd.DataFrame()
    st.session_state["produto_nome"] = None
    st.session_state["quantidade"] = 1


# Configuração da página
if "page_config_set" not in st.session_state:
    st.set_page_config(page_title="Login", layout="centered")
    st.session_state["page_config_set"] = True

# Criar um estado de sessão para login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Função para verificar login e obter nível de acesso
def check_login(username, password):
    query = f"""
        SELECT nivel FROM usuarios 
        WHERE username = '{username}' AND password = '{password}'
    """
    df = pd.read_sql(query, conexao)
    if not df.empty:
        return df.iloc[0]["nivel"]
    return None

# Interface do login
if not st.session_state.logged_in:
    st.title("Tela de Login ao Sistema")

    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    if st.button("Login"):
        nivel = check_login(username, password)
        if nivel:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.nivel = nivel
            st.session_state["page_config_set"] = False
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos!")

# Interface após login
if st.session_state.logged_in:
    st.set_page_config(page_title="Loja Pet Store", layout="wide")

    # Inicializar DataFrame de compras na sessão, se ainda não existir
    if "dados_loja" not in st.session_state:
        st.session_state["dados_loja"] = pd.DataFrame(columns=["Produto", "Quantidade", "Preço Unitário", "Total"])
    
    # Sidebar com saudação
    st.sidebar.title(f"Bem-vindo, {st.session_state.username}!")
    st.sidebar.markdown(f"**Nível de acesso:** {st.session_state.nivel}")
        
    if st.session_state.nivel == "admin":
        menu_opcoes = ["Loja", "Cadastro de Produto", "Compras do Dia", "Relatorio de Compras", "Administração"]
    elif st.session_state.nivel == "gerente":
        menu_opcoes = ["Loja","Cadastro de Produto", "Compras do Dia", "Relatorio de Compras", "Definição"]
    elif st.session_state.nivel == "atendente":
        menu_opcoes = ["Loja", "Compras do Dia", "Definição"]
    
    # Menu lateral
    with st.sidebar:
        selected = option_menu(
            menu_title="Menu Principal",
            options=menu_opcoes,
            menu_icon="cast",
            default_index=0
        )
    
    # Páginas conforme menu
    if selected == "Loja":
        st.title("Loja")
        st.write("Bem-vindo")
        query = "SELECT * FROM cadastro_produto"
        produto = pd.read_sql(query, conexao)

        # criar colunas
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            produto_nome = st.selectbox("Produto", produto['produto'].tolist())
            
        with col2:
            quantidade = st.number_input("Quantidade", min_value=1, step=1)

        with col3:
            if st.button("Adicionar"):
                linha = produto[produto['produto'] == produto_nome].iloc[0]
                preco_unitario = linha['preco']
                quantidade_em_estoque = linha['quantidade']

                if quantidade > quantidade_em_estoque:
                    st.warning(f"❌ Estoque insuficiente! Apenas {quantidade_em_estoque} unidades disponíveis.")
                else:
                    total = preco_unitario * quantidade
                    novo_dado = {
                        "Produto": produto_nome,
                        "Quantidade": quantidade,
                        "Preço Unitário": preco_unitario,
                        "Total": total
                    }

                    st.session_state["dados_loja"] = pd.concat(
                        [st.session_state["dados_loja"], pd.DataFrame([novo_dado])],
                        ignore_index=True
                    )

                    st.success(f"✅ {quantidade}x {produto_nome} adicionado(s) - Total: R$ {total:.2f}")

            if st.button("🧹 Limpar Dados"):
                limpar_dados_loja()
                st.success("🧽 Campos e lista de produtos limpos!")

        # Se houver itens, exibe editor
        if not st.session_state["dados_loja"].empty:
            st.subheader("🛒 Itens adicionados ao pedido (edite quantidades se desejar):")

            # 1) Mostra o DataEditor, permitindo editar apenas "Quantidade"
            dados_editados = st.data_editor(
                st.session_state["dados_loja"],
                column_config={
                    "Produto": st.column_config.Column(disabled=True),
                    "Preço Unitário": st.column_config.Column(disabled=True),
                    "Total": st.column_config.Column(disabled=True),
                },
                use_container_width=True,
                hide_index=True,
                key="editor_dados_loja"
            )

            # 2) Verifica se a coluna "Quantidade" mudou
            quant_original = st.session_state["dados_loja"]["Quantidade"]
            quant_editada = dados_editados["Quantidade"]

            if not quant_editada.equals(quant_original):
                # 3) Recalcula "Total" com base na nova quantidade
                dados_editados["Total"] = dados_editados["Quantidade"] * dados_editados["Preço Unitário"]

                # 4) Atualiza o state com o DataFrame novo
                st.session_state["dados_loja"] = dados_editados
                st.success("✏️ Quantidades atualizadas e totais recalculados!")

            # 5) Exibe o total geral atualizado
            total_geral = st.session_state["dados_loja"]["Total"].sum()
            st.markdown(f"### 💰 Total geral: R$ {total_geral:.2f}")
        
                                    
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:

                if not st.session_state["dados_loja"].empty:
                    st.subheader("🧾 Finalizar Compra")

                    forma_pagamento = st.selectbox("Forma de Pagamento", ["Dinheiro", "Cartão", "PIX"])
                    valor_recebido = 0.0
                    troco = 0.0
                    total_geral = st.session_state["dados_loja"]["Total"].sum()

                    if forma_pagamento == "Dinheiro":
                        valor_recebido = st.number_input("Valor recebido (R$)", min_value=0.0, step=0.5, format="%.2f")
                        troco = valor_recebido - total_geral
                        if valor_recebido > 0:
                            if troco < 0:
                                st.warning(f"💸 Valor insuficiente! Faltam R$ {abs(troco):.2f}")
                            else:
                                st.success(f"Troco: R$ {troco:.2f}")

                    if st.button("Finalizar Compra"):
                        if forma_pagamento == "Dinheiro" and valor_recebido < total_geral:
                            st.error("🚫 Valor recebido insuficiente para pagamento em dinheiro.")
                        else:
                            dados = st.session_state["dados_loja"]

                            with conexao.begin() as conn:
                                # Dentro do bloco with conexao.begin()
                                ids_compra = []
                                # 👉 1. Inserir a venda e pegar o ID (número do recibo)
                                insert_venda = text("""
                                    INSERT INTO venda (data, usuario, forma_pagamento, valor_recebido, troco)
                                    VALUES (NOW(), :usuario, :forma_pagamento, :valor_recebido, :troco)
                                """)
                                conn.execute(insert_venda, {
                                    "usuario": st.session_state.username,
                                    "forma_pagamento": forma_pagamento,
                                    "valor_recebido": valor_recebido if forma_pagamento == "Dinheiro" else None,
                                    "troco": troco if forma_pagamento == "Dinheiro" else None
                                })

                                numero_recibo = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()  

                                for _, row in dados.iterrows():
                                    insert_query = text("""
                                        INSERT INTO compra (produto, quantidade, preco_unitario, total, forma_pagamento, id_venda)
                                        VALUES (:produto, :quantidade, :preco_unitario, :total, :forma_pagamento, :id_venda)
                                    """)
                                    conn.execute(insert_query, {
                                        "produto": row["Produto"],
                                        "quantidade": row["Quantidade"],
                                        "preco_unitario": row["Preço Unitário"],
                                        "total": row["Total"],
                                        "forma_pagamento": forma_pagamento,
                                        "id_venda": numero_recibo
                                    })
                                     # Atualizar o estoque
                                    atualizar_estoque = text("""
                                        UPDATE cadastro_produto
                                        SET quantidade = quantidade - :quantidade
                                        WHERE produto = :produto
                                    """)
                                    conn.execute(atualizar_estoque, {
                                        "quantidade": row["Quantidade"],
                                        "produto": row["Produto"]
                                    })
                                    #Salva o último id gerado
                                    last_id = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()
                                    ids_compra.append(last_id)

                                numero_recibo = ids_compra[-1] if ids_compra else None

                            st.success(f"✅ Compra finalizada com pagamento em {forma_pagamento}. Dados salvos no banco!")
                            st.session_state["dados_loja"] = pd.DataFrame()

                            if not dados.empty:
                                data_compra = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                                recibo_html = f"""
                                <style>
                                @media print {{
                                    @page {{
                                        size: 80mm auto;
                                        margin: 0;
                                    }}
                                    body {{
                                        margin: 0;
                                        padding: 0;
                                    }}
                                    .recibo {{
                                        width: 50mm;
                                        font-size: 12px;
                                        padding: 0;
                                        margin: 0;
                                    }}
                                    button {{
                                        display: none; /* Esconde o botão na impressão */
                                    }}
                                }}
                                </style>

                                <div class="recibo" style="font-family: Arial, sans-serif; padding: 10px; width: 295px; border: 1px solid #ccc;">
                                    <h2 style="text-align: center;">🐾 Pet Store - Recibo de Compra</h2>
                                    <hr>
                                    <p><strong>Data:</strong> {data_compra}</p>
                                    <p><strong>Número do Recibo:</strong> {numero_recibo}</p>
                                    <p><strong>Usuário:</strong> {st.session_state.username}</p>
                                    <p><strong>Forma de Pagamento:</strong> {forma_pagamento}</p>
                                    {f"<p><strong>Valor Recebido:</strong> R$ {valor_recebido:.2f}</p><p><strong>Troco:</strong> R$ {troco:.2f}</p>" if forma_pagamento == "Dinheiro" else ""}
                                    <hr>
                                    <table style="width:100%; border-collapse: collapse;">
                                        <tr>
                                            <th style="text-align:left;">Produto</th>
                                            <th style="text-align:right;">Qtd</th>
                                            <th style="text-align:right;">Preço</th>
                                            <th style="text-align:right;">Total</th>
                                        </tr>
                                        {''.join([
                                            f"<tr><td>{row['Produto']}</td><td style='text-align:right;'>{row['Quantidade']}</td><td style='text-align:right;'>R$ {row['Preço Unitário']:.2f}</td><td style='text-align:right;'>R$ {row['Total']:.2f}</td></tr>"
                                            for _, row in dados.iterrows()
                                        ])}
                                    </table>
                                    <hr>
                                    <h3 style="text-align: right;">Total Geral: R$ {total_geral:.2f}</h3>
                                    <br>
                                    <p style="text-align: center;">Obrigado pela sua compra! 🐶🐱</p>
                                    <br>
                                    <div style="text-align: center;">
                                        <button onclick="window.print()">🖨️ Imprimir Recibo</button>
                                    </div>
                                </div>
                                """
                                st.markdown("### 🧾 Recibo da Compra")
                                components.html(recibo_html, height=800, scrolling=False)
                            
    if selected == "Cadastro de Produto":
        st.title("Cadastro")
        menu = st.radio(
        "Seleção", ["Cadastro", "Atualização"], horizontal=True
        )

        #campo de Cadastro
        if menu == "Cadastro":

            # Formulário de cadastro
            with st.form("form_cadastro_produto"):
                nome_produto = st.text_input("Nome do Produto")
                preco_produto = st.number_input("Preço (R$)", min_value=0.0, step=0.01, format="%.2f")
                estoque_inicial = st.number_input("Estoque Inicial", min_value=0, step=1)
                submit_produto = st.form_submit_button("Cadastrar Produto")

                if submit_produto:
                    if not nome_produto.strip():
                        st.warning("⚠️ Nome do produto não pode estar vazio.")
                    elif preco_produto <= 0:
                        st.warning("⚠️ O preço deve ser maior que zero.")
                    else:
                        try:
                            with conexao.begin() as conn:
                                insert_query = text("""
                                    INSERT INTO cadastro_produto (produto, preco, quantidade)
                                    VALUES (:produto, :preco, :quantidade)
                                """)
                                conn.execute(insert_query, {
                                    "produto": nome_produto,
                                    "preco": preco_produto,
                                    "quantidade": estoque_inicial,
                                    
                                })
                            st.success(f"✅ Produto '{nome_produto}' cadastrado com sucesso!")
                        except Exception as e:
                            st.error(f"❌ Erro ao cadastrar produto: {e}")
                        
                
            
            st.markdown("---")
            query = "SELECT * FROM cadastro_produto"
            cadastro_produto = pd.read_sql(query, conexao)
            #cadastro_produto.set_index('id_prod', inplace=True)                   
            #st.dataframe(cadastro_produto)
            st.data_editor(
                cadastro_produto[["id_prod", "produto", "preco", "quantidade"]],
                column_config={
                    "id_prod": st.column_config.NumberColumn(width="small"),
                    "produto": st.column_config.TextColumn(width="medium"),
                    "preco": st.column_config.NumberColumn(width="small"),
                    "quantidade": st.column_config.NumberColumn(width="small")
                },
                use_container_width=False,
                hide_index=True,
                disabled=True  # Só leitura
            )
                    
        #campo de Atualização
        if menu == "Atualização":
            query = "SELECT * FROM cadastro_produto"
            df_produtos = pd.read_sql(query, conexao)
            #pro_id = df_produtos["id_prod"].tolist()
            pro_map = {f"{row['produto']} ({row['preco']})": row["id_prod"] for _, row in df_produtos.iterrows()}

            selecionado = st.selectbox("Selecionar Produto", list(pro_map.keys()))
            id_selecionado = pro_map[selecionado]

            # Buscar dados do usuário selecionado
            dados_produto = df_produtos[df_produtos["id_prod"] == id_selecionado].iloc[0]
            
            with st.form("form_editar_produto"):
                novo_produto = st.text_input("Novo nome do produto", value=dados_produto["produto"])
                nova_preco = st.text_input("Novo valor", value=dados_produto["preco"])
                nova_quantidade = st.text_input("Nova quantidade", value=dados_produto["quantidade"])
                col1, col2 = st.columns(2)
                with col1:
                    atualizar = st.form_submit_button("Atualizar")
                with col2:
                    deletar = st.form_submit_button("Excluir", type="primary")
                
                if atualizar:
                    try:
                        if nova_preco:
                            update_query = f"""
                                UPDATE cadastro_produto 
                                SET produto = '{novo_produto}', preco = '{nova_preco}', quantidade = '{nova_quantidade}'
                                WHERE id_prod = {id_selecionado}
                            """
                        else:
                            update_query = f"""
                                UPDATE cadastro_produto 
                                SET produto = '{novo_produto}', preco = '{nova_preco}'
                                WHERE id_prod = {id_selecionado}
                            """
                        session = SessionLocal()
                        try:
                            session.execute(text(update_query))
                            session.commit()
                            #st.success("Produto atualizado com sucesso!")
                        except Exception as e:
                            session.rollback()
                            st.error(f"Erro ao atualizar: {e}")
                        finally:
                            session.close()
                            st.success("Produto atualizado com sucesso!")
                            #st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar: {e}")
                
                if deletar:
                    try:
                        session = SessionLocal()
                        try:
                            session.execute(text(f"DELETE FROM cadastro_produto WHERE id_prod = {id_selecionado}"))
                            session.commit()
                            #st.success("Produto excluído com sucesso!")
                        except Exception as e:
                            session.rollback()
                            st.error(f"Erro ao excluir: {e}")
                        finally:
                            session.close()
                            st.success("Produto excluído com sucesso!")
                            #st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir: {e}")

    if selected == "Compras do Dia":
        st.title("Compras do Dia")
        st.write("Bem-vindo")
        query = "SELECT * FROM compra"
        compra = pd.read_sql(query, conexao)

        st.sidebar.header("Pesquisar compra")
        id_venda = st.sidebar.multiselect(
            "Inserir Nº Recibo: ",
            options=compra['id_venda'].unique(),
        )

        geral_selection = compra.query("`id_venda` == @id_venda")
        
        
        if 'Excluir' not in geral_selection.columns:
            geral_selection['Excluir'] = False
        
        # 🔐 Bloqueia edição da coluna "Excluir" se for atendente
        def usuario_tem_permissao(permissao):
            nivel = st.session_state.nivel.lower()
            if permissao == "excluir":
                return nivel in ["admin", "gerente"]
            return False

        pode_excluir = usuario_tem_permissao("excluir")

        
        # Editor com edição restrita à coluna 'Excluir'
        edit_geral_selection = st.data_editor(
            geral_selection,
            column_config={
                "id_compra": st.column_config.NumberColumn(disabled=True),
                "id_venda": st.column_config.NumberColumn(disabled=True),
                "produto": st.column_config.TextColumn(disabled=True),
                "quantidade": st.column_config.NumberColumn(disabled=True),
                "compra": st.column_config.DatetimeColumn(disabled=True),
                "Excluir": st.column_config.CheckboxColumn("Excluir", default=False, disabled=not pode_excluir),
                },
            use_container_width=True,
            key="editor"
        )
        edit_geral_selection.set_index('id_compra', inplace=True)
        # Após edição, submeter exclusão
        if pode_excluir:
            if st.button("Submeter exclusão"):
                excluir_ids = edit_geral_selection[edit_geral_selection["Excluir"] == True].index.tolist()

                if excluir_ids:
                    # Executa exclusão no banco
                    with conexao.connect() as conn:
                        from sqlalchemy import text
                        stmt = text("DELETE FROM compra WHERE id_compra IN :ids")
                        conn.execute(stmt, {"ids": tuple(excluir_ids)})
                        conn.commit()

                    # Atualiza o DataFrame removendo as linhas excluídas
                    geral_selection = edit_geral_selection[edit_geral_selection["Excluir"] == False].drop(columns=["Excluir"])
                    st.success(f"{len(excluir_ids)} linha(s) excluída(s) com sucesso!")

                    # Reexibir DataFrame atualizado
                    st.dataframe(geral_selection)
                else:
                    st.warning("Nenhuma linha marcada para exclusão.")
        else:
            st.info("Você não tem permissão para excluir registros.")
        
    if selected == "Relatorio de Compras":
        st.title("Relatorio de Compras")
        compras = importar_dados_compra()
        
        #definir campos de pesquisa para tipo de leitura
        st.sidebar.header("Definir Ano:")
        ano = st.sidebar.multiselect(
            "Definir Contador",
            options=compras['Ano'].unique(),

        )
        geral_selection = compras.query(
        "`Ano` == @ano"
            )
        st.markdown(" ")

        st.subheader("Compras por Formas de Pagamento")

        #por formato de compra
        #tabela dinamica
        tabela = pd.pivot_table(
            geral_selection,
            values='total',
            index='forma_pagamento',
            columns='Mes',
            aggfunc='sum',
            fill_value=0
        )
        # Adiciona a coluna "Total" com a soma das colunas (por linha)
        tabela['Total'] = tabela.sum(axis=1)

        #tabela dinamica
        tabela2 = pd.pivot_table(
            geral_selection,
            values='total',
            index='forma_pagamento',
            columns='Mes',
            aggfunc='count',
            fill_value=0
        )
        # Adiciona a coluna "Total" com a soma das colunas (por linha)
        tabela2['Total'] = tabela2.sum(axis=1)

        #inserir em cada coluna a tabela dinamica e o grafico por forma de pagamento
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Valor Comprado (ECV)")
            st.dataframe(tabela)
            # Transforma o índice em coluna normal
            tabela_reset = tabela.reset_index()

            fig = px.bar(
                tabela_reset,
                x='forma_pagamento',
                y='Total',
                title='Compra por Forma de Pagamento',
                width=500,   # Largura menor
                height=300,   # Altura menor
                color_discrete_sequence=["#1D32A8"]
            )

            st.plotly_chart(fig, use_container_width=False)
           
        with col2:
            st.subheader("Quantidade Comprado")
            st.dataframe(tabela2)
            tabela2_reset = tabela2.reset_index()
            fig2 = px.bar(
                tabela2_reset,
                x='forma_pagamento',
                y='Total',
                title='Quantidade por Forma de Pagamento',
                width=500,   # Largura menor
                height=300,   # Altura menor
                color_discrete_sequence=["#D31C1C"]
            )

            st.plotly_chart(fig2, use_container_width=False)
        
        st.markdown(" ")

        st.subheader("Compras por Produtos")

        st.markdown(" ")

        #por produtos comprados
        #tabela dinamica
        tabela3 = pd.pivot_table(
            geral_selection,
            values='total',
            index='produto',
            columns='Mes',
            aggfunc='sum',
            fill_value=0
        )
        # Adiciona a coluna "Total" com a soma das colunas (por linha)
        tabela3['Total'] = tabela3.sum(axis=1)        

        #tabela dinamica
        tabela4 = pd.pivot_table(
            geral_selection,
            values='total',
            index='produto',
            columns='Mes',
            aggfunc='count',
            fill_value=0
        )
        # Adiciona a coluna "Total" com a soma das colunas (por linha)
        tabela4['Total'] = tabela4.sum(axis=1)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Valor Produto Comprado (ECV)")
            st.dataframe(tabela3)

            # Transforma o índice em coluna normal
            tabela3_reset = tabela3.reset_index()

            fig = px.bar(
                tabela3_reset,
                x='produto',
                y='Total',
                title='Valor de Compra Produto',
                width=500,   # Largura menor
                height=300,   # Altura menor
                color_discrete_sequence=["#1D32A8"]
            )

            st.plotly_chart(fig, use_container_width=False)
 
        with col2:
            st.subheader("Quantidade Produto Comprado")
            st.dataframe(tabela4)
            # Transforma o índice em coluna normal
            tabela4_reset = tabela4.reset_index()

            fig = px.bar(
                tabela4_reset,
                x='produto',
                y='Total',
                title='Quantidade de Compra',
                width=500,   # Largura menor
                height=300,   # Altura menor
                color_discrete_sequence=["#A81723"]
            )

            st.plotly_chart(fig, use_container_width=False)

    elif selected == "Administração":
        st.title("Painel Administrativo")
        
        st.subheader("📋 Lista de Usuários")

        # Consulta todos os usuários
        df_usuarios = pd.read_sql("SELECT id, username, password, nivel FROM usuarios", conexao)
        st.dataframe(df_usuarios, hide_index=True)
        st.markdown("---")
        st.subheader("➕ Criar Novo Usuário")
        with st.form("form_criar_usuario"):
            novo_user = st.text_input("Nome de usuário")
            nova_senha = st.text_input("Senha", type="password")
            novo_nivel = st.selectbox("Nível de acesso", ["admin", "gerente", "atendente"])
            submitted = st.form_submit_button("Criar")
            if submitted:
                try:
                    query = text("""
                        INSERT INTO usuarios (username, password, nivel) 
                        VALUES (:username, :password, :nivel)
                    """)
                    session = SessionLocal()
                    try:
                        session.execute(query, {"username": novo_user, "password": nova_senha, "nivel": novo_nivel})
                        session.commit()
                        st.success(f"Usuário '{novo_user}' criado com sucesso!")
                    except Exception as e:
                        session.rollback()
                        st.error(f"Erro ao criar usuário: {e}")
                    finally:
                        session.close()
                    st.success(f"Usuário '{novo_user}' criado com sucesso!")
                    #st.experimental_rerun()
                except Exception as e:
                    st.error(f"Erro ao criar usuário: {e}")
        st.markdown("---")
        st.subheader("✏️ Editar ou Excluir Usuário")

        # Selecionar usuário para edição
        user_ids = df_usuarios["id"].tolist()
        user_map = {f"{row['username']} ({row['nivel']})": row["id"] for _, row in df_usuarios.iterrows()}
        
        selecionado = st.selectbox("Selecionar usuário", list(user_map.keys()))
        id_selecionado = user_map[selecionado]

        # Buscar dados do usuário selecionado
        dados_user = df_usuarios[df_usuarios["id"] == id_selecionado].iloc[0]
    
        with st.form("form_editar_usuario"):
            novo_username = st.text_input("Novo nome de usuário", value=dados_user["username"])
            nova_senha_edit = st.text_input("Nova senha (deixe em branco para não alterar)", type="password")
            novo_nivel_edit = st.selectbox("Novo nível", ["admin", "gerente", "atendente"], index=["admin", "gerente", "atendente"].index(dados_user["nivel"]))
            
            col1, col2 = st.columns(2)
            with col1:
                atualizar = st.form_submit_button("Atualizar")
            with col2:
                deletar = st.form_submit_button("Excluir", type="primary")

            if atualizar:
                try:
                    if nova_senha_edit:
                        update_query = f"""
                            UPDATE usuarios 
                            SET username = '{novo_username}', password = '{nova_senha_edit}', nivel = '{novo_nivel_edit}'
                            WHERE id = {id_selecionado}
                        """
                    else:
                        update_query = f"""
                            UPDATE usuarios 
                            SET username = '{novo_username}', nivel = '{novo_nivel_edit}'
                            WHERE id = {id_selecionado}
                        """
                    session = SessionLocal()
                    try:
                        session.execute(text(update_query))
                        session.commit()
                        st.success("Usuário atualizado com sucesso!")
                    except Exception as e:
                        session.rollback()
                        st.error(f"Erro ao atualizar: {e}")
                    finally:
                        session.close()
                        st.success("Usuário atualizado com sucesso!")
                        #st.experimental_rerun()
                except Exception as e:
                    st.error(f"Erro ao atualizar: {e}")

            if deletar:
                try:
                    session = SessionLocal()
                    try:
                        session.execute(text(f"DELETE FROM usuarios WHERE id = {id_selecionado}"))
                        session.commit()
                        st.success("Usuário excluído com sucesso!")
                    except Exception as e:
                        session.rollback()
                        st.error(f"Erro ao excluir: {e}")
                    finally:
                        session.close()
                        st.success("Usuário excluído com sucesso!")
                        #st.experimental_rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")

    elif selected == "Definição":
        st.title("Configuração de Conta")
        st.subheader("Alterar Senha da Conta")

        # Recuperar nome do usuário logado
        username_logado = st.session_state.username

        with st.form("alterar_senha_form"):
            senha_atual = st.text_input("Senha Atual", type="password")
            nova_senha = st.text_input("Nova Senha", type="password")
            confirmar_senha = st.text_input("Confirmar Nova Senha", type="password")
            submitted = st.form_submit_button("Alterar Senha")

            if submitted:
                # Verificar se senha atual está correta
                query = text("SELECT password FROM usuarios WHERE username = :username")
                session = SessionLocal()
                try:
                    result = session.execute(query, {"username": username_logado}).fetchone()
                    if result and result[0] == senha_atual:
                        if nova_senha == confirmar_senha:
                            update_query = text("UPDATE usuarios SET password = :nova WHERE username = :username")
                            session.execute(update_query, {"nova": nova_senha, "username": username_logado})
                            session.commit()
                            st.success("Senha alterada com sucesso!")
                        else:
                            st.error("A nova senha e a confirmação não coincidem.")
                    else:
                        st.error("Senha atual incorreta.")
                except Exception as e:
                    st.error(f"Erro ao alterar a senha: {e}")
                finally:
                    session.close()

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
    
    
