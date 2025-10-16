# app.py

import os
import pandas as pd
import numpy as np
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, render_template, request, send_from_directory

app = Flask(__name__)

# Textos e constantes

TARIFA_KWH = 0.6735  # Valor médio da tarifa SP em R$/kWh

POTENCIA_MAP = {
    'muito_leve': (0, 1.5), 'leve': (2, 5), 'intermediario': (6, 15),
    'pesado': (20, 50), 'muito_pesado': (60, 100), 'extremamente_pesado': (101, float('inf'))
}
PARTIDA_MAP = {'baixo': 0, 'medio': 1.5, 'alto': 2.5}

TEXTOS_REGIMES = {
    'S1': """
        <h3>Regime S1 – Contínuo</h3>
        <p>Segundo as informações inseridas, seu motor se enquadra no <strong>regime S1 (serviço contínuo)</strong>.</p>
        <p>Isso significa que ele pode operar por longos períodos em carga constante, atingindo equilíbrio térmico sem risco de superaquecimento.</p>
    """,
    'S3': """
        <h3>Regime S3 – Intermitente periódico</h3>
        <p>Com base nas respostas fornecidas, seu motor se enquadra no <strong>regime S3 (serviço intermitente periódico)</strong>.</p>
        <p>Ou seja, ele pode suportar ciclos repetidos de trabalho e parada, desde que o número de partidas por hora seja limitado.</p>
    """,
    'S4': """
        <h3>Regime S4 – Intermitente periódico com partida</h3>
        <p>De acordo com as informações, seu motor se enquadra no <strong>regime S4</strong>.</p>
        <p>Nesse regime, além de ciclos de trabalho e parada, o aquecimento causado pelas partidas também influencia.</p>
    """,
    'S6': """
        <h3>Regime S6 – Contínuo com carga intermitente</h3>
        <p>Segundo suas respostas, o motor indicado opera em <strong>regime S6 (contínuo com carga intermitente)</strong>.</p>
        <p>Isso quer dizer que o motor permanece sempre ligado, mas a carga varia bastante ao longo do tempo.</p>
    """,
    'S9': """
        <h3>Regime S9 – Contínuo com variações não periódicas</h3>
        <p>Com base no que você informou, o regime mais adequado é o <strong>S9</strong>, caracterizado por variações bruscas e não periódicas de carga.</p>
        <p>Esse regime exige motores projetados para esforços severos, comuns em britadores e ventiladores de túnel.</p>
    """,
    'INDEFINIDO': """
        <h3>Regime de Serviço não encontrado</h3>
        <p>Com base na combinação de critérios selecionada, não foi possível identificar um regime de serviço padrão correspondente.</p>
        <p>A seleção do motor ainda é válida com base nos critérios de potência e torque, mas a análise do regime de operação pode exigir uma avaliação mais detalhada da sua aplicação.</p>
    """
}

# Lógica principal
def calcular_consumo(row, horas_dia):
    try:
        potencia_kw = float(row['Potência [kW]'])
        eficiencia = float(row['η 100% Pn']) / 100
        if eficiencia == 0: return float('inf')
        consumo_mensal = (potencia_kw / eficiencia) * horas_dia * 30
        return consumo_mensal
    except (ValueError, TypeError):
        return float('inf')

def calcular_custo(row, horas_dia, tarifa):
    """Calcula o custo DIÁRIO de consumo."""
    try:
        potencia_kw = float(row['Potência [kW]'])
        eficiencia = float(row['η 100% Pn']) / 100
        if eficiencia == 0: return float('inf')
        custo_diario = (potencia_kw / tarifa * horas_dia) / eficiencia
        return custo_diario
    except (ValueError, TypeError):
        return float('inf')

def determinar_regime(porte, esforco, operacao):
    partidas = "frequentes" if operacao == 'intermitente' else "ocasionais"
    if partidas == "ocasionais":
        if porte in ['muito_leve', 'leve', 'intermediario'] and esforco == 'baixo': return 'S1'
        if porte == 'intermediario' and esforco == 'medio': return 'S6'
        if porte in ['pesado', 'muito_pesado', 'extremamente_pesado'] and esforco == 'alto': return 'S9'
    if partidas == "frequentes":
        if porte in ['leve', 'intermediario'] and esforco == 'baixo': return 'S3'
        if porte == 'intermediario' and esforco in ['medio', 'alto']: return 'S4'
    return 'INDEFINIDO'

# Gerando o gráfico
def gerar_grafico_conjugado(motor_data):
    try:
        cn = motor_data['Cn (kgfm)'] * 9.80665
        cp_cn = motor_data['Corrente com rotor bloqueado Cp/Cn']
        cmax_cn = motor_data['Conjugado máximo Cmáx./Cn']
        rpm_nominal = motor_data['RPM']

        cp = cn * cp_cn
        cmax = cn * cmax_cn

        ns = 1800
        s_n = (ns - rpm_nominal) / ns if ns > rpm_nominal else 0

        s_max = 0.2
        s = np.linspace(0.001, 1, 500)
        conjugado = (2 * cmax) / ((s / s_max) + (s_max / s))

        plt.figure(figsize=(10, 6))

        plt.fill_between(s, 0, cn, color='#fadadd', alpha=0.7, label='Região abaixo do Cn')
        plt.fill_between(s, cn, conjugado, color='#d1eaf1', alpha=0.6, label='Região de sobrecarga')

        plt.plot(s, conjugado, 'k-', linewidth=1.5, label='Curva de Conjugado')
        plt.plot(1, cp, 'ro', markersize=8, label=f'Cp (Partida)')
        plt.plot(s_n, cn, 'bs', markersize=8, label=f'Cn (Nominal)')
        plt.plot(s_max, cmax, 'g^', markersize=8, label=f'Cmax')

        plt.axhline(y=cn, color='gray', linestyle='--')
        plt.axhline(y=cmax, color='gray', linestyle='--')
        plt.axhline(y=cp, color='gray', linestyle='--')

        plt.title('Curva de Conjugado vs Escorregamento - Motor trifásico IP55')
        plt.xlabel('Escorregamento (s)')
        plt.ylabel('Conjugado (Nm)')
        plt.xlim(0, 1)
        plt.ylim(0, cmax * 1.25)
        plt.grid(True, linestyle=':', alpha=0.7)
        plt.legend()

        img_path = os.path.join('static', 'images')
        os.makedirs(img_path, exist_ok=True)
        graph_url = os.path.join(img_path, 'conjugado_vs_escorregamento.png')
        plt.savefig(graph_url, dpi=100)
        plt.close()

        return graph_url
    except Exception as e:
        print(f"Erro ao gerar gráfico de conjugado: {e}")
        return None


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        try:
            porte, partida, operacao = request.form['porte'], request.form['partida'], request.form['operacao']
            horas_dia = float(request.form['horas_dia'])
        except (KeyError, ValueError):
            return render_template('home.html', error="Todos os campos devem ser preenchidos corretamente.")

        df = pd.read_excel('data/catalogo_motores.xlsx')
        df.columns = df.columns.str.strip()

        min_cv, max_cv = POTENCIA_MAP[porte]
        df_filtrado = df[(df['Potência [cv]'] >= min_cv) & (df['Potência [cv]'] <= max_cv)]
        cp_cn_min = PARTIDA_MAP[partida]
        df_filtrado = df_filtrado[df_filtrado['Corrente com rotor bloqueado Cp/Cn'] >= cp_cn_min]

        if df_filtrado.empty:
            return render_template('home.html', error="Nenhum motor encontrado com os critérios especificados.")

        df_filtrado['Consumo_Mensal_kWh'] = df_filtrado.apply(lambda row: calcular_consumo(row, horas_dia), axis=1)
        df_filtrado['Custo_Diario'] = df_filtrado.apply(lambda row: calcular_custo(row, horas_dia, TARIFA_KWH), axis=1)

        df_eficiencia = df_filtrado.sort_values(by='η 100% Pn', ascending=False)
        df_consumo = df_filtrado.sort_values(by='Consumo_Mensal_kWh', ascending=True)

        resultados, motores_selecionados = {}, []

        opcao_a = df_eficiencia.iloc[0]
        resultados['A'] = opcao_a.to_dict()
        motores_selecionados.append(opcao_a)

        opcao_b = df_consumo.iloc[0]
        resultados['B'] = opcao_b.to_dict()
        if not opcao_b.equals(opcao_a): motores_selecionados.append(opcao_b)

        for _, motor in df_eficiencia.iterrows():
            if not motor.equals(opcao_a) and not motor.equals(opcao_b):
                resultados['C'] = motor.to_dict();
                motores_selecionados.append(motor);
                break

        grafico_url = gerar_grafico_conjugado(opcao_a)

        regime_ideal = determinar_regime(porte, partida, operacao)
        texto_regime = TEXTOS_REGIMES[regime_ideal]

        df_final = pd.DataFrame(motores_selecionados).drop(columns=['Consumo_Mensal_kWh', 'Custo_Diario'],
                                                           errors='ignore')
        download_path = 'downloads'
        os.makedirs(download_path, exist_ok=True)
        download_filename = "motores_selecionados.xlsx"
        df_final.to_excel(os.path.join(download_path, download_filename), index=False)

        return render_template('home.html', resultados=resultados, grafico_url=grafico_url,
                               download_file=download_filename, texto_regime=texto_regime)

    return render_template('home.html')

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory('downloads', filename, as_attachment=True)

@app.route('/mais_informacoes')
def mais_informacoes():
    return render_template('mais_informacoes.html')

if __name__ == '__main__':

    app.run(debug=True)
