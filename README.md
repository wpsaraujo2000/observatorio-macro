# Observatório Macroeconômico — PTAX

Dashboard de análise cambial com dados oficiais do Banco Central do Brasil.

## Tecnologias
Python, Streamlit, Plotly, Pandas, NumPy e `python-bcb`.

## Executar localmente

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Funcionalidades
- Cotações PTAX de compra e venda de seis moedas
- Evolução histórica e médias móveis de 20/60 observações
- Comparação de índices base 100
- Estatísticas descritivas e volatilidade anualizada
- Exportação de dados e estatísticas para CSV

## Publicação
Suba os arquivos para um repositório público no GitHub. Em [Streamlit Community Cloud](https://share.streamlit.io/), selecione o repositório e defina `app.py` como arquivo principal.

## Notas metodológicas
A cotação é a última observação disponível de cada dia. Em finais de semana e feriados, a API pode não retornar valores. A volatilidade anualizada é calculada como o desvio-padrão amostral dos retornos simples entre observações, multiplicado por raiz de 252. Para moedas com unidades de cotação especiais, verifique a documentação da PTAX antes de comparar níveis.

Fonte: [BCB PTAX](https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/aplicacao#!/recursos).
