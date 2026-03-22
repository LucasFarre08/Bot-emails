import matplotlib
matplotlib.use('Agg')
import mysql.connector
import smtplib
import matplotlib.pyplot as plt
import numpy as np
import io
import os
from datetime import date, timedelta
from staticmap import StaticMap, CircleMarker
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


# ===============================
# FUNÇÕES
# ===============================

def variacao_percentual(atual, anterior):
    if anterior == 0:
        return 0 if atual == 0 else 100
    if anterior is None:
        return 0
    return round(((atual - anterior) / anterior) * 100, 2)


def formatar_variacao(valor):
    return f"+{valor}%" if valor > 0 else f"{valor}%"


def cor_variacao(valor):
    if valor > 0:
        return "#22c55e"
    elif valor < 0:
        return "#ef4444"
    return "#cbd5e1"


def contar_generico(cursor, tabela, campo_data, id_cliente, inicio, fim):
    cursor.execute(f"""
        SELECT COUNT(*)
        FROM {tabela} t
        JOIN frotas f
        ON f.nome COLLATE utf8mb4_unicode_ci =
           t.grouping COLLATE utf8mb4_unicode_ci
        WHERE f.IDcliente = %s
        AND {campo_data} >= %s
        AND {campo_data} < %s
    """,(id_cliente,inicio,fim))

    return cursor.fetchone()[0] or 0


def contar_eventos_dados(cursor, id_cliente, inicio, fim):
    cursor.execute("""
    SELECT 
        CASE evento
            WHEN 0 THEN 'Frenagem Brusca'
            WHEN 1 THEN 'Aceleração Brusca'
            WHEN 2 THEN 'Curva Brusca'
            WHEN 3 THEN 'Curva Brusca'
            WHEN 4 THEN 'Curva Brusca'
            WHEN 5 THEN 'Condução Agressiva'
            ELSE 'Outros'
        END AS evento_nome,
        COUNT(*) as total
    FROM seguranca s
    JOIN frotas f 
        ON f.nome COLLATE utf8mb4_unicode_ci =
           s.grouping COLLATE utf8mb4_unicode_ci
    WHERE f.IDcliente = %s
    AND s.data >= %s 
    AND s.data < %s
    GROUP BY evento_nome
    """,(id_cliente, inicio, fim))

    return cursor.fetchall()


# ===============================
# PERÍODO
# ===============================

inicio_ultimo_mes = date(2026,2,1)
fim_ultimo_mes = date(2026,3,1) 

dias_periodo = (fim_ultimo_mes - inicio_ultimo_mes).days

inicio_mes_anterior = inicio_ultimo_mes - timedelta(days=dias_periodo)
fim_mes_anterior = inicio_ultimo_mes

periodo_relatorio = f"{inicio_ultimo_mes.strftime('%d/%m/%Y')} - {(fim_ultimo_mes - timedelta(days=1)).strftime('%d/%m/%Y')}"
periodo_comparacao = f"{inicio_mes_anterior.strftime('%d/%m/%Y')} - {(fim_mes_anterior - timedelta(days=1)).strftime('%d/%m/%Y')}"


# ===============================
# BANCO
# ===============================

conexao = mysql.connector.connect(
    host="localhost",
    user="root",
    password="12345",
    database="telemetria_db"
)

cursor = conexao.cursor()

cursor.execute("""
SELECT IDcliente, MAX(`Razao Social`)
FROM frotas
WHERE IDcliente IS NOT NULL
GROUP BY IDcliente
""")

clientes = cursor.fetchall()


# ===============================
# LOOP CLIENTES
# ===============================

for id_cliente, razao_social in clientes:

    print("Gerando relatório:", razao_social)

    # ===============================
    # EVENTOS DISTRIBUIÇÃO
    # ===============================

    eventos_dist = contar_eventos_dados(cursor,id_cliente,inicio_ultimo_mes,fim_ultimo_mes) or []

    eventos_dict = {
        "Frenagem Brusca": 0,
        "Aceleração Brusca": 0,
        "Curva Brusca": 0,
        "Condução Agressiva": 0
    }

    for nome, total in eventos_dist:
        if nome in eventos_dict:
            eventos_dict[nome] += total
    
    # ===============================
    # VARIAÇÕES (placeholder)
    # ===============================

    var_veiculos = 0
    var_km = 0
    var_litros = 0
    var_consumo = 0
    var_eventos = 0
    var_eventos_100km = 0   

    # ===============================
    # VIAGENS
    # ===============================

    cursor.execute("""
        SELECT COUNT(DISTINCT v.grouping),
               SUM(v.quilometragem),
               SUM(v.litros_consumidos)
        FROM viagens v
        JOIN frotas f 
        ON f.nome COLLATE utf8mb4_unicode_ci = v.grouping COLLATE utf8mb4_unicode_ci
        WHERE f.IDcliente = %s
        AND v.inicio >= %s
        AND v.inicio < %s
    """,(id_cliente,inicio_ultimo_mes,fim_ultimo_mes))

    veiculos, km_total, litros = cursor.fetchone()
    veiculos = veiculos or 0
    km_total = km_total or 0
    litros = litros or 0
    if veiculos <= 1:
        print(f"Sem dados suficientes para {razao_social}, email não enviado.")
        continue

    consumo_medio = round(km_total/litros,2) if litros else 0

    # ===============================
    # EVENTOS
    # ===============================

    cursor.execute("""
        SELECT COUNT(*)
        FROM seguranca s
        JOIN frotas f 
        ON f.nome COLLATE utf8mb4_unicode_ci = s.grouping COLLATE utf8mb4_unicode_ci
        WHERE f.IDcliente = %s
        AND s.data >= %s
        AND s.data < %s
    """,(id_cliente,inicio_ultimo_mes,fim_ultimo_mes))

    eventos = cursor.fetchone()[0] or 0
    eventos_100km = round((eventos/km_total)*100,2) if km_total else 0

    # ===============================
    # EVENTOS CONDUÇÃO
    # ===============================

    freio = contar_generico(cursor,"freio","ativado",id_cliente,inicio_ultimo_mes,fim_ultimo_mes)
    kickdown = contar_generico(cursor,"kickdown","ativado",id_cliente,inicio_ultimo_mes,fim_ultimo_mes)
    rpm_amarelo = contar_generico(cursor,"rpm_amarelo","ativado",id_cliente,inicio_ultimo_mes,fim_ultimo_mes)
    rpm_vermelho = contar_generico(cursor,"rpm_vermelho","ativado",id_cliente,inicio_ultimo_mes,fim_ultimo_mes)
    vel80 = contar_generico(cursor,"velocidade_80km","ativado",id_cliente,inicio_ultimo_mes,fim_ultimo_mes)
    vel60 = contar_generico(cursor,"velocidade_chuva_60km","ativado",id_cliente,inicio_ultimo_mes,fim_ultimo_mes)

    # ===============================
    # OCIOSIDADE
    # ===============================

    cursor.execute("""
    SELECT 
        CONCAT(ROUND(SUM(TIME_TO_SEC(IFNULL(duracao,'00:00:00'))) / 3600,2),' horas'),
        ROUND(SUM(IFNULL(combustivel_gasto,0)), 2),
        ROUND(SUM(IFNULL(combustivel_gasto,0) * 6.46), 2)
    FROM ociosidade o
    JOIN frotas f 
    ON f.nome COLLATE utf8mb4_unicode_ci = o.grouping COLLATE utf8mb4_unicode_ci
    WHERE f.IDcliente = %s
    AND o.ativado >= %s
    AND o.ativado < %s
    """,(id_cliente,inicio_ultimo_mes,fim_ultimo_mes))

    ocioso_tempo, combustivel_ocioso, total_reais = cursor.fetchone()
    ocioso_tempo = ocioso_tempo or "0 horas"
    combustivel_ocioso = combustivel_ocioso or 0
    total_reais = total_reais or 0

    # ===============================
    # TOP EFICIÊNCIA
    # ===============================

    cursor.execute("""
        SELECT 
            v.grouping AS placa,
            SUM(IFNULL(v.quilometragem,0)) AS km,
            SUM(IFNULL(v.litros_consumidos,0)) AS litros,
            ROUND(SUM(IFNULL(v.quilometragem,0)) / 
                NULLIF(SUM(IFNULL(v.litros_consumidos,0)),0), 2) AS km_l
        FROM viagens v
        JOIN frotas f 
            ON f.nome COLLATE utf8mb4_unicode_ci = v.grouping COLLATE utf8mb4_unicode_ci
        WHERE f.IDcliente = %s
        AND v.inicio >= %s
        AND v.inicio < %s
        GROUP BY v.grouping
        HAVING litros > 0
        AND km > 100
        ORDER BY km_l DESC
        LIMIT 10
    """,(id_cliente,inicio_ultimo_mes,fim_ultimo_mes))

    dados_melhores = cursor.fetchall()

    placas_m = [d[0] for d in dados_melhores]
    km_m = [d[1] for d in dados_melhores]
    litros_m = [d[2] for d in dados_melhores]

    cursor.execute("""
    SELECT 
        v.grouping AS placa,
        SUM(IFNULL(v.quilometragem,0)) AS km,
        SUM(IFNULL(v.litros_consumidos,0)) AS litros,
        ROUND(SUM(IFNULL(v.quilometragem,0)) / 
              NULLIF(SUM(IFNULL(v.litros_consumidos,0)),0), 2) AS km_l
    FROM viagens v
    JOIN frotas f 
        ON f.nome COLLATE utf8mb4_unicode_ci = v.grouping COLLATE utf8mb4_unicode_ci
    WHERE f.IDcliente = %s
    AND v.inicio >= %s
    AND v.inicio < %s
    GROUP BY v.grouping
    HAVING litros > 0
    AND km > 100
    ORDER BY km_l ASC
    LIMIT 10
""",(id_cliente,inicio_ultimo_mes,fim_ultimo_mes))

    dados_piores = cursor.fetchall()

    placas_p = [d[0] for d in dados_piores]
    km_p = [d[1] for d in dados_piores]
    litros_p = [d[2] for d in dados_piores]

    # ===============================
    # GRÁFICOS
    # ===============================

    buffer_melhores = None

    if placas_m:
        plt.figure(figsize=(8,5))

        y = np.arange(len(placas_m))
        km_max = max(km_m) if km_m else 1

        # fundo
        plt.barh(y, [km_max]*len(y), color="#e5e7eb")

        # KM
        plt.barh(y, km_m, color="#ef4444")

        # linha litros
        for i, litros in enumerate(litros_m):
            plt.plot([litros, litros], [i-0.3, i+0.3], color='black', linewidth=2)

        # eficiência
        for i, (km, litros) in enumerate(zip(km_m, litros_m)):
            if litros > 0:
                eficiencia = km / litros

                plt.text(
                    km + (km_max * 0.02),
                    i,
                    f"{eficiencia:.2f} km/l",
                    va='center',
                    fontsize=9,
                    fontweight='bold',
                    color='#111827'
                )

        # legenda
        legend_elements = [
            Patch(facecolor="#ef4444", label="KM Rodado"),
            Line2D([0], [0], color='black', lw=2, label='Litros Consumidos')
        ]
        plt.legend(handles=legend_elements)

        plt.yticks(y, placas_m)
        plt.title("Top Piores Placas (Eficiência)")
        plt.xlabel("KM Rodado")

        plt.tight_layout()

        buffer_melhores = None

    if placas_m:
        plt.figure(figsize=(8,5))

        y = np.arange(len(placas_m))
        km_max = max(km_m) if km_m else 1

        # fundo
        plt.barh(y, [km_max]*len(y), color="#e5e7eb")

        # KM
        plt.barh(y, km_m, color="#14b8a6")

        # linha litros
        for i, litros in enumerate(litros_m):
            plt.plot([litros, litros], [i-0.3, i+0.3], color='black', linewidth=2)

        # eficiência
        for i, (km, litros) in enumerate(zip(km_m, litros_m)):
            if litros > 0:
                eficiencia = km / litros

                plt.text(
                    km + (km_max * 0.02),
                    i,
                    f"{eficiencia:.2f} km/l",
                    va='center',
                    fontsize=9,
                    fontweight='bold',
                    color='#111827'
                )

        # legenda
        legend_elements = [
            Patch(facecolor="#14b8a6", label="KM Rodado"),
            Line2D([0], [0], color='black', lw=2, label='Litros Consumidos')
        ]
        plt.legend(handles=legend_elements)

        plt.yticks(y, placas_m)
        plt.title("Top Melhores Placas (Eficiência)")
        plt.xlabel("KM Rodado")

        plt.tight_layout()

        buffer_melhores = io.BytesIO()
        plt.savefig(buffer_melhores, format="png", bbox_inches="tight")
        plt.close()
        buffer_melhores.seek(0)

        buffer_melhores = io.BytesIO()
        plt.savefig(buffer_melhores, format="png", bbox_inches="tight")
        plt.close()
        buffer_melhores.seek(0)

        buffer_piores = None

    if placas_p:
        plt.figure(figsize=(8,5))

        y = np.arange(len(placas_p))
        km_max = max(km_p) if km_p else 1

        plt.barh(y, [km_max]*len(y), color="#e5e7eb")
        plt.barh(y, km_p, color="#14b8a6")

        for i, litros in enumerate(litros_p):
            plt.plot([litros, litros], [i-0.3, i+0.3], color='black', linewidth=2)

        for i, (km, litros) in enumerate(zip(km_p, litros_p)):
            if litros > 0:
                eficiencia = km / litros

                plt.text(
                    km + (km_max * 0.02),
                    i,
                    f"{eficiencia:.2f} km/l",
                    va='center',
                    fontsize=9,
                    fontweight='bold',
                    color='#111827'
                )

        # legenda
        legend_elements = [
            Patch(facecolor="#14b8a6", label="KM Rodado"),
            Line2D([0], [0], color='black', lw=2, label='Litros Consumidos')
        ]
        plt.legend(handles=legend_elements)

        plt.yticks(y, placas_p)
        plt.title("Top Melhores Placas (Eficiência)")
        plt.xlabel("KM Rodado")

        plt.tight_layout()

        buffer_piores = io.BytesIO()
        plt.savefig(buffer_piores, format="png", bbox_inches="tight")
        plt.close()
        buffer_piores.seek(0)

        # ===============================
        # MAPA (AGORA CORRETO)
        # ===============================

        cursor.execute("""
            SELECT s.coordenadas
            FROM seguranca s
            JOIN frotas f 
            ON f.nome COLLATE utf8mb4_unicode_ci = s.grouping COLLATE utf8mb4_unicode_ci
            WHERE f.IDcliente = %s
            AND s.data >= %s
            AND s.data < %s
            AND s.coordenadas IS NOT NULL
            LIMIT 300
        """,(id_cliente,inicio_ultimo_mes,fim_ultimo_mes))

        coords = cursor.fetchall()
        mapa = StaticMap(900,500)

        for coord in coords:
            try:
                lat,lon = map(float,coord[0].split(","))
                mapa.add_marker(CircleMarker((lon,lat),"#ff3333",5))
            except:
                pass

        if coords:
            buffer_mapa = io.BytesIO()
            mapa.render().save(buffer_mapa,format="PNG")
            buffer_mapa.seek(0)
            mapa_html='<img src="cid:mapa_eventos">'
        else:
            buffer_mapa=None
            mapa_html="<p>Sem eventos com coordenadas</p>"


        # ===============================
        # HTML
        # ===============================

        html = f"""
        <body style="font-family:Arial;background:#f4f6f8;padding:30px">


        <table width="100%" style="margin-bottom:20px;">
        <tr>
        <td style="font-size:28px;font-weight:bold;color:#111827;">
        🚛 Relatório Frota - {razao_social}
        </td>

        <td align="right">
        <img src="cid:logo_empresa" style="height:250px;">
        </td>
        </tr>
        </table>

        <div style="color:#6b7280;font-size:14px;margin-bottom:25px">
        Período: <b>{periodo_relatorio}</b> &nbsp;&nbsp;|&nbsp;&nbsp;
        Comparação: <b>{periodo_comparacao}</b>
        </div>

        <table width="100%" cellspacing="15">
        <tr>

        <td width="25%" style="background:#0b0f2b;color:white;padding:22px;border-radius:10px;text-align:center">
        <div style="font-size:12px;color:#cbd5e1">VEÍCULOS</div>
        <div style="font-size:34px;font-weight:bold;margin-top:6px">{veiculos}</div>
        <div style="font-size:14px;color:{cor_variacao(var_veiculos)}">
        {formatar_variacao(var_veiculos)}
        </div>
        </td>

        <td width="25%" style="background:#0b0f2b;color:white;padding:22px;border-radius:10px;text-align:center">
        <div style="font-size:12px;color:#cbd5e1">KM RODADOS</div>
        <div style="font-size:34px;font-weight:bold;margin-top:6px">{km_total:,.0f}</div>
        <div style="font-size:14px;color:{cor_variacao(var_km)}">
        {formatar_variacao(var_km)}
        </div>
        </td>

        <td width="25%" style="background:#0b0f2b;color:white;padding:22px;border-radius:10px;text-align:center">
        <div style="font-size:12px;color:#cbd5e1">LITROS</div>
        <div style="font-size:34px;font-weight:bold;margin-top:6px">{litros:,.0f}</div>
        <div style="font-size:14px;color:{cor_variacao(var_litros)}">
        {formatar_variacao(var_litros)}
        </div>
        </td>

        <td width="25%" style="background:#0b0f2b;color:white;padding:22px;border-radius:10px;text-align:center">
        <div style="font-size:12px;color:#cbd5e1">EFICIÊNCIA</div>
        <div style="font-size:34px;font-weight:bold;margin-top:6px">{consumo_medio} km/l</div>
        <div style="font-size:14px;color:{cor_variacao(var_consumo)}">
        {formatar_variacao(var_consumo)}
        </div>
        </td>

        </tr>
        </table>


        </div>


        <h3 style="margin-top:30px;color:#0b0f2b">Eventos de Condução</h3>

        <div style="background:white;padding:20px;border-radius:10px">

        <table width="100%" style="font-size:15px">

        <tr>
        <td>Freio Brusco</td>
        <td align="right"><b>{freio}</b></td>
        </tr>

        <tr>
        <td>Kickdown</td>
        <td align="right"><b>{kickdown}</b></td>
        </tr>

        <tr>
        <td>RPM Amarelo</td>
        <td align="right"><b>{rpm_amarelo}</b></td>
        </tr>

        <tr>
        <td>RPM Vermelho</td>
        <td align="right"><b>{rpm_vermelho}</b></td>
        </tr>

        <tr>
        <td>Velocidade &gt; 80km</td>
        <td align="right"><b>{vel80}</b></td>
        </tr>

        <tr>
        <td>Velocidade chuva &gt; 60km</td>
        <td align="right"><b>{vel60}</b></td>
        </tr>

        </table>

        </div>


        <h3 style="margin-top:30px;color:#0b0f2b">Ociosidade</h3>

        <div style="background:white;padding:20px;border-radius:10px">

        <div style="font-size:16px">
        Tempo ocioso: <b>{ocioso_tempo}</b>
        </div>

        <div style="margin-top:8px;font-size:16px">
        Combustível gasto parado: <b>{combustivel_ocioso}</b>
        </div>

        <div style="margin-top:8px;font-size:16px">
        Valor em Reais gasto de combustível: <b>R${total_reais}</b>
        </div>

        </div>

        <h3 style="margin-top:30px;color:#0b0f2b">Segurança</h3>

        <div style="background:white;padding:20px;border-radius:10px">

        <div style="font-size:16px">
        Eventos: <b>{eventos}</b>
        <span style="color:{cor_variacao(var_eventos)}">
        ({formatar_variacao(var_eventos)})
        </span>
        </div>

        <div style="margin-top:8px;font-size:16px">
        Eventos / 100km: <b>{eventos_100km}</b>
        <span style="color:{cor_variacao(var_eventos_100km)}">
        ({formatar_variacao(var_eventos_100km)})
        </span>
        </div>


        <h3 style="margin-top:30px;color:#0b0f2b">Mapa de Eventos</h3>

        <div style="background:white;padding:15px;border-radius:10px;text-align:center">
        {mapa_html}
        </div>

        <h3 style="margin-top:30px;color:#0b0f2b">
        Top melhores placas com eficiência
        </h3>

        <div style="background:white;padding:15px;border-radius:10px;text-align:center">
        <img src="cid:grafico_piores" style="max-width:100%">
        </div>

        <h3 style="margin-top:30px;color:#0b0f2b">
        Top piores placas com eficiência
        </h3>

        <div style="background:white;padding:15px;border-radius:10px;text-align:center">
        <img src="cid:grafico_melhores" style="max-width:100%">
        </div>

        </body>
        """


        # ===============================

        remetente="lucasfarre08@gmail.com"
        senha="niim wrus yilq cdee"
        destinatario="lucasfarre08@gmail.com"

        msg=MIMEMultipart("related")
        msg["Subject"]=f"Relatório - {razao_social}"
        msg["From"]=remetente
        msg["To"]=destinatario

        msg.attach(MIMEText(html,"html"))

        # LOGO
        with open("C:/Users/adminwialon/Desktop/nstech_logo.png", "rb") as f:
            logo = MIMEImage(f.read())
            logo.add_header("Content-ID", "<logo_empresa>")
            msg.attach(logo)

        # LISTA DE IMAGENS (AGORA COMPLETA)
        imagens = [
            ("grafico_melhores", buffer_melhores),
            ("grafico_piores", buffer_piores),
        ]

        # ANEXAR IMAGENS
        for nome, buffer in imagens:
            if buffer:  # evita erro se for None
                buffer.seek(0)
                img = MIMEImage(buffer.read())
                img.add_header("Content-ID", f"<{nome}>")
                msg.attach(img)

        # MAPA
        if buffer_mapa:
            buffer_mapa.seek(0)
            img = MIMEImage(buffer_mapa.read())
            img.add_header("Content-ID","<mapa_eventos>")
            msg.attach(img)

        # ENVIO
        server = smtplib.SMTP("smtp.gmail.com",587)
        server.starttls()
        server.login(remetente,senha)
        server.sendmail(remetente,[destinatario],msg.as_string())
        server.quit()

        print("Email enviado:", razao_social)