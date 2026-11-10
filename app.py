"""Observatório Macroeconômico — dados PTAX do Banco Central do Brasil."""
from datetime import date, timedelta
from io import BytesIO
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from bcb import PTAX

st.set_page_config(page_title='Observatório Macroeconômico | PTAX', page_icon='📈', layout='wide')
st.markdown('''<style>
.block-container {padding-top: 1.7rem; max-width: 1400px;}
[data-testid="stMetric"] {background:rgba(120,140,170,.08);padding:15px;border-radius:12px;}
</style>''', unsafe_allow_html=True)

MOEDAS = {'Dólar americano (USD)': 'USD', 'Euro (EUR)': 'EUR', 'Libra esterlina (GBP)': 'GBP',
          'Franco suíço (CHF)': 'CHF', 'Iene japonês (JPY)': 'JPY', 'Dólar canadense (CAD)': 'CAD'}

@st.cache_data(ttl=3600, show_spinner=False)
def obter_ptax(moeda: str, inicio: date, fim: date) -> pd.DataFrame:
    endpoint = PTAX().get_endpoint('CotacaoMoedaPeriodo')
    dados = (endpoint.query()
             .parameters(moeda=moeda, dataInicial=inicio.strftime('%m-%d-%Y'),
                         dataFinalCotacao=fim.strftime('%m-%d-%Y'))
             .collect())
    if dados.empty:
        return pd.DataFrame(columns=['data', 'compra', 'venda', 'moeda'])
    dados = dados.copy()
    necessarias = {'dataHoraCotacao', 'cotacaoCompra', 'cotacaoVenda'}
    if not necessarias.issubset(dados.columns):
        raise ValueError(f'Campos inesperados na resposta da PTAX: {list(dados.columns)}')
    dados['data'] = pd.to_datetime(dados['dataHoraCotacao']).dt.normalize()
    dados = dados.sort_values('dataHoraCotacao').drop_duplicates('data', keep='last')
    dados['compra'] = pd.to_numeric(dados['cotacaoCompra'], errors='coerce')
    dados['venda'] = pd.to_numeric(dados['cotacaoVenda'], errors='coerce')
    dados['moeda'] = moeda
    return dados[['data', 'compra', 'venda', 'moeda']].dropna().sort_values('data').reset_index(drop=True)

@st.cache_data(ttl=3600, show_spinner=False)
def carregar(moedas: tuple, inicio: date, fim: date) -> tuple[pd.DataFrame, list[str]]:
    quadros, avisos = [], []
    for moeda in moedas:
        try:
            quadro = obter_ptax(moeda, inicio, fim)
            if quadro.empty:
                avisos.append(f'{moeda}: sem cotações no período.')
            else:
                quadros.append(quadro)
        except Exception as exc:
            avisos.append(f'{moeda}: falha na consulta ({type(exc).__name__}: {exc}).')
    return (pd.concat(quadros, ignore_index=True) if quadros else pd.DataFrame(), avisos)

def estatisticas(s: pd.Series) -> dict:
    s = s.dropna().astype(float)
    retornos = s.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    return {
        'Observações': len(s), 'Média': s.mean(), 'Mediana': s.median(),
        'Mínimo': s.min(), 'Máximo': s.max(), 'Desvio-padrão': s.std(ddof=1),
        'Variação acumulada (%)': (s.iloc[-1] / s.iloc[0] - 1) * 100 if len(s)>1 and s.iloc[0] else np.nan,
        'Volatilidade anualizada (%)': retornos.std(ddof=1) * np.sqrt(252) * 100 if len(retornos)>1 else np.nan,
    }

st.title('📈 Observatório Macroeconômico')
st.caption('Inteligência cambial com dados oficiais da PTAX | Banco Central do Brasil')

hoje = date.today()
with st.sidebar:
    st.header('Filtros')
    escolhidas = st.multiselect('Moedas', list(MOEDAS), default=list(MOEDAS)[:3])
    periodo = st.date_input('Intervalo', value=(hoje-timedelta(days=365), hoje), max_value=hoje)
    tipo = st.radio('Cotação', ['Venda', 'Compra'], horizontal=True)
    st.caption('Consultas armazenadas em cache por até 1 hora. Dados sujeitos à publicação pelo BCB.')

if not escolhidas:
    st.info('Selecione pelo menos uma moeda na barra lateral.')
    st.stop()
if not isinstance(periodo, (tuple, list)) or len(periodo) != 2:
    st.info('Selecione as datas inicial e final.')
    st.stop()
inicio, fim = periodo
if inicio > fim:
    st.error('A data inicial não pode ser posterior à data final.')
    st.stop()
if (fim-inicio).days > 3650:
    st.warning('Para manter o desempenho, selecione um intervalo de até 10 anos.')
    st.stop()

with st.spinner('Consultando as séries PTAX...'):
    dados, avisos = carregar(tuple(MOEDAS[m] for m in escolhidas), inicio, fim)
for aviso in avisos:
    st.warning(aviso)
if dados.empty:
    st.error('Nenhuma cotação disponível. Tente outro período ou verifique a conexão com o BCB.')
    st.stop()

coluna = tipo.lower()
series = dados.pivot(index='data', columns='moeda', values=coluna).sort_index()
st.caption(f'Última data disponível no recorte: {series.dropna(how="all").index.max():%d/%m/%Y}. '
           'Valores em BRL por unidade de moeda estrangeira, conforme unidade divulgada pelo BCB.')

st.subheader('Resumo das cotações')
cols = st.columns(min(len(series.columns), 4))
for i, moeda in enumerate(series.columns):
    s = series[moeda].dropna()
    if s.empty: continue
    delta = (s.iloc[-1]/s.iloc[-2]-1)*100 if len(s)>1 else None
    cols[i % len(cols)].metric(moeda, f'R$ {s.iloc[-1]:,.4f}',
                               f'{delta:+.2f}% vs. observação anterior' if delta is not None else None)

aba1, aba2, aba3, aba4 = st.tabs(['Evolução histórica', 'Comparação', 'Estatísticas', 'Dados e exportação'])
with aba1:
    st.subheader('Cotação PTAX ao longo do tempo')
    fig = go.Figure()
    for moeda in series:
        s = series[moeda].dropna()
        fig.add_trace(go.Scatter(x=s.index, y=s, name=moeda, mode='lines'))
    fig.update_layout(template='plotly_dark', height=480, hovermode='x unified',
                      xaxis_title='Data', yaxis_title='Cotação PTAX (BRL)', legend_title='Moeda')
    st.plotly_chart(fig, use_container_width=True)
    st.caption('Comparações em nível exigem cautela: moedas distintas possuem escalas e unidades próprias.')
    st.subheader('Médias móveis')
    moeda_mm = st.selectbox('Moeda para tendência', list(series.columns))
    s = series[moeda_mm].dropna()
    fig_mm = go.Figure()
    fig_mm.add_trace(go.Scatter(x=s.index, y=s, name='Cotação'))
    for janela in (20, 60):
        fig_mm.add_trace(go.Scatter(x=s.index, y=s.rolling(janela, min_periods=janela).mean(),
                                    name=f'Média móvel ({janela} observações)'))
    fig_mm.update_layout(template='plotly_dark', height=420, hovermode='x unified')
    st.plotly_chart(fig_mm, use_container_width=True)

with aba2:
    st.subheader('Índice base 100 — primeira observação de cada moeda')
    normalizadas = pd.DataFrame(index=series.index)
    for moeda in series:
        s = series[moeda].dropna()
        if not s.empty and s.iloc[0] != 0:
            normalizadas[moeda] = series[moeda] / s.iloc[0] * 100
    fig_comp = go.Figure()
    for moeda in normalizadas:
        fig_comp.add_trace(go.Scatter(x=normalizadas.index, y=normalizadas[moeda], name=moeda))
    fig_comp.add_hline(y=100, line_dash='dash', line_color='gray')
    fig_comp.update_layout(template='plotly_dark', height=480, hovermode='x unified', yaxis_title='Índice (base 100)')
    st.plotly_chart(fig_comp, use_container_width=True)
    st.caption('Cada moeda usa sua primeira cotação disponível como base 100; datas-base podem diferir.')
    st.subheader('Retornos percentuais entre observações')
    retornos = series.pct_change(fill_method=None) * 100
    st.line_chart(retornos)

with aba3:
    st.subheader('Estatísticas descritivas por moeda')
    tabela = pd.DataFrame({moeda: estatisticas(series[moeda]) for moeda in series}).T
    st.dataframe(tabela.style.format('{:,.4f}', na_rep='—', subset=[c for c in tabela if c != 'Observações']),
                 use_container_width=True)
    st.caption('Volatilidade: desvio-padrão amostral dos retornos simples entre observações × √252; '
               'é uma aproximação anualizada, não uma previsão. A média e o desvio-padrão da cotação estão em BRL.')
    moeda_hist = st.selectbox('Distribuição dos retornos', list(series.columns))
    r = series[moeda_hist].dropna().pct_change().dropna() * 100
    if len(r):
        fig_hist = go.Figure(go.Histogram(x=r, nbinsx=40, name=moeda_hist))
        fig_hist.update_layout(template='plotly_dark', xaxis_title='Retorno por observação (%)',
                               yaxis_title='Frequência', height=390)
        st.plotly_chart(fig_hist, use_container_width=True)

with aba4:
    st.subheader('Base de dados consultada')
    st.dataframe(dados.sort_values(['moeda', 'data']), use_container_width=True, hide_index=True)
    st.download_button('⬇️ Exportar CSV', dados.to_csv(index=False).encode('utf-8-sig'),
                       file_name='observatorio_ptax.csv', mime='text/csv')
    st.download_button('⬇️ Exportar estatísticas CSV',
                       pd.DataFrame({m: estatisticas(series[m]) for m in series}).T.to_csv().encode('utf-8-sig'),
                       file_name='estatisticas_ptax.csv', mime='text/csv')

st.divider()
st.caption('Fonte: Banco Central do Brasil — serviço PTAX (Olinda), via biblioteca python-bcb. '
           'Informações para análise e educação; não constituem recomendação financeira.')
