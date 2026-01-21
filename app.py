import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

st.set_page_config(page_title="Conversor de Extratos - Vôlei Joinville", layout="wide")

st.title("📊 Conversor de Extratos PDF para Excel")
st.markdown("Arraste seu arquivo PDF consolidado para transformar em uma planilha organizada.")

uploaded_file = st.file_uploader("Escolha o arquivo PDF", type="pdf")

def extrair_dados(pdf_file):
    transacoes = []
    # Regex para capturar data (DD/MM/AAAA) e o restante da linha
    padrao_data = re.compile(r"(\d{2}/\d{2}/\d{4})")
    
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                for linha in text.split('\n'):
                    # Procura por linhas que começam com data
                    match = padrao_data.search(linha)
                    if match:
                        data = match.group(1)
                        # Remove a data da linha para isolar descrição e valor
                        resto = linha.replace(data, "").strip()
                        
                        # Tenta capturar o valor no final da linha (formato -1.234,56 ou 1.234,56)
                        partes = resto.split()
                        if len(partes) >= 2:
                            valor_str = partes[-2] if "R$" in partes[-1] else partes[-1]
                            descricao = " ".join(partes[:-1]) if "R$" in partes[-1] else " ".join(partes[:-1])
                            
                            # Limpeza do valor para converter em float
                            try:
                                valor_limpo = valor_str.replace(".", "").replace(",", ".")
                                valor_float = float(valor_limpo)
                                transacoes.append({
                                    "Data": data,
                                    "Descrição": descricao,
                                    "Valor": valor_float
                                })
                            except ValueError:
                                continue

    df = pd.DataFrame(transacoes)
    return df

if uploaded_file is not None:
    with st.spinner('Processando extratos... Isso pode levar alguns segundos devido ao volume de dados.'):
        df_total = extrair_dados(uploaded_file)
        
        if not df_total.empty:
            # Separação de Entradas e Saídas
            entradas = df_total[df_total['Valor'] > 0].copy()
            saidas = df_total[df_total['Valor'] < 0].copy()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("✅ Entradas")
                st.dataframe(entradas, use_container_width=True)
                st.metric("Total Entradas", f"R$ {entradas['Valor'].sum():,.2f}")

            with col2:
                st.subheader("❌ Saídas")
                st.dataframe(saidas, use_container_width=True)
                st.metric("Total Saídas", f"R$ {saidas['Valor'].sum():,.2f}")

            # Geração do Excel em memória para download
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                entradas.to_excel(writer, sheet_name='Entradas', index=False)
                saidas.to_excel(writer, sheet_name='Saídas', index=False)
                df_total.to_excel(writer, sheet_name='Tudo Consolidado', index=False)
            
            st.divider()
            st.download_button(
                label="📥 Baixar Planilha Excel Completa (.xlsx)",
                data=output.getvalue(),
                file_name="extrato_consolidado_joinville.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("Não foi possível extrair dados. Verifique se o PDF é um extrato digital original.")
