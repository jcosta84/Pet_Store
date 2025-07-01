import fitz  # PyMuPDF
import re
import pandas as pd

# Lê o PDF
with fitz.open(r"C:\Users\pcost\PycharmProjects\Geral_Departamento\1.pdf") as pdf:
    texto = ""
    for pagina in pdf:
        texto += pagina.get_text()

# Extrai os dados: CIL (8 dígitos) seguido por (x), depois Nº do Contador (10 dígitos)
padrao = re.findall(r"(\d{8})\(\d\)\s*[\s\S]{0,50}?(\d{10})", texto)

# Cria o DataFrame
df = pd.DataFrame(padrao, columns=["CIL", "Nº Contador"])
df['Nº Contador'] = df['Nº Contador'].astype(int)
# Exibe a tabela
print(df)