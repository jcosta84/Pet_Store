import datetime
import customtkinter as ctk
from tkinter import messagebox, filedialog, ttk
from sqlalchemy import create_engine, text
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
import tkinter as tk


# Configurações do banco
usuario = "pj"
senha = "loucoste9850053"
host = "localhost"
porta = "3306"
banco = "pet_store"
conexao = create_engine(f"mysql+pymysql://{usuario}:{senha}@{host}:{porta}/{banco}")



# ----------------- FRAME LOJA -----------------
class LojaFrame(ctk.CTkFrame):
    def __init__(self, parent, username):
        super().__init__(parent)
        self.username = username
        self.carrinho = []

        self.produtos_df = pd.read_sql("SELECT * FROM cadastro_produto", conexao)

        self.produto_var = ctk.StringVar()
        self.quantidade_var = ctk.IntVar(value=1)

        ctk.CTkLabel(self, text="Loja - Adicionar Produtos", font=("Arial", 18)).pack(pady=10)
        ttk.Combobox(self, values=self.produtos_df['produto'].tolist(), textvariable=self.produto_var).pack(pady=5)
        ctk.CTkEntry(self, textvariable=self.quantidade_var, placeholder_text="Quantidade").pack(pady=5)
        ctk.CTkButton(self, text="Adicionar ao Carrinho", command=self.adicionar_ao_carrinho).pack(pady=10)

        self.tree = ttk.Treeview(self, columns=("Produto", "Qtd", "Preço", "Total"), show="headings")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
        self.tree.pack(pady=10, fill="x")

        self.total_label = ctk.CTkLabel(self, text="Total: R$ 0.00", font=("Arial", 14))
        self.total_label.pack(pady=5)

        self.pagamento = ttk.Combobox(self, values=["Dinheiro", "Cartão", "PIX"])
        self.pagamento.set("Dinheiro")
        self.pagamento.pack(pady=5)

        self.valor_recebido = ctk.CTkEntry(self, placeholder_text="Valor Recebido")
        self.valor_recebido.pack(pady=5)

        self.troco_label = ctk.CTkLabel(self, text="Troco: R$ 0.00", font=("Arial", 14))
        self.troco_label.pack(pady=5)        
        

        ctk.CTkButton(self, text="Finalizar Compra", command=self.finalizar_compra).pack(pady=10)
        self.troco_label.configure(text="Troco: R$ 0.00")
        self.valor_recebido.delete(0, 'end')

    def adicionar_ao_carrinho(self):
        nome = self.produto_var.get()
        try:
            qtd = int(self.quantidade_var.get())
        except:
            messagebox.showerror("Erro", "Quantidade inválida.")
            return

        linha = self.produtos_df[self.produtos_df['produto'] == nome]
        if linha.empty:
            messagebox.showerror("Erro", "Produto não encontrado.")
            return

        preco = float(linha['preco'].values[0])
        total = preco * qtd
        self.carrinho.append({"Produto": nome, "Qtd": qtd, "Preço": preco, "Total": total})
        self.atualizar_tabela()

    def atualizar_tabela(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        total_geral = 0
        for item in self.carrinho:
            self.tree.insert("", "end", values=(
                item['Produto'],
                item['Qtd'],
                f"R$ {item['Preço']:.2f}",
                f"R$ {item['Total']:.2f}"
            ))
            total_geral += item['Total']
        self.total_label.configure(text=f"Total: R$ {total_geral:.2f}")

    def finalizar_compra(self):
        if not self.carrinho:
            messagebox.showwarning("Aviso", "Carrinho vazio.")
            return

        forma = self.pagamento.get()
        total = sum(i['Total'] for i in self.carrinho)

        recebido = None
        troco = None

        if forma == "Dinheiro":
            try:
                recebido = float(self.valor_recebido.get())
            except:
                messagebox.showwarning("Erro", "Informe o valor recebido.")
                return
            troco = recebido - total
            if troco < 0:
                messagebox.showwarning("Erro", f"Valor insuficiente. Faltam R$ {abs(troco):.2f}")
                return
            self.troco_label.configure(text=f"Troco: R$ {troco:.2f}")

        try:
            with conexao.begin() as conn:
                conn.execute(text("""
                    INSERT INTO venda (data, usuario, forma_pagamento, valor_recebido, troco)
                    VALUES (NOW(), :usuario, :forma, :recebido, :troco)
                """), {"usuario": self.username, "forma": forma, "recebido": recebido, "troco": troco})

                id_venda = conn.execute(text("SELECT LAST_INSERT_ID()")).scalar()

                for item in self.carrinho:
                    conn.execute(text("""
                        INSERT INTO compra (produto, quantidade, preco_unitario, total, forma_pagamento, id_venda)
                        VALUES (:p, :q, :pu, :t, :f, :idv)
                    """), {
                        "p": item['Produto'],
                        "q": item['Qtd'],
                        "pu": item['Preço'],
                        "t": item['Total'],
                        "f": forma,
                        "idv": id_venda
                    })

            carrinho_copia = self.carrinho.copy()
            self.mostrar_recibo(total, recebido, troco, forma, carrinho_copia)
            self.troco_label.configure(text="Troco: R$ 0.00")
            self.carrinho.clear()
            self.atualizar_tabela()
            
            self.valor_recebido.delete(0, 'end')
            self.carrinho.clear()
        except Exception as e:
            messagebox.showerror("Erro", str(e))
    
    def mostrar_recibo(self, total, recebido, troco, forma, carrinho):
        recibo_janela = ctk.CTkToplevel(self)
        recibo_janela.title("🧾 Recibo de Compra")
        recibo_janela.geometry("300x500")
        recibo_janela.update_idletasks()
        recibo_janela.minsize(302, recibo_janela.winfo_reqheight())
        recibo_janela.resizable(False, False)

        frame = ctk.CTkFrame(recibo_janela)
        frame.pack(padx=10, pady=10, fill="both", expand=True)

        data = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        ctk.CTkLabel(frame, text="🐾 Pet Store", font=("Arial", 16)).pack()
        ctk.CTkLabel(frame, text="Recibo de Compra", font=("Arial", 14)).pack()
        ctk.CTkLabel(frame, text=f"Data: {data}", font=("Arial", 10)).pack(pady=2)
        ctk.CTkLabel(frame, text=f"Usuário: {self.username}", font=("Arial", 10)).pack(pady=2)
        ctk.CTkLabel(frame, text=f"Pagamento: {forma}", font=("Arial", 10)).pack(pady=2)

        if forma == "Dinheiro":
            ctk.CTkLabel(frame, text=f"Recebido: R$ {recebido:.2f}", font=("Arial", 10)).pack()
            ctk.CTkLabel(frame, text=f"Troco: R$ {troco:.2f}", font=("Arial", 10)).pack()
            self.troco_label.configure(text=f"Troco: R$ {troco:.2f}")
            messagebox.showinfo("Troco", f"Troco a devolver: R$ {troco:.2f}")

        ctk.CTkLabel(frame, text="-------------------------------").pack(pady=5)

        # Cabeçalho dos itens
        ctk.CTkLabel(frame, text="Produto        Qtd  Total", font=("Consolas", 10)).pack(anchor="w")

        for item in carrinho:
            texto = f"{item['Produto'][:12]:12} {item['Qtd']:>3}  R$ {item['Total']:.2f}"
            ctk.CTkLabel(frame, text=texto, font=("Consolas", 10)).pack(anchor="w")

        ctk.CTkLabel(frame, text="-------------------------------").pack(pady=5)
        ctk.CTkLabel(frame, text=f"Total Geral: R$ {total:.2f}", font=("Arial", 12)).pack(pady=2)
        ctk.CTkLabel(frame, text="Obrigado pela sua compra! 🐶🐱", font=("Arial", 10)).pack(pady=10)

        ctk.CTkButton(frame, text="🖨️ Imprimir Recibo", command=lambda: self.imprimir_recibo_txt(total, recebido, troco, forma, carrinho)).pack(pady=5)
        ctk.CTkButton(frame, text="Fechar", command=recibo_janela.destroy).pack(pady=5)
    
    def imprimir_recibo_txt(self, total, recebido, troco, forma, carrinho):
        from tempfile import NamedTemporaryFile
        import os

        data = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        conteudo = []
        conteudo.append("🐾 PET STORE")
        conteudo.append("RECIBO DE COMPRA")
        conteudo.append(f"Data: {data}")
        conteudo.append(f"Usuário: {self.username}")
        conteudo.append(f"Pagamento: {forma}")
        if forma == "Dinheiro":
            conteudo.append(f"Valor Recebido: R$ {recebido:.2f}")
            conteudo.append(f"Troco: R$ {troco:.2f}")
        conteudo.append("-" * 32)
        conteudo.append(f"{'Produto':<12}{'Qtd':>4}  {'Total':>8}")
        for item in carrinho:
            linha = f"{item['Produto'][:12]:<12}{item['Qtd']:>4}  R$ {item['Total']:>6.2f}"
            conteudo.append(linha)
            
        conteudo.append("-" * 32)
        conteudo.append(f"TOTAL GERAL: R$ {total:.2f}")
        conteudo.append("Obrigado pela compra! 🐶🐱")

        texto = "\n".join(conteudo)

        # Cria arquivo temporário
        with NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as f:
            f.write(texto)
            caminho = f.name

        try:
            with NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as f:
                f.write(texto)
                caminho = f.name
            os.startfile(caminho, "print")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao imprimir: {e}")

        self.troco_label.configure(text="Troco: R$ 0.00")
        self.valor_recebido.delete(0, 'end')

   
# ----------------- FRAME RELATÓRIO -----------------
class RelatorioFrame(ctk.CTkFrame):
    def __init__(self, parent, _):
        super().__init__(parent)
        ctk.CTkLabel(self, text="📊 Relatório de Compras", font=("Arial", 20)).pack(pady=10)

        # Consulta geral
        self.df = pd.read_sql("""
            SELECT c.*, v.data
            FROM compra c
            JOIN venda v ON c.id_venda = v.id_venda
        """, conexao)

        if self.df.empty:
            messagebox.showinfo("Informação", "Não há dados de compras no sistema.")
            return

        self.df['data'] = pd.to_datetime(self.df['data'])
        self.df['Ano'] = self.df['data'].dt.year
        self.df['Mes'] = self.df['data'].dt.month_name()

        # Seleção múltipla de anos
        anos = sorted(self.df['Ano'].unique(), reverse=True)
        self.anos_var = tk.StringVar(value=[str(anos[0])])
        ctk.CTkLabel(self, text="Selecionar Ano(s):", font=("Arial", 14)).pack()
        self.anos_listbox = tk.Listbox(self, selectmode="multiple", exportselection=False, height=5)
        for ano in anos:
            self.anos_listbox.insert("end", str(ano))
        self.anos_listbox.selection_set(0)  # seleciona o primeiro ano automaticamente
        self.anos_listbox.pack(pady=5)

        # Botões de ação
        ctk.CTkButton(self, text="Gerar Relatório", command=self.gerar).pack(pady=10)
        ctk.CTkButton(self, text="📈 Gráfico por Valor", command=self.grafico_valor).pack(pady=5)
        ctk.CTkButton(self, text="📊 Gráfico por Quantidade", command=self.grafico_qtd).pack(pady=5)
        ctk.CTkButton(self, text="💾 Exportar CSV", command=self.exportar_csv).pack(pady=5)
        ctk.CTkButton(self, text="💾 Exportar Excel", command=self.exportar_excel).pack(pady=5)
        ctk.CTkButton(self, text="📈 Gráfico por Produto (Valor)", command=self.grafico_produto_valor).pack(pady=5)
        ctk.CTkButton(self, text="📊 Gráfico por Produto (Quantidade)", command=self.grafico_produto_qtd).pack(pady=5)

        # Treeview para dados filtrados
        self.tree = ttk.Treeview(self, columns=("Produto", "Qtd", "Preço", "Total", "Forma", "Data"), show="headings")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        self.df_filtrado = pd.DataFrame()
        self.tabela_valor = pd.DataFrame()
        self.tabela_qtd = pd.DataFrame()

    def gerar(self):
        indices = self.anos_listbox.curselection()
        if not indices:
            # Selecionar todos os anos se nenhum for marcado
            self.anos_listbox.selection_set(0, tk.END)
            indices = self.anos_listbox.curselection()

        anos_selecionados = [int(self.anos_listbox.get(i)) for i in indices]

        self.df_filtrado = self.df[self.df['Ano'].isin(anos_selecionados)]

        if self.df_filtrado.empty:
            messagebox.showinfo("Sem dados", "Nenhum dado encontrado para os anos selecionados.")
            return

        self.tabela_valor = pd.pivot_table(
            self.df_filtrado,
            values='total',
            index='forma_pagamento',
            columns='Mes',
            aggfunc='sum',
            fill_value=0
        )
        self.tabela_valor['Total'] = self.tabela_valor.sum(axis=1)

        self.tabela_qtd = pd.pivot_table(
            self.df_filtrado,
            values='total',
            index='forma_pagamento',
            columns='Mes',
            aggfunc='count',
            fill_value=0
        )
        self.tabela_qtd['Total'] = self.tabela_qtd.sum(axis=1)

        self.tabela_produto_valor = pd.pivot_table(
            self.df_filtrado,
            values='total',
            index='produto',
            aggfunc='sum',
            fill_value=0
        ).sort_values(by='total', ascending=False)

        self.tabela_produto_qtd = pd.pivot_table(
            self.df_filtrado,
            values='quantidade',
            index='produto',
            aggfunc='sum',
            fill_value=0
        ).sort_values(by='quantidade', ascending=False)

        self.atualizar_treeview()
        messagebox.showinfo("Relatório", "Relatório gerado com sucesso.")

    def atualizar_treeview(self):
        self.tree.delete(*self.tree.get_children())
        for _, row in self.df_filtrado.iterrows():
            self.tree.insert("", "end", values=(
                row['produto'],
                row['quantidade'],
                f"R$ {row['preco_unitario']:.2f}",
                f"R$ {row['total']:.2f}",
                row['forma_pagamento'],
                row['data'].strftime("%d/%m/%Y")
            ))

    def grafico_valor(self):
        if self.tabela_valor.empty:
            messagebox.showwarning("Aviso", "Gere o relatório primeiro.")
            return
        fig = px.bar(
            self.tabela_valor.reset_index(),
            x='forma_pagamento',
            y='Total',
            title='Valor Total por Forma de Pagamento',
            color_discrete_sequence=["#1D32A8"]
        )
        fig.show()

    def grafico_qtd(self):
        if self.tabela_qtd.empty:
            messagebox.showwarning("Aviso", "Gere o relatório primeiro.")
            return
        fig = px.bar(
            self.tabela_qtd.reset_index(),
            x='forma_pagamento',
            y='Total',
            title='Quantidade de Compras por Forma de Pagamento',
            color_discrete_sequence=["#D31C1C"]
        )
        fig.show()
    
    def grafico_produto_valor(self):
        if self.tabela_produto_valor.empty:
            messagebox.showwarning("Aviso", "Gere o relatório primeiro.")
            return
        fig = px.bar(
            self.tabela_produto_valor.reset_index(),
            x='produto',
            y='total',
            title='Valor Total por Produto',
            labels={'total': 'Valor Total', 'produto': 'Produto'},
            color_discrete_sequence=["#228B22"]
        )
        fig.update_layout(xaxis_tickangle=-45)
        fig.show()

    def grafico_produto_qtd(self):
        if self.tabela_produto_qtd.empty:
            messagebox.showwarning("Aviso", "Gere o relatório primeiro.")
            return
        fig = px.bar(
            self.tabela_produto_qtd.reset_index(),
            x='produto',
            y='quantidade',
            title='Quantidade Vendida por Produto',
            labels={'quantidade': 'Qtd Vendida', 'produto': 'Produto'},
            color_discrete_sequence=["#FFA500"]
        )
        fig.update_layout(xaxis_tickangle=-45)
        fig.show()

    def exportar_csv(self):
        if self.df_filtrado.empty:
            messagebox.showwarning("Aviso", "Gere o relatório primeiro.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv")
        if path:
            self.df_filtrado.to_csv(path, index=False, sep=";")
            try:
                os.startfile(path)
            except:
                messagebox.showinfo("Salvo", f"Arquivo salvo em: {path}")

    def exportar_excel(self):
        if self.df_filtrado.empty:
            messagebox.showwarning("Aviso", "Gere o relatório primeiro.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx")
        if path:
            self.df_filtrado.to_excel(path, index=False)
            try:
                os.startfile(path)
            except:
                messagebox.showinfo("Salvo", f"Arquivo salvo em: {path}")

# ----------------- FRAME CADASTRO PRODUTO -----------------
class CadastroProdutoFrame(ctk.CTkFrame):
    def __init__(self, parent, _):
        super().__init__(parent)
        self.produto_id = None

        ctk.CTkLabel(self, text="Cadastro de Produtos", font=("Arial", 20)).pack(pady=10)

        self.nome_var = ctk.StringVar()
        self.preco_var = ctk.DoubleVar()

        ctk.CTkEntry(self, placeholder_text="Nome do Produto", textvariable=self.nome_var).pack(pady=5)
        ctk.CTkEntry(self, placeholder_text="Preço (R$)", textvariable=self.preco_var).pack(pady=5)
        ctk.CTkButton(self, text="Cadastrar", command=self.cadastrar_produto).pack(pady=10)

        self.tree = ttk.Treeview(self, columns=("ID", "Produto", "Preço"), show="headings")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
        self.tree.pack(pady=5, fill="x")
        self.tree.bind("<ButtonRelease-1>", self.selecionar_produto)

        ctk.CTkButton(self, text="Atualizar", command=self.atualizar_produto).pack(pady=5)
        ctk.CTkButton(self, text="Excluir", command=self.excluir_produto).pack(pady=5)

        self.atualizar_tabela()

    def atualizar_tabela(self):
        self.tree.delete(*self.tree.get_children())
        df = pd.read_sql("SELECT * FROM cadastro_produto", conexao)
        for _, row in df.iterrows():
            self.tree.insert("", "end", values=(row['id_prod'], row['produto'], f"R$ {row['preco']:.2f}"))

    def cadastrar_produto(self):
        nome = self.nome_var.get().strip()
        preco = self.preco_var.get()
        if not nome or preco <= 0:
            messagebox.showwarning("Atenção", "Preencha nome e preço corretamente.")
            return
        with conexao.begin() as conn:
            conn.execute(text("INSERT INTO cadastro_produto (produto, preco) VALUES (:n, :p)"),
                         {"n": nome, "p": preco})
        self.nome_var.set("")
        self.preco_var.set(0.0)
        self.atualizar_tabela()

    def selecionar_produto(self, event):
        sel = self.tree.focus()
        if not sel:
            return
        values = self.tree.item(sel, "values")
        self.produto_id = int(values[0])
        self.nome_var.set(values[1])
        preco_str = values[2].replace("R$", "").replace(",", ".")
        self.preco_var.set(float(preco_str))

    def atualizar_produto(self):
        if not self.produto_id:
            messagebox.showwarning("Selecione", "Selecione um produto.")
            return
        with conexao.begin() as conn:
            conn.execute(text("UPDATE cadastro_produto SET produto = :n, preco = :p WHERE id_prod = :id"),
                         {"n": self.nome_var.get(), "p": self.preco_var.get(), "id": self.produto_id})
        self.atualizar_tabela()

    def excluir_produto(self):
        if not self.produto_id:
            messagebox.showwarning("Selecione", "Selecione um produto.")
            return
        if messagebox.askyesno("Confirmação", "Excluir este produto?"):
            with conexao.begin() as conn:
                conn.execute(text("DELETE FROM cadastro_produto WHERE id_prod = :id"),
                             {"id": self.produto_id})
            self.atualizar_tabela()

# ----------------- FRAME ADMIN USUÁRIOS -----------------
class AdminUsuariosFrame(ctk.CTkFrame):
    def __init__(self, parent, _):
        super().__init__(parent)
        ctk.CTkLabel(self, text="Administração de Usuários", font=("Arial", 20)).pack(pady=10)

        self.usuario_var = ctk.StringVar()
        self.senha_var = ctk.StringVar()
        self.nivel_var = ctk.StringVar()

        ctk.CTkLabel(self, text="Usuário:", font=("Arial", 14)).pack(pady=(10, 0))
        ctk.CTkEntry(self, placeholder_text="Usuário", textvariable=self.usuario_var).pack(pady=5)

        ctk.CTkLabel(self, text="Senha:", font=("Arial", 14)).pack(pady=(10, 0))
        ctk.CTkEntry(self, placeholder_text="Senha", textvariable=self.senha_var, show="*").pack(pady=5)
        ttk.Combobox(self, values=["admin", "gerente", "atendente"], textvariable=self.nivel_var).pack(pady=5)

        ctk.CTkButton(self, text="Criar", command=self.criar_usuario).pack(pady=10)

        # Treeview com altura personalizada (número de linhas visíveis)
        self.tree = ttk.Treeview(
            self,
            columns=("ID", "Usuário", "Senha", "Nível"),
            show="headings",
            height=8  # Número de linhas visíveis
        )

        # Cabeçalhos das colunas
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)

        # Largura e alinhamento das colunas
        self.tree.column("ID", width=5, anchor="center")
        self.tree.column("Usuário", width=150)
        self.tree.column("Senha", width=150)
        self.tree.column("Nível", width=100, anchor="center")

        self.tree.place(x=200, y=300)
        self.tree.bind("<ButtonRelease-1>", self.selecionar_usuario)

        ctk.CTkButton(self, text="Atualizar", command=self.atualizar_usuario).place(x=200, y=500)
        ctk.CTkButton(self, text="Excluir", command=self.excluir_usuario).place(x=350, y=500)

        self.usuario_id = None
        self.atualizar_tabela()

    def atualizar_tabela(self):
        df = pd.read_sql("SELECT * FROM usuarios", conexao)
        self.tree.delete(*self.tree.get_children())
        for _, row in df.iterrows():
            self.tree.insert("", "end", values=(row['id'], row['username'], row['password'], row['nivel']))

    def criar_usuario(self):
        with conexao.begin() as conn:
            conn.execute(text("INSERT INTO usuarios (username, password, nivel) VALUES (:u, :p, :n)"),
                         {"u": self.usuario_var.get(), "p": self.senha_var.get(), "n": self.nivel_var.get()})
        self.atualizar_tabela()

    def selecionar_usuario(self, event):
        sel = self.tree.focus()
        if not sel:
            return
        values = self.tree.item(sel, "values")
        self.usuario_id = int(values[0])
        self.usuario_var.set(values[1])
        self.senha_var.set(values[2])
        self.nivel_var.set(values[3])

    def atualizar_usuario(self):
        if not self.usuario_id:
            return
        with conexao.begin() as conn:
            conn.execute(text("UPDATE usuarios SET username = :u, password = :p, nivel = :n WHERE id = :id"),
                         {"u": self.usuario_var.get(), "p": self.senha_var.get(),
                          "n": self.nivel_var.get(), "id": self.usuario_id})
        self.atualizar_tabela()

    def excluir_usuario(self):
        if not self.usuario_id:
            return
        with conexao.begin() as conn:
            conn.execute(text("DELETE FROM usuarios WHERE id = :id"), {"id": self.usuario_id})
        self.atualizar_tabela()

# --------------------- FRAME: COMPRAS DO DIA ---------------------
class ComprasDiaFrame(ctk.CTkFrame):
    def __init__(self, parent, username=None):
        super().__init__(parent)
        ctk.CTkLabel(self, text="📅 Compras por Data", font=("Arial", 20)).pack(pady=10)

        # Campos de filtro
        filtro_frame = ctk.CTkFrame(self)
        filtro_frame.pack(pady=5)

        self.dia_var = ctk.StringVar()
        self.mes_var = ctk.StringVar()
        self.ano_var = ctk.StringVar()

        ctk.CTkEntry(filtro_frame, placeholder_text="Dia (DD)", width=80, textvariable=self.dia_var).grid(row=0, column=0, padx=5)
        ctk.CTkEntry(filtro_frame, placeholder_text="Mês (MM)", width=80, textvariable=self.mes_var).grid(row=0, column=1, padx=5)
        ctk.CTkEntry(filtro_frame, placeholder_text="Ano (AAAA)", width=100, textvariable=self.ano_var).grid(row=0, column=2, padx=5)
        ctk.CTkButton(filtro_frame, text="Filtrar", command=self.recarregar_compras_data).grid(row=0, column=3, padx=10)

        # Botão de exclusão
        ctk.CTkButton(self, text="🗑️ Excluir Compra Selecionada", command=self.excluir_compra).pack(pady=5)

        self.total_label = ctk.CTkLabel(self, text="Total: R$ 0.00", font=("Arial", 16))
        self.total_label.pack(pady=5)

        self.tree = ttk.Treeview(self, columns=("Venda", "Data", "Produto", "Qtd", "Total", "Forma"), show="headings")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Carrega as compras do dia atual
        hoje = datetime.now()
        self.dia_var.set(str(hoje.day).zfill(2))
        self.mes_var.set(str(hoje.month).zfill(2))
        self.ano_var.set(str(hoje.year))
        self.recarregar_compras_data()

    def recarregar_compras_data(self):
        try:
            data = datetime(
                int(self.ano_var.get()),
                int(self.mes_var.get()),
                int(self.dia_var.get())
            ).date()
        except ValueError:
            messagebox.showerror("Erro", "Data inválida. Use formato DD/MM/AAAA.")
            return

        query = text("""
            SELECT v.id_venda, v.data, c.produto, c.quantidade, c.total, v.forma_pagamento
            FROM venda v
            JOIN compra c ON v.id_venda = c.id_venda
            WHERE DATE(v.data) = :data
        """)
        df = pd.read_sql(query, conexao, params={"data": data})

        self.tree.delete(*self.tree.get_children())

        total_dia = df['total'].sum() if not df.empty else 0
        self.total_label.configure(text=f"Total: R$ {total_dia:.2f}")

        for _, row in df.iterrows():
            self.tree.insert("", "end", values=(
                row['id_venda'],
                row['data'].strftime("%d/%m/%Y"),
                row['produto'],
                row['quantidade'],
                f"R$ {row['total']:.2f}",
                row['forma_pagamento']
            ))

    def excluir_compra(self):
        selecionado = self.tree.focus()
        if not selecionado:
            messagebox.showwarning("Atenção", "Selecione uma compra para excluir.")
            return

        valores = self.tree.item(selecionado, "values")
        if not valores:
            messagebox.showwarning("Erro", "Não foi possível obter os dados da seleção.")
            return

        id_venda = valores[0]

        if not messagebox.askyesno("Confirmação", f"Deseja realmente excluir a venda nº {id_venda}?"):
            return

        try:
            with conexao.begin() as conn:
                conn.execute(text("DELETE FROM compra WHERE id_venda = :id"), {"id": id_venda})
                conn.execute(text("DELETE FROM venda WHERE id_venda = :id"), {"id": id_venda})
            messagebox.showinfo("Sucesso", "Venda excluída com sucesso.")
            self.recarregar_compras_data()
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao excluir: {e}")

# --------------------- FRAME: DEFINIÇÕES ---------------------
class DefinicoesFrame(ctk.CTkFrame):
    def __init__(self, parent, _):
        super().__init__(parent)
        ctk.CTkLabel(self, text="⚙️ Definições do Sistema", font=("Arial", 20)).pack(pady=20)
        ctk.CTkButton(self, text="Tema: Claro", command=lambda: ctk.set_appearance_mode("light")).pack(pady=10)
        ctk.CTkButton(self, text="Tema: Escuro", command=lambda: ctk.set_appearance_mode("dark")).pack(pady=10)

        ctk.CTkLabel(self, text="⚙️ Configuração de Conta", font=("Arial", 20)).pack(pady=20)
        ctk.CTkLabel(self, text="Alterar Senha da Conta", font=("Arial", 16)).pack(pady=10)

        self.senha_atual_var = ctk.StringVar()
        self.nova_senha_var = ctk.StringVar()
        self.confirmar_senha_var = ctk.StringVar()

        ctk.CTkLabel(self, text="Senha Atual:", font=("Arial", 14)).pack(pady=(10, 0))
        ctk.CTkEntry(self, placeholder_text="Senha Atual", textvariable=self.senha_atual_var, show="*").pack(pady=5)

        ctk.CTkLabel(self, text="Nova Senha:", font=("Arial", 14)).pack(pady=(10, 0))
        ctk.CTkEntry(self, placeholder_text="Nova Senha", textvariable=self.nova_senha_var, show="*").pack(pady=5)

        ctk.CTkLabel(self, text="Confirmar Nova Senha:", font=("Arial", 14)).pack(pady=(10, 0))
        ctk.CTkEntry(self, placeholder_text="Confirmar Nova Senha", textvariable=self.confirmar_senha_var, show="*").pack(pady=5)
        ctk.CTkButton(self, text="Alterar Senha", command=self.alterar_senha).pack(pady=10)

    def alterar_senha(self):
        senha_atual = self.senha_atual_var.get()
        nova_senha = self.nova_senha_var.get()
        confirmar_senha = self.confirmar_senha_var.get()

        try:
            with conexao.begin() as conn:
                result = conn.execute(text("SELECT password FROM usuarios WHERE username = :username"),
                                      {"username": self.username}).fetchone()

                if result and result[0] == senha_atual:
                    if nova_senha == confirmar_senha:
                        conn.execute(text("UPDATE usuarios SET password = :nova WHERE username = :username"),
                                     {"nova": nova_senha, "username": self.username})
                        messagebox.showinfo("Sucesso", "Senha alterada com sucesso!")
                    else:
                        messagebox.showerror("Erro", "A nova senha e a confirmação não coincidem.")
                else:
                    messagebox.showerror("Erro", "Senha atual incorreta.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao alterar a senha: {e}")

# ----------------- APP PRINCIPAL -----------------
class AppPrincipal(ctk.CTk):
    def __init__(self, username, nivel):
        super().__init__()
        self.geometry("1000x600")
        self.username = username
        self.nivel = nivel
        self.title("Sistema Pet Store")

        self.sidebar = ctk.CTkFrame(self, width=200)
        self.sidebar.pack(side="left", fill="y")

        self.container = ctk.CTkFrame(self)
        self.container.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(self.sidebar, text=f"👤 {username}\nNível: {nivel}", font=("Arial", 14)).pack(pady=10)
        ctk.CTkButton(self.sidebar, text="Loja", command=self.abrir_loja).pack(pady=5, fill="x")
        ctk.CTkButton(self.sidebar, text="Relatório", command=self.abrir_relatorio).pack(pady=5, fill="x")
        ctk.CTkButton(self.sidebar, text="Compras do Dia", command=self.abrir_compras_dia).pack(pady=5, fill="x")
        
        
        if nivel in ["admin", "gerente"]:
            ctk.CTkButton(self.sidebar, text="Produtos", command=self.abrir_cadastro).pack(pady=5, fill="x")
        if nivel == "admin":
            ctk.CTkButton(self.sidebar, text="Administração", command=self.abrir_admin).pack(pady=5, fill="x")
        
        ctk.CTkButton(self.sidebar, text="Definições", command=self.abrir_definicoes).pack(pady=5, fill="x")
        
        ctk.CTkButton(self.sidebar, text="Sair", command=self.destroy).pack(side="bottom", pady=10, fill="x")

        self.frames = {}
        self.abrir_loja()

    def carregar(self, FrameClass):
        for f in self.frames.values():
            f.pack_forget()
        if FrameClass not in self.frames:
            try:
                self.frames[FrameClass] = FrameClass(self.container, self.username)
            except TypeError:
                self.frames[FrameClass] = FrameClass(self.container, None)
            self.frames[FrameClass].pack(fill="both", expand=True)
        else:
            self.frames[FrameClass].pack(fill="both", expand=True)

    def abrir_loja(self):
        self.carregar(LojaFrame)

    def abrir_relatorio(self):
        self.carregar(RelatorioFrame)

    def abrir_cadastro(self):
        self.carregar(CadastroProdutoFrame)

    def abrir_admin(self):
        self.carregar(AdminUsuariosFrame)
    
    def abrir_compras_dia(self):
        self.carregar(ComprasDiaFrame)

    def abrir_definicoes(self):
        self.carregar(DefinicoesFrame)

# ----------------- LOGIN -----------------
class LoginApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("400x300")
        self.title("Login - Pet Store")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        

        ctk.CTkLabel(self, text="Login ao Sistema", font=("Arial", 20)).pack(pady=20)

        self.user_var = ctk.StringVar()
        self.pass_var = ctk.StringVar()

        # Label Usuário
        ctk.CTkLabel(self, text="Usuário:", font=("Arial", 15)).place(relx=0.3, rely=0.3, anchor="e")

        # Entry Usuário
        ctk.CTkEntry(self, placeholder_text="Usuário", textvariable=self.user_var, width=200).place(relx=0.31, rely=0.3, anchor="w")
        # Label Senha
        ctk.CTkLabel(self, text="Senha:", font=("Arial", 15)).place(relx=0.3, rely=0.4, anchor="e")
        # Entry Senha
        ctk.CTkEntry(self, placeholder_text="Senha", show="*", textvariable=self.pass_var, width=200).place(relx=0.31, rely=0.4, anchor="w")
        # Botão Entrar
        ctk.CTkButton(self, text="Entrar", command=self.fazer_login, width=100).place(relx=0.43, rely=0.55, anchor="center")

    def fazer_login(self):
        user = self.user_var.get()
        senha = self.pass_var.get()
        query = text("SELECT nivel FROM usuarios WHERE username = :u AND password = :s")
        try:
            df = pd.read_sql(query, conexao, params={"u": user, "s": senha})
            if not df.empty:
                nivel = df.iloc[0]["nivel"]
                self.destroy()
                AppPrincipal(user, nivel).mainloop()
            else:
                messagebox.showerror("Erro", "Usuário ou senha incorretos.")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

if __name__ == "__main__":
    LoginApp().mainloop()
