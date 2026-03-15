import matplotlib
matplotlib.use('Agg')
import mysql.connector
import smtplib
import matplotlib.pyplot as plt
import io
from datetime import date, timedelta
from staticmap import StaticMap, CircleMarker
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# ===============================
# FUNÇÕES
# ===============================

def variacao_percentual(atual, anterior):
    if anterior in (0, None):
        return 0
    return round(((atual - anterior) / anterior) * 100, 2)

def formatar_variacao(valor):
    if valor > 0:
        return f"+{valor}%"
    return f"{valor}%"

def cor_variacao(valor):
    if valor > 0:
        return "#22c55e"
    elif valor < 0:
        return "#ef4444"
    return "#cbd5e1"

# ===============================
# PERÍODO
# ===============================

inicio_ultimo_mes = date(2026,1,1)
fim_ultimo_mes = date(2026,1,31)

dias_periodo = (fim_ultimo_mes - inicio_ultimo_mes).days

inicio_mes_anterior = inicio_ultimo_mes - timedelta(days=dias_periodo)
fim_mes_anterior = inicio_ultimo_mes

periodo_relatorio = f"{inicio_ultimo_mes.strftime('%d/%m/%Y')} - {fim_ultimo_mes.strftime('%d/%m/%Y')}"
periodo_comparacao = f"{inicio_mes_anterior.strftime('%d/%m/%Y')} - {fim_mes_anterior.strftime('%d/%m/%Y')}"

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

for cliente_row in clientes:

    id_cliente = cliente_row[0]
    razao_social = cliente_row[1]

    print("Gerando relatório:", razao_social)

    # ===============================
    # MÉTRICAS MÊS ATUAL
    # ===============================

    cursor.execute("""
    SELECT COUNT(DISTINCT v.grouping),
           SUM(v.quilometragem),
           SUM(v.litros_consumidos)
    FROM viagens v
    JOIN frotas f ON f.nome = v.grouping
    WHERE f.IDcliente = %s
    AND v.inicio >= %s AND v.inicio < %s
    """,(id_cliente,inicio_ultimo_mes,fim_ultimo_mes))

    veiculos, km_total, litros = cursor.fetchone()

    veiculos = veiculos or 0
    km_total = km_total or 0
    litros = litros or 0

    consumo_medio = round(km_total/litros,2) if litros else 0

    # pular clientes sem km
    if km_total == 0:
        print(f"{razao_social} sem dados no período")
        continue

    # ===============================
    # EVENTOS
    # ===============================

    cursor.execute("""
    SELECT COUNT(*)
    FROM seguranca s
    JOIN frotas f ON f.nome = s.grouping
    WHERE f.IDcliente = %s
    AND s.data >= %s AND s.data < %s
    """,(id_cliente,inicio_ultimo_mes,fim_ultimo_mes))

    eventos = cursor.fetchone()[0] or 0
    eventos_100km = round((eventos/km_total)*100,2) if km_total else 0

    # ===============================
    # MÊS ANTERIOR
    # ===============================

    cursor.execute("""
    SELECT COUNT(DISTINCT v.grouping),
           SUM(v.quilometragem),
           SUM(v.litros_consumidos)
    FROM viagens v
    JOIN frotas f ON f.nome = v.grouping
    WHERE f.IDcliente = %s
    AND v.inicio >= %s AND v.inicio < %s
    """,(id_cliente,inicio_mes_anterior,fim_mes_anterior))

    veiculos_ant, km_total_ant, litros_ant = cursor.fetchone()

    veiculos_ant = veiculos_ant or 0
    km_total_ant = km_total_ant or 0
    litros_ant = litros_ant or 0

    consumo_medio_ant = round(km_total_ant/litros_ant,2) if litros_ant else 0

    cursor.execute("""
    SELECT COUNT(*)
    FROM seguranca s
    JOIN frotas f ON f.nome = s.grouping
    WHERE f.IDcliente = %s
    AND s.data >= %s AND s.data < %s
    """,(id_cliente,inicio_mes_anterior,fim_mes_anterior))

    eventos_ant = cursor.fetchone()[0] or 0
    eventos_100km_ant = round((eventos_ant/km_total_ant)*100,2) if km_total_ant else 0

    # ===============================
    # VARIAÇÕES
    # ===============================

    var_veiculos = variacao_percentual(veiculos, veiculos_ant)
    var_km = variacao_percentual(km_total, km_total_ant)
    var_litros = variacao_percentual(litros, litros_ant)
    var_consumo = variacao_percentual(consumo_medio, consumo_medio_ant)
    var_eventos = variacao_percentual(eventos, eventos_ant)
    var_eventos_100km = variacao_percentual(eventos_100km, eventos_100km_ant)

    # ===============================
    # TOP KM
    # ===============================

    cursor.execute("""
    SELECT v.grouping, SUM(IFNULL(v.quilometragem,0))
    FROM viagens v
    JOIN frotas f ON f.nome = v.grouping
    WHERE f.IDcliente = %s
    AND v.inicio >= %s AND v.inicio < %s
    GROUP BY v.grouping
    ORDER BY SUM(v.quilometragem) DESC
    LIMIT 5
    """,(id_cliente,inicio_ultimo_mes,fim_ultimo_mes))

    dados = cursor.fetchall()

    placas = [d[0] for d in dados]
    kms = [d[1] or 0 for d in dados]

    if not placas:
        placas = ["Sem dados"]
        kms = [0]

    # ===============================
    # GRÁFICO
    # ===============================

    plt.figure(figsize=(6,4))
    plt.bar(placas,kms)

    buffer = io.BytesIO()
    plt.savefig(buffer,format="png",bbox_inches="tight")
    plt.close()
    buffer.seek(0)

    # ===============================
    # MAPA
    # ===============================

    cursor.execute("""
    SELECT s.coordenadas
    FROM seguranca s
    JOIN frotas f ON f.nome = s.grouping
    WHERE f.IDcliente = %s
    AND s.coordenadas IS NOT NULL
    AND s.data >= %s AND s.data < %s
    LIMIT 500
    """,(id_cliente,inicio_ultimo_mes,fim_ultimo_mes))

    coords = cursor.fetchall()

    latitudes=[]
    longitudes=[]

    for coord in coords:
        try:
            lat,lon = coord[0].split(",")
            latitudes.append(float(lat))
            longitudes.append(float(lon))
        except:
            pass

    mapa = StaticMap(900,500)

    for lat,lon in zip(latitudes,longitudes):
        mapa.add_marker(CircleMarker((lon,lat),"#ff3333",5))

    if latitudes:
        imagem = mapa.render()
        buffer_mapa = io.BytesIO()
        imagem.save(buffer_mapa,format="PNG")
        buffer_mapa.seek(0)
        mapa_html = '<img src="cid:mapa_eventos">'
    else:
        buffer_mapa=None
        mapa_html="<p>Sem eventos com coordenadas</p>"

    # ===============================
    # HTML
    # ===============================

    html = f"""
<body style="font-family:Arial;background:#f4f6f8;padding:30px">

<h1>🚛 Relatório Frota - {razao_social}</h1>

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

</div>

<h3 style="margin-top:30px;color:#0b0f2b">Mapa de Eventos</h3>

<div style="background:white;padding:15px;border-radius:10px;text-align:center">
{mapa_html}
</div>

<h3 style="margin-top:30px;color:#0b0f2b">Top KM por Placa</h3>

<div style="background:white;padding:15px;border-radius:10px;text-align:center">
<img src="cid:grafico_km" style="max-width:100%">
</div>

</body>
"""

    # ===============================
    # EMAIL
    # ===============================

    remetente="lucasfarre08@gmail.com"
    senha="niim wrus yilq cdee"
    destinatario="lucasfarre08@gmail.com"

    msg=MIMEMultipart("related")
    msg["Subject"]=f"Relatório Operacional - {razao_social}"
    msg["From"]=remetente
    msg["To"]=destinatario

    msg.attach(MIMEText(html,"html"))

    grafico=MIMEImage(buffer.read())
    grafico.add_header("Content-ID","<grafico_km>")
    msg.attach(grafico)

    if buffer_mapa:
        mapa_img=MIMEImage(buffer_mapa.read())
        mapa_img.add_header("Content-ID","<mapa_eventos>")
        msg.attach(mapa_img)

    server=smtplib.SMTP("smtp.gmail.com",587)
    server.starttls()
    server.login(remetente,senha)
    server.sendmail(remetente,[destinatario],msg.as_string())
    server.quit()

    print("Email enviado:",razao_social)

cursor.close()
conexao.close()