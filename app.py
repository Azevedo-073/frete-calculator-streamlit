import pandas as pd
import unicodedata
from difflib import get_close_matches
from pathlib import Path
import streamlit as st

st.set_page_config(page_title='Calculadora de Frete', layout='wide')

BASE_DIR = Path(__file__).parent
PASTA_PLANILHAS = BASE_DIR / 'planilhas'

TABELAS = {
    'Tabela A': {
        'arquivo': 'tabela_a.xlsx',
        'aba': 'Planilha1',
        'header': 1,
        'col_origem': 'Origem',
        'col_destino': 'Cidade',
        'col_valor': 'VALOR',
        'col_tarifa': 'Tarifa MAR/26 com pedágio e aumento',
        'col_pedagio': None,
        'col_icms': '% ICMS',
        'col_uf': 'UF',
        'col_km': 'Km',
        'col_faixa_km': 'Faixa de KM',
        'peso_minimo_ton': 25,
        'col_veiculo': None,
        'col_operacao': None,
        'pedagio_embutido': True,
        'regra': 'tarifa_com_minimo',
    },
    'Tabela B': {
        'arquivo': 'tabela_b.xlsx',
        'aba': 'Planilha1',
        'header': 6,
        'col_origem': 'ORIGEM',
        'col_destino': 'DESTINO',
        'col_valor': 'FRETE',
        'col_tarifa': 'FRETE',
        'col_pedagio': None,
        'col_icms': 'ICMS',
        'col_valor_total': 'VALOR TOTAL',
        'col_uf': None,
        'col_km': None,
        'col_faixa_km': None,
        'peso_minimo_ton': 25,
        'col_veiculo': 'VEIICULO',
        'col_operacao': None,
        'pedagio_embutido': False,
        'regra': 'valor_total_preferencial',
    },
    'Tabela C': {
        'arquivo': 'tabela_c.xlsx',
        'aba': 'Planilha1',
        'header': 4,
        'col_origem': 'ORIGEM',
        'col_destino': 'DESTINO',
        'col_valor': 'FRETE AL IN (FRETE INCLUSO ICMS)',
        'col_tarifa': 'FRETE AL IN (FRETE INCLUSO ICMS)',
        'col_pedagio': None,
        'col_icms': None,
        'col_valor_total': None,
        'col_uf': None,
        'col_km': None,
        'col_faixa_km': None,
        'peso_minimo_ton': 25,
        'col_veiculo': 'VEICULO',
        'col_operacao': 'TIPO OPERACAO',
        'pedagio_embutido': False,
        'regra': 'icms_embutido',
    },
}


def normalizar(texto):
    if isinstance(texto, str):
        texto = texto.lower().strip()
        texto = unicodedata.normalize('NFKD', texto)
        texto = texto.encode('ascii', 'ignore').decode('utf-8')
        return texto
    return ''


def normalizar_coluna(texto):
    texto = str(texto).strip().replace('\n', ' ')
    return ' '.join(texto.split()).upper()


def sugerir_opcoes(lista, busca):
    return get_close_matches(busca, list(lista), n=5, cutoff=0.3)


def formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')


def resolver_coluna(df, nome_esperado):
    if not nome_esperado:
        return None

    mapa = {normalizar_coluna(col): col for col in df.columns}
    chave = normalizar_coluna(nome_esperado)

    if chave in mapa:
        return mapa[chave]

    for chave_real, col_real in mapa.items():
        if chave in chave_real or chave_real in chave:
            return col_real

    raise KeyError(nome_esperado)


def detectar_coluna_veiculo(df, config):
    try:
        if config.get('col_veiculo'):
            return resolver_coluna(df, config['col_veiculo'])
    except KeyError:
        pass

    candidatos = [
        'Veículo', 'VEICULO', 'Veiculo', 'VEIICULO', 'Tipo Veículo',
        'Tipo de Veículo', 'Tipo Veiculo', 'Tipo', 'Frota'
    ]

    for candidato in candidatos:
        try:
            return resolver_coluna(df, candidato)
        except KeyError:
            continue

    return None


def detectar_coluna_operacao(df, config):
    try:
        if config.get('col_operacao'):
            return resolver_coluna(df, config['col_operacao'])
    except KeyError:
        pass

    candidatos = [
        'Operação', 'Operacao', 'Tipo Operação', 'Tipo Operacao',
        'TIPO OPERACAO', 'CIF/FOB', 'Modalidade', 'Frete'
    ]

    for candidato in candidatos:
        try:
            col = resolver_coluna(df, candidato)
            serie = df[col].dropna().astype(str).str.strip().str.upper()
            if serie.isin(['CIF', 'FOB']).any():
                return col
        except KeyError:
            continue

    for col in df.columns:
        serie = df[col].dropna().astype(str).str.strip().str.upper()
        if not serie.empty and serie.isin(['CIF', 'FOB']).any():
            return col

    return None


def parse_peso(valor_digitado):
    valor_digitado = str(valor_digitado).strip()
    if not valor_digitado:
        raise ValueError('Informe o peso.')

    valor_digitado = valor_digitado.replace(' ', '')

    if ',' in valor_digitado and '.' in valor_digitado:
        valor_digitado = valor_digitado.replace('.', '').replace(',', '.')
    else:
        valor_digitado = valor_digitado.replace(',', '.')

    peso = float(valor_digitado)

    if peso > 1000:
        peso = peso / 1000

    if peso <= 0:
        raise ValueError('O peso deve ser maior que zero.')

    if peso > 100:
        raise ValueError('Peso muito alto. Confira se digitou em kg ou ton corretamente.')

    return peso


def converter_numero(serie):
    serie = serie.astype(str)
    serie = serie.str.replace('R$', '', regex=False).str.strip()
    serie = serie.str.replace(' ', '', regex=False)

    tem_virgula = serie.str.contains(',', regex=False)
    serie = serie.where(~tem_virgula, serie.str.replace('.', '', regex=False))
    serie = serie.str.replace(',', '.', regex=False)

    return pd.to_numeric(serie, errors='coerce')


@st.cache_data
def carregar_tabela(nome_tabela, uploaded_bytes=None):
    config = TABELAS[nome_tabela].copy()

    if uploaded_bytes is not None:
        origem_arquivo = uploaded_bytes
    else:
        caminho = PASTA_PLANILHAS / config['arquivo']
        if not caminho.exists():
            raise FileNotFoundError(f'Arquivo não encontrado: {caminho}')
        origem_arquivo = caminho

    df = pd.read_excel(
        origem_arquivo,
        sheet_name=config['aba'],
        header=config['header'],
    )

    df.columns = df.columns.astype(str)
    df.columns = [str(col).strip().replace('\n', ' ') for col in df.columns]
    df = df.loc[:, ~pd.Series(df.columns).astype(str).str.contains('Unnamed', na=False).values]
    df = df.dropna(how='all').copy()

    campos_para_resolver = [
        'col_origem', 'col_destino', 'col_valor', 'col_tarifa', 'col_pedagio',
        'col_icms', 'col_valor_total', 'col_uf', 'col_km', 'col_faixa_km'
    ]

    for campo in campos_para_resolver:
        valor = config.get(campo)
        if valor:
            config[campo] = resolver_coluna(df, valor)

    colunas_numericas = [
        config.get('col_valor'),
        config.get('col_tarifa'),
        config.get('col_pedagio'),
        config.get('col_icms'),
        config.get('col_km'),
        config.get('col_valor_total'),
    ]

    for coluna in colunas_numericas:
        if coluna and coluna in df.columns:
            df[coluna] = converter_numero(df[coluna])

    if config.get('col_icms') and config['col_icms'] in df.columns:
        df[config['col_icms']] = df[config['col_icms']].apply(
            lambda x: x / 100 if pd.notna(x) and x > 1 else x
        )

    df['origem_norm'] = df[config['col_origem']].astype(str).apply(normalizar)
    df['destino_norm'] = df[config['col_destino']].astype(str).apply(normalizar)

    col_veiculo = detectar_coluna_veiculo(df, config)
    df['veiculo_norm'] = df[col_veiculo].astype(str).apply(normalizar) if col_veiculo else ''

    col_operacao = detectar_coluna_operacao(df, config)
    df['operacao_norm'] = (
        df[col_operacao].astype(str).str.strip().str.upper() if col_operacao else ''
    )

    return df, col_veiculo, col_operacao, config


def buscar_rotas(df, origem, destino, veiculo=None, usar_veiculo=False, operacao=None, usar_operacao=False):
    origem_norm = normalizar(origem)
    destino_norm = normalizar(destino)

    resultado = df[
        (df['origem_norm'] == origem_norm) &
        (df['destino_norm'] == destino_norm)
    ].copy()

    if usar_veiculo and veiculo:
        veiculo_norm = normalizar(veiculo)
        filtrado = resultado[resultado['veiculo_norm'] == veiculo_norm].copy()
        if not filtrado.empty:
            resultado = filtrado

    if usar_operacao and operacao:
        operacao_norm = str(operacao).strip().upper()
        filtrado = resultado[
            resultado['operacao_norm'].fillna('').astype(str).str.upper() == operacao_norm
        ].copy()
        if not filtrado.empty:
            resultado = filtrado

    return resultado


def calcular_frete(linha, config, peso_ton):
    col_valor = config.get('col_valor')
    col_tarifa = config.get('col_tarifa')
    col_pedagio = config.get('col_pedagio')
    col_icms = config.get('col_icms')
    col_valor_total = config.get('col_valor_total')

    valor_base = linha[col_valor] if col_valor and col_valor in linha.index and pd.notna(linha[col_valor]) else 0
    tarifa_base = linha[col_tarifa] if col_tarifa and col_tarifa in linha.index and pd.notna(linha[col_tarifa]) else 0
    pedagio = linha[col_pedagio] if col_pedagio and col_pedagio in linha.index and pd.notna(linha[col_pedagio]) else 0

    if config.get('pedagio_embutido'):
        pedagio = 0

    icms_perc = linha[col_icms] if col_icms and col_icms in linha.index and pd.notna(linha[col_icms]) else 0
    valor_total_base = linha[col_valor_total] if col_valor_total and col_valor_total in linha.index and pd.notna(linha[col_valor_total]) else None

    peso_minimo = config.get('peso_minimo_ton', 25)
    regra = config.get('regra')

    if regra == 'tarifa_com_minimo':
        if peso_ton <= peso_minimo:
            peso_cobrado = peso_minimo
            frete = valor_base
            regra_aplicada = f'Frete mínimo aplicado (cobrança mínima de {peso_minimo} ton)'
        else:
            peso_cobrado = peso_ton
            frete = tarifa_base * peso_ton
            regra_aplicada = f'Tarifa por tonelada aplicada (acima de {peso_minimo} ton)'

        icms = frete * icms_perc
        total = frete + icms
        return {
            'frete': frete,
            'pedagio': 0,
            'icms_perc': icms_perc,
            'icms': icms,
            'total': total,
            'regra': regra_aplicada,
            'peso_cobrado': peso_cobrado,
            'icms_embutido': False,
        }

    if regra == 'icms_embutido':
        if peso_ton <= peso_minimo:
            peso_cobrado = peso_minimo
            frete = valor_base
            regra_aplicada = f'Frete com ICMS incluso (cobrança mínima de {peso_minimo} ton)'
        else:
            peso_cobrado = peso_ton
            tarifa_por_ton = tarifa_base if tarifa_base else (valor_base / peso_minimo if valor_base else 0)
            frete = tarifa_por_ton * peso_ton
            regra_aplicada = f'Frete com ICMS incluso proporcional (acima de {peso_minimo} ton)'

        total = frete + pedagio
        return {
            'frete': frete,
            'pedagio': pedagio,
            'icms_perc': 0,
            'icms': 0,
            'total': total,
            'regra': regra_aplicada,
            'peso_cobrado': peso_cobrado,
            'icms_embutido': True,
        }

    if regra == 'valor_total_preferencial':
        base_calculo = valor_total_base if valor_total_base is not None else valor_base
        if peso_ton <= peso_minimo:
            peso_cobrado = peso_minimo
            frete = base_calculo
            regra_aplicada = f'Valor base aplicado como mínimo (cobrança mínima de {peso_minimo} ton)'
        else:
            peso_cobrado = peso_ton
            tarifa_por_ton = tarifa_base if tarifa_base else (base_calculo / peso_minimo if base_calculo else 0)
            frete = tarifa_por_ton * peso_ton
            regra_aplicada = f'Valor proporcional aplicado (acima de {peso_minimo} ton)'

        if valor_total_base is not None:
            icms = 0
            total = frete + pedagio
        else:
            icms = frete * icms_perc
            total = frete + pedagio + icms

        return {
            'frete': frete,
            'pedagio': pedagio,
            'icms_perc': icms_perc,
            'icms': icms,
            'total': total,
            'regra': regra_aplicada,
            'peso_cobrado': peso_cobrado,
            'icms_embutido': valor_total_base is not None,
        }

    if peso_ton <= peso_minimo:
        peso_cobrado = peso_minimo
        frete = valor_base
        regra_aplicada = f'Frete mínimo aplicado (cobrança mínima de {peso_minimo} ton)'
    else:
        peso_cobrado = peso_ton
        tarifa_por_ton = tarifa_base if tarifa_base else (valor_base / peso_minimo if valor_base else 0)
        frete = tarifa_por_ton * peso_ton
        regra_aplicada = f'Tarifa proporcional aplicada (acima de {peso_minimo} ton)'

    icms = frete * icms_perc
    total = frete + pedagio + icms

    return {
        'frete': frete,
        'pedagio': pedagio,
        'icms_perc': icms_perc,
        'icms': icms,
        'total': total,
        'regra': regra_aplicada,
        'peso_cobrado': peso_cobrado,
        'icms_embutido': False,
    }


st.title('🚛 Calculadora de Frete')
st.caption('Consulta de frete com múltiplas tabelas e regras de cálculo.')

with st.sidebar:
    st.subheader('Configuração')
    tabela = st.selectbox('Tabela', list(TABELAS.keys()))
    arquivo_upload = st.file_uploader('Substituir planilha', type=['xlsx'])

try:
    if arquivo_upload is not None:
        df_base, col_veiculo, col_operacao, config = carregar_tabela(tabela, arquivo_upload.getvalue())
    else:
        df_base, col_veiculo, col_operacao, config = carregar_tabela(tabela)
except Exception as e:
    st.error(f'Erro ao carregar a base: {e}')
    st.stop()

usa_veiculo = col_veiculo is not None
usa_operacao = col_operacao is not None

origens_disponiveis = sorted(
    df_base[config['col_origem']]
    .dropna()
    .astype(str)
    .str.strip()
    .unique()
)

col1, col2, col3, col4, col5, col6 = st.columns([1.1, 1.8, 1.8, 1.2, 1.5, 1.3])

with col1:
    st.text_input('Tabela selecionada', value=tabela, disabled=True)

with col2:
    origem = st.selectbox('Origem', [''] + origens_disponiveis)

df_origem = df_base.copy()
if origem:
    df_origem = df_origem[df_origem['origem_norm'] == normalizar(origem)].copy()

destinos_disponiveis = sorted(
    df_origem[config['col_destino']]
    .dropna()
    .astype(str)
    .str.strip()
    .unique()
)

with col3:
    destino = st.selectbox('Destino', [''] + destinos_disponiveis)

df_rota = df_origem.copy()
if destino:
    df_rota = df_rota[df_rota['destino_norm'] == normalizar(destino)].copy()

opcoes_veiculo = []
if usa_veiculo and col_veiculo:
    opcoes_veiculo = sorted(
        df_rota[col_veiculo].dropna().astype(str).str.strip().unique()
    )

with col4:
    peso_txt = st.text_input('Peso (kg ou ton)', placeholder='Ex: 24500 ou 24,5')

with col5:
    if usa_veiculo:
        veiculo = st.selectbox('Veículo', [''] + opcoes_veiculo)
    else:
        veiculo = st.text_input('Veículo', value='Não aplicável', disabled=True)

df_rota_final = df_rota.copy()
if usa_veiculo and veiculo:
    df_rota_final = df_rota_final[df_rota_final['veiculo_norm'] == normalizar(veiculo)].copy()

opcoes_operacao = []
if usa_operacao and col_operacao:
    opcoes_operacao = sorted([
        v for v in df_rota_final[col_operacao].dropna().astype(str).str.strip().str.upper().unique()
        if v in ['CIF', 'FOB']
    ])

with col6:
    if usa_operacao:
        operacao = st.selectbox('Operação', [''] + opcoes_operacao)
    else:
        operacao = st.text_input('Operação', value='Não aplicável', disabled=True)

if 'resultado_consulta' not in st.session_state:
    st.session_state['resultado_consulta'] = None
if 'peso_consulta' not in st.session_state:
    st.session_state['peso_consulta'] = None
if 'tabela_consulta' not in st.session_state:
    st.session_state['tabela_consulta'] = None
if 'config_consulta' not in st.session_state:
    st.session_state['config_consulta'] = None
if 'col_veiculo_consulta' not in st.session_state:
    st.session_state['col_veiculo_consulta'] = None
if 'col_operacao_consulta' not in st.session_state:
    st.session_state['col_operacao_consulta'] = None

calcular = st.button('Calcular frete', use_container_width=True)

if calcular:
    if not origem or not destino or not peso_txt:
        st.warning('Preencha origem, destino e peso.')
        st.stop()

    try:
        peso = parse_peso(peso_txt)
    except Exception as e:
        st.error(str(e))
        st.stop()

    resultado = buscar_rotas(
        df_base,
        origem,
        destino,
        veiculo=veiculo,
        usar_veiculo=usa_veiculo,
        operacao=operacao,
        usar_operacao=usa_operacao,
    )

    st.session_state['resultado_consulta'] = resultado.copy()
    st.session_state['peso_consulta'] = peso
    st.session_state['tabela_consulta'] = tabela
    st.session_state['config_consulta'] = config
    st.session_state['col_veiculo_consulta'] = col_veiculo
    st.session_state['col_operacao_consulta'] = col_operacao

resultado = st.session_state.get('resultado_consulta')
peso = st.session_state.get('peso_consulta')
config_resultado = st.session_state.get('config_consulta')
col_veiculo_resultado = st.session_state.get('col_veiculo_consulta')
col_operacao_resultado = st.session_state.get('col_operacao_consulta')

if resultado is not None and tabela == st.session_state.get('tabela_consulta'):
    if resultado.empty:
        st.error('Nenhum frete encontrado.')
    else:
        if len(resultado) > 1:
            st.warning('Foram encontrados vários resultados. Escolha a rota correta.')

            opcoes = []
            for idx, row in resultado.iterrows():
                valor_ref = row[config_resultado['col_valor']] if pd.notna(row[config_resultado['col_valor']]) else 0
                descricao = f"{row[config_resultado['col_origem']]} -> {row[config_resultado['col_destino']]} | Referência: {formatar_brl(valor_ref)}"
                if col_veiculo_resultado:
                    descricao += f" | Veículo: {row[col_veiculo_resultado]}"
                if col_operacao_resultado:
                    descricao += f" | Operação: {str(row[col_operacao_resultado]).upper()}"
                opcoes.append((idx, descricao))

            escolha = st.selectbox(
                'Selecione a opção correta',
                options=opcoes,
                format_func=lambda x: x[1],
                key='selecao_rota'
            )
            linha = resultado.loc[escolha[0]]
        else:
            linha = resultado.iloc[0]

        calculo = calcular_frete(linha, config_resultado, peso)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric('Frete base', formatar_brl(calculo['frete']))
        m2.metric('Pedágio', formatar_brl(calculo['pedagio']))
        m3.metric('ICMS', formatar_brl(calculo['icms']))
        m4.metric('Total', formatar_brl(calculo['total']))

        st.divider()

        d1, d2, d3 = st.columns(3)
        d1.write(f"**Origem:** {linha[config_resultado['col_origem']]}")
        d2.write(f"**Destino:** {linha[config_resultado['col_destino']]}")
        d3.write(f"**Peso informado:** {peso:.2f} ton")

        st.write(f"**Peso cobrado:** {calculo['peso_cobrado']:.2f} ton")
        st.write(f"**Regra aplicada:** {calculo['regra']}")
        if calculo['icms_embutido']:
            st.write('**ICMS aplicado:** já incluso no frete')
        else:
            st.write(f"**ICMS aplicado:** {calculo['icms_perc'] * 100:.0f}%")

        detalhe = {
            'Tabela': tabela,
            'Origem': linha.get(config_resultado['col_origem'], ''),
            'Destino': linha.get(config_resultado['col_destino'], ''),
            'UF': linha.get(config_resultado['col_uf'], '') if config_resultado.get('col_uf') else '',
            'Km': linha.get(config_resultado['col_km'], '') if config_resultado.get('col_km') else '',
            'Faixa de KM': linha.get(config_resultado['col_faixa_km'], '') if config_resultado.get('col_faixa_km') else '',
            'Veículo': linha.get(col_veiculo_resultado, 'Não aplicável') if col_veiculo_resultado else 'Não aplicável',
            'Operação': linha.get(col_operacao_resultado, 'Não aplicável') if col_operacao_resultado else 'Não aplicável',
            'Frete': formatar_brl(calculo['frete']),
            'Pedágio': formatar_brl(calculo['pedagio']),
            'ICMS': formatar_brl(calculo['icms']),
            'Total': formatar_brl(calculo['total']),
        }

        st.dataframe(pd.DataFrame([detalhe]), use_container_width=True, hide_index=True)
