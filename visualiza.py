import streamlit as st
import pandas as pd
import numpy as np

# Configuração da página para ocupar toda a largura
st.set_page_config(layout="wide", page_title="Simulador Eleitoral - 2º Turno")

# --- CARREGAMENTO DE DADOS ---
@st.cache_data
def carregar_dados():
    # Lê o banco consolidado gerado anteriormente
    df = pd.read_csv("resultado_final_1oturno.csv.gz", sep=';', compression='gzip')
    
    # Criar coluna Região para permitir o filtro regional
    regioes = {
        'Norte': ['AC', 'AP', 'AM', 'PA', 'RO', 'RR', 'TO'],
        'Nordeste': ['AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE'],
        'Centro-Oeste': ['DF', 'GO', 'MT', 'MS'],
        'Sudeste': ['ES', 'MG', 'RJ', 'SP'],
        'Sul': ['PR', 'RS', 'SC']
    }
    def mapear_regiao(uf):
        for regiao, estados in regioes.items():
            if uf in estados: return regiao
        return 'Outros'
        
    df['REGIAO'] = df['SG_UF'].apply(mapear_regiao)
    
    # Calcular as abstenções absolutas do 1º Turno
    df['ABSTENCOES_1T'] = df['QT_APTOS'] - df['QT_COMPARECIMENTO']
    return df

df_base = carregar_dados()

# --- LAYOUT PRINCIPAL (Esquerda: Resultados | Direita: Simulação) ---
col_resultados, col_simulacao = st.columns([2, 1])

# ==========================================
# PAINEL DA DIREITA - PARÂMETROS DA SIMULAÇÃO
# ==========================================
with col_simulacao:
    st.header("⚙️ Parâmetros da Simulação")
    
    # Passo 1
    st.subheader("Passo 1: Fidelidade (1º Turno)")
    fidelidade_base = pd.DataFrame({
        'Candidato': ['Flávio', 'Lula'],
        'Mantém Voto (%)': [95.0, 95.0],
        'Não vai votar (%)': [1.0, 1.0]
    })
    fidelidade_editada = st.data_editor(fidelidade_base, hide_index=True)
    
    # Passo 2
    st.subheader("Passo 2: Migração de Outros Candidatos")
    migracao_base = pd.DataFrame({
        'Candidato 1T': [
            'AUGUSTO JORGE CURY', 'CLARIANA ZACARKIM BARAO', 'EDMILSON SILVA COSTA', 
            'HERTZ DA CONCEICAO DIAS', 'LEONARDO ALVES DE ARAUJO', 'RENAN ANTONIO FERREIRA DOS SANTOS', 
            'ROMEU ZEMA NETO', 'RONALDO RAMOS CAIADO', 'RUI COSTA PIMENTA', 
            'SAMARA MARTINS DA SILVA FEITOSA', 'WILSON GRASSI JUNIOR', 'VOTO BRANCO + VOTO NULO'
        ],
        'Flávio (%)': [50, 30, 70, 80, 15, 50, 70, 60, 30, 80, 30, 0],
        'Lula (%)': [20, 40, 10, 0, 15, 30, 15, 20, 10, 0, 40, 0],
        'Não vai votar (%)': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        'Branco/Nulo (%)': [10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 99]
    })
    migracao_editada = st.data_editor(migracao_base, hide_index=True)
    
    # Passo 3
    st.subheader("Passo 3: Comportamento das Abstenções (1T)")
    abstencao_base = pd.DataFrame({
        'Não vai votar (%)': [95.0], 'Branco/Nulo (%)': [0.0], 'Flávio (%)': [0.0], 'Lula (%)': [0.0]
    })
    abstencao_editada = st.data_editor(abstencao_base, hide_index=True)
    
    # Passo 4
    st.subheader("Passo 4: Fator Turbo Lula")
    turbo_lula = st.slider("Capacidade extra de converter indecisos (%)", 0.0, 100.0, 20.0, 1.0) / 100.0

# ==========================================
# CÁLCULOS DO MODELO MATEMÁTICO
# ==========================================
df_sim = df_base.copy()

# Inicializando colunas do 2º Turno
df_sim['2T_FLAVIO'] = 0.0
df_sim['2T_LULA'] = 0.0
df_sim['2T_BRANCO_NULO'] = 0.0
df_sim['2T_ABSTENCAO'] = 0.0
df_sim['2T_INDECISOS'] = 0.0

# Aplicando Passo 1 (Fidelidade)
for idx, row in fidelidade_editada.iterrows():
    candidato_col = 'FLAVIO NANTES BOLSONARO' if row['Candidato'] == 'Flávio' else 'LUIZ INÁCIO LULA DA SILVA'
    votos_origem = df_sim[candidato_col]
    
    mantem = row['Mantém Voto (%)'] / 100.0
    nao_vota = row['Não vai votar (%)'] / 100.0
    indeciso = 1.0 - (mantem + nao_vota)
    
    if row['Candidato'] == 'Flávio':
        df_sim['2T_FLAVIO'] += votos_origem * mantem
    else:
        df_sim['2T_LULA'] += votos_origem * mantem
        
    df_sim['2T_ABSTENCAO'] += votos_origem * nao_vota
    df_sim['2T_INDECISOS'] += votos_origem * indeciso

# Aplicando Passo 2 (Migração)
for idx, row in migracao_editada.iterrows():
    votos_origem = df_sim[row['Candidato 1T']]
    
    flavio_pct = row['Flávio (%)'] / 100.0
    lula_pct = row['Lula (%)'] / 100.0
    nao_vota_pct = row['Não vai votar (%)'] / 100.0
    bn_pct = row['Branco/Nulo (%)'] / 100.0
    indeciso_pct = 1.0 - (flavio_pct + lula_pct + nao_vota_pct + bn_pct)
    
    df_sim['2T_FLAVIO'] += votos_origem * flavio_pct
    df_sim['2T_LULA'] += votos_origem * lula_pct
    df_sim['2T_ABSTENCAO'] += votos_origem * nao_vota_pct
    df_sim['2T_BRANCO_NULO'] += votos_origem * bn_pct
    df_sim['2T_INDECISOS'] += votos_origem * indeciso_pct

# Aplicando Passo 3 (Abstenções)
abst = abstencao_editada.iloc[0]
votos_origem = df_sim['ABSTENCOES_1T']
nao_vota_pct = abst['Não vai votar (%)'] / 100.0
bn_pct = abst['Branco/Nulo (%)'] / 100.0
flavio_pct = abst['Flávio (%)'] / 100.0
lula_pct = abst['Lula (%)'] / 100.0
indeciso_pct = 1.0 - (nao_vota_pct + bn_pct + flavio_pct + lula_pct)

df_sim['2T_ABSTENCAO'] += votos_origem * nao_vota_pct
df_sim['2T_BRANCO_NULO'] += votos_origem * bn_pct
df_sim['2T_FLAVIO'] += votos_origem * flavio_pct
df_sim['2T_LULA'] += votos_origem * lula_pct
df_sim['2T_INDECISOS'] += votos_origem * indeciso_pct

# Aplicando Passo 4 (Distribuição de Indecisos + Turbo Lula)
votos_1t_lula = df_sim['LUIZ INÁCIO LULA DA SILVA']
votos_1t_flavio = df_sim['FLAVIO NANTES BOLSONARO']
total_1t_validos = votos_1t_lula + votos_1t_flavio
total_1t_validos = total_1t_validos.replace(0, 1) # Evitar divisão por zero

base_lula = votos_1t_lula / total_1t_validos
base_flavio = votos_1t_flavio / total_1t_validos

lula_turbo = base_lula + turbo_lula
total_rebalanceado = lula_turbo + base_flavio

perc_final_lula = lula_turbo / total_rebalanceado
perc_final_flavio = base_flavio / total_rebalanceado

# Guardar os indecisos para exibição na tabela ANTES de zerar a variável
df_sim['INDECISOS_TOTAIS'] = df_sim['2T_INDECISOS']
df_sim['INDECISOS_PARA_LULA'] = df_sim['2T_INDECISOS'] * perc_final_lula
df_sim['INDECISOS_PARA_FLAVIO'] = df_sim['2T_INDECISOS'] * perc_final_flavio

# Adicionar os votos indecisos aos candidatos
df_sim['2T_LULA'] += df_sim['INDECISOS_PARA_LULA']
df_sim['2T_FLAVIO'] += df_sim['INDECISOS_PARA_FLAVIO']
df_sim['2T_INDECISOS'] = 0 # Todos distribuídos

# ==========================================
# PAINEL DA ESQUERDA - RESULTADOS E FILTROS
# ==========================================
with col_resultados:
    st.header("📊 Resultados da Simulação")
    
    # Seletor de Granularidade
    nivel = st.selectbox("Analisar por:", ['Nacional', 'Região', 'Estado', 'Município', 'Seção'])
    
    df_filtrado = df_sim.copy()
    grupo = []
    
    # Filtros dinâmicos em cascata
    if nivel == 'Município':
        col1, col2 = st.columns(2)
        with col1:
            uf = st.selectbox("Selecione o Estado:", sorted(df_sim['SG_UF'].unique()))
        with col2:
            municipios = sorted(df_sim[df_sim['SG_UF'] == uf]['NM_MUNICIPIO'].unique())
            mun = st.selectbox("Selecione o Município:", municipios)
        
        df_filtrado = df_sim[(df_sim['SG_UF'] == uf) & (df_sim['NM_MUNICIPIO'] == mun)]
        grupo = ['SG_UF', 'NM_MUNICIPIO']
        
    elif nivel == 'Seção':
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            uf = st.selectbox("Estado:", sorted(df_sim['SG_UF'].unique()))
        with col2:
            municipios = sorted(df_sim[df_sim['SG_UF'] == uf]['NM_MUNICIPIO'].unique())
            mun = st.selectbox("Município:", municipios)
        with col3:
            zonas = sorted(df_sim[(df_sim['SG_UF'] == uf) & (df_sim['NM_MUNICIPIO'] == mun)]['NR_ZONA'].unique())
            zona = st.selectbox("Zona:", zonas)
        with col4:
            secoes = sorted(df_sim[(df_sim['SG_UF'] == uf) & (df_sim['NM_MUNICIPIO'] == mun) & (df_sim['NR_ZONA'] == zona)]['NR_SECAO'].unique())
            secao = st.selectbox("Seção:", secoes)
            
        df_filtrado = df_sim[(df_sim['SG_UF'] == uf) & (df_sim['NM_MUNICIPIO'] == mun) & 
                             (df_sim['NR_ZONA'] == zona) & (df_sim['NR_SECAO'] == secao)]
        grupo = ['SG_UF', 'NM_MUNICIPIO', 'NR_ZONA', 'NR_SECAO']
        
    elif nivel == 'Estado':
        grupo = ['SG_UF']
    elif nivel == 'Região':
        grupo = ['REGIAO']
    else: # Nacional
        grupo = []
    
    # Colunas que serão somadas na agregação (incluindo as de indecisos)
    colunas_soma = [
        'QT_APTOS', 'QT_COMPARECIMENTO', 'ABSTENCOES_1T', 'FLAVIO NANTES BOLSONARO', 
        'LUIZ INÁCIO LULA DA SILVA', 'VOTO BRANCO + VOTO NULO', 
        '2T_FLAVIO', '2T_LULA', '2T_BRANCO_NULO', '2T_ABSTENCAO',
        'INDECISOS_TOTAIS', 'INDECISOS_PARA_LULA', 'INDECISOS_PARA_FLAVIO'
    ]
    
    if grupo:
        df_agrupado = df_filtrado.groupby(grupo)[colunas_soma].sum().reset_index()
    else:
        df_agrupado = pd.DataFrame(df_filtrado[colunas_soma].sum()).T
        df_agrupado['Nivel'] = 'Brasil'
        grupo = ['Nivel']
        
    # --- CÁLCULOS DE TOTAIS PARA PERCENTUAIS ---
    # 1º Turno (Válidos = Comparecimento - Brancos e Nulos)
    validos_1t = df_agrupado['QT_COMPARECIMENTO'] - df_agrupado['VOTO BRANCO + VOTO NULO']
    comparecimento_1t = df_agrupado['QT_COMPARECIMENTO']
    
    # 2º Turno
    validos_2t = df_agrupado['2T_FLAVIO'] + df_agrupado['2T_LULA']
    comparecimento_2t = df_agrupado['QT_APTOS'] - df_agrupado['2T_ABSTENCAO']

    # Função auxiliar para formatação
    def formatar_celula(absoluto, divisor):
        if divisor == 0: return "0 (0.0%)"
        pct = (absoluto / divisor) * 100
        return f"{int(absoluto):,} ({pct:.1f}%)"

    # --- MONTANDO O DATAFRAME DE EXIBIÇÃO ---
    df_display = pd.DataFrame()
    
    # 1. Adiciona as colunas de identificação
    for col in grupo:
        df_display[col] = df_agrupado[col]
        
    df_display['Aptos'] = df_agrupado['QT_APTOS'].apply(lambda x: f"{int(x):,}")

    # 2. Bloco 1º Turno
    df_display['1T - Abstenções'] = [formatar_celula(a, apt) for a, apt in zip(df_agrupado['ABSTENCOES_1T'], df_agrupado['QT_APTOS'])]
    df_display['1T - Brancos/Nulos (Comp.)'] = [formatar_celula(v, comp) for v, comp in zip(df_agrupado['VOTO BRANCO + VOTO NULO'], comparecimento_1t)]
    df_display['1T - Flávio (Válidos)'] = [formatar_celula(v, val) for v, val in zip(df_agrupado['FLAVIO NANTES BOLSONARO'], validos_1t)]
    df_display['1T - Lula (Válidos)'] = [formatar_celula(v, val) for v, val in zip(df_agrupado['LUIZ INÁCIO LULA DA SILVA'], validos_1t)]

    # 3. Bloco 2º Turno
    df_display['2T - Abstenções'] = [formatar_celula(a, apt) for a, apt in zip(df_agrupado['2T_ABSTENCAO'], df_agrupado['QT_APTOS'])]
    df_display['2T - Brancos/Nulos (Comp.)'] = [formatar_celula(v, comp) for v, comp in zip(df_agrupado['2T_BRANCO_NULO'], comparecimento_2t)]
    df_display['2T - Flávio (Válidos)'] = [formatar_celula(v, val) for v, val in zip(df_agrupado['2T_FLAVIO'], validos_2t)]
    df_display['2T - Lula (Válidos)'] = [formatar_celula(v, val) for v, val in zip(df_agrupado['2T_LULA'], validos_2t)]

    # 4. Bloco Indecisos (Fatiados)
    df_display['Indecisos Totais (Válidos 2T)'] = [formatar_celula(i, val) for i, val in zip(df_agrupado['INDECISOS_TOTAIS'], validos_2t)]
    df_display['Indecisos p/ Flávio (Total Ind.)'] = [formatar_celula(f, i) for f, i in zip(df_agrupado['INDECISOS_PARA_FLAVIO'], df_agrupado['INDECISOS_TOTAIS'])]
    df_display['Indecisos p/ Lula (Total Ind.)'] = [formatar_celula(l, i) for l, i in zip(df_agrupado['INDECISOS_PARA_LULA'], df_agrupado['INDECISOS_TOTAIS'])]

    # --- FUNÇÃO PARA COLORIR A TABELA ---
    def colorir_tabela(df):
        cores = pd.DataFrame('', index=df.index, columns=df.columns)
        
        # Define as regras de cores para cada bloco
        for col in df.columns:
            if col.startswith('1T'):
                cores[col] = 'background-color: #d4edda; color: black;' # Verde claro
            elif col.startswith('2T'):
                cores[col] = 'background-color: #fff3cd; color: black;' # Amarelo claro
            elif col.startswith('Indecisos'):
                cores[col] = 'background-color: #ffe5b4; color: black;' # Laranja claro
        return cores

    # Aplica o estilo na tabela e exibe
    df_styled = df_display.style.apply(colorir_tabela, axis=None)
    st.dataframe(df_styled, use_container_width=True, hide_index=True)
    
    # --- MÉTRICAS GLOBAIS DA TELA ---
    totais = df_filtrado[colunas_soma].sum()
    st.subheader("Comparativo Global do Filtro Selecionado")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Lula (2º Turno)", f"{int(totais['2T_LULA']):,}", f"{int(totais['2T_LULA'] - totais['LUIZ INÁCIO LULA DA SILVA']):,} vs 1T")
    c2.metric("Flávio (2º Turno)", f"{int(totais['2T_FLAVIO']):,}", f"{int(totais['2T_FLAVIO'] - totais['FLAVIO NANTES BOLSONARO']):,} vs 1T")
    c3.metric("Abstenções (2º Turno)", f"{int(totais['2T_ABSTENCAO']):,}", f"{int(totais['2T_ABSTENCAO'] - totais['ABSTENCOES_1T']):,} vs 1T")
    c4.metric("Brancos/Nulos (2º T)", f"{int(totais['2T_BRANCO_NULO']):,}", f"{int(totais['2T_BRANCO_NULO'] - totais['VOTO BRANCO + VOTO NULO']):,} vs 1T")