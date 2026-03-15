import mysql.connector
import smtplib
import matplotlib.pyplot as plt
import io
import sys
from datetime import datetime
from datetime import date
from datetime import timedelta
from staticmap import StaticMap, CircleMarker
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage


# ===============================
# FUNÇÕES AUXILIARES
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
# DEFINIR PERÍODO MANUAL
# ===============================

inicio_ultimo_mes = date(2026, 1, 1)
fim_ultimo_mes = date(2026, 1, 31)

# período anterior automático
dias_periodo = (fim_ultimo_mes - inicio_ultimo_mes).days

inicio_mes_anterior = inicio_ultimo_mes - timedelta(days=dias_periodo)
fim_mes_anterior = inicio_ultimo_mes

periodo_relatorio = inicio_ultimo_mes.strftime("%d/%m/%Y") + " - " + fim_ultimo_mes.strftime("%d/%m/%Y")
periodo_comparacao = inicio_mes_anterior.strftime("%d/%m/%Y") + " - " + fim_mes_anterior.strftime("%d/%m/%Y")


# ===============================
# CONEXÃO BANCO
# ===============================

conexao = mysql.connector.connect(
    host="localhost",
    user="root",
    password="12345",
    database="telemetria_db"
)

cursor = conexao.cursor()

# ===============================
# VIAGENS - ÚLTIMO MÊS
# ===============================

cursor.execute("""
SELECT COUNT(DISTINCT `grouping`)
FROM viagens
WHERE `inicio` >= %s AND `inicio` < %s
""", (inicio_ultimo_mes, fim_ultimo_mes))
veiculos = cursor.fetchone()[0] or 0

cursor.execute("""
SELECT SUM(`quilometragem`)
FROM viagens
WHERE `inicio` >= %s AND `inicio` < %s
""", (inicio_ultimo_mes, fim_ultimo_mes))
km_total = cursor.fetchone()[0] or 0

cursor.execute("""
SELECT SUM(`litros_consumidos`)
FROM viagens
WHERE `inicio` >= %s AND `inicio` < %s
""", (inicio_ultimo_mes, fim_ultimo_mes))
litros = cursor.fetchone()[0] or 0

consumo_medio = round(km_total / litros, 2) if litros else 0


# ===============================
# VIAGENS - MÊS ANTERIOR
# ===============================

cursor.execute("""
SELECT COUNT(DISTINCT `grouping`)
FROM viagens
WHERE `inicio` >= %s AND `inicio` < %s
""", (inicio_mes_anterior, fim_mes_anterior))
veiculos_ant = cursor.fetchone()[0] or 0

cursor.execute("""
SELECT SUM(`quilometragem`)
FROM viagens
WHERE `inicio` >= %s AND `inicio` < %s
""", (inicio_mes_anterior, fim_mes_anterior))
km_total_ant = cursor.fetchone()[0] or 0

cursor.execute("""
SELECT SUM(`litros_consumidos`)
FROM viagens
WHERE `inicio` >= %s AND `inicio` < %s
""", (inicio_mes_anterior, fim_mes_anterior))
litros_ant = cursor.fetchone()[0] or 0

consumo_medio_ant = round(km_total_ant / litros_ant, 2) if litros_ant else 0


# ===============================
# SEGURANÇA - ÚLTIMO MÊS
# ===============================

cursor.execute("""
SELECT COUNT(*)
FROM seguranca
WHERE `data` >= %s AND `data` < %s
""", (inicio_ultimo_mes, fim_ultimo_mes))
eventos = cursor.fetchone()[0] or 0

eventos_100km = round((eventos / km_total) * 100, 2) if km_total else 0


# ===============================
# SEGURANÇA - MÊS ANTERIOR
# ===============================

cursor.execute("""
SELECT COUNT(*)
FROM seguranca
WHERE `data` >= %s AND `data` < %s
""", (inicio_mes_anterior, fim_mes_anterior))
eventos_ant = cursor.fetchone()[0] or 0

eventos_100km_ant = round((eventos_ant / km_total_ant) * 100, 2) if km_total_ant else 0


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
# GRÁFICO
# ===============================

cursor.execute("""
SELECT `grouping`, SUM(quilometragem)
FROM viagens
WHERE `inicio` >= %s AND `inicio` < %s
GROUP BY `grouping`
ORDER BY SUM(quilometragem) DESC
LIMIT 5
""", (inicio_ultimo_mes, fim_ultimo_mes))

dados = cursor.fetchall()


# ===============================
# MAPA
# ===============================

cursor.execute("""
SELECT coordenadas
FROM seguranca
WHERE coordenadas IS NOT NULL
AND `data` >= %s AND `data` < %s
LIMIT 500
""", (inicio_ultimo_mes, fim_ultimo_mes))

coords = cursor.fetchall()

cursor.close()
conexao.close()


# ===============================
# COORDENADAS
# ===============================

latitudes = []
longitudes = []

for c in coords:
    try:
        lat, lon = c[0].split(",")
        latitudes.append(float(lat.strip()))
        longitudes.append(float(lon.strip()))
    except:
        pass


# ===============================
# GERAR MAPA
# ===============================

mapa = StaticMap(900, 500)

for lat, lon in zip(latitudes, longitudes):
    mapa.add_marker(CircleMarker((lon, lat), "#ff3333", 5))

if len(latitudes) > 0:

    imagem = mapa.render()

    buffer_mapa = io.BytesIO()
    imagem.save(buffer_mapa, format="PNG")
    buffer_mapa.seek(0)

else:
    buffer_mapa = None

mapa_html = ""

if buffer_mapa:
    mapa_html = '<img src="cid:mapa_eventos">'
else:
    mapa_html = "<p>Sem eventos com coordenadas no período.</p>"


# ===============================
# GERAR GRÁFICO
# ===============================

placas = [d[0] for d in dados]
kms = [d[1] for d in dados]

plt.figure(figsize=(6,4))
plt.plot(placas, kms, marker="o")
plt.title(f"Top 5 Placas com Mais KM - {periodo_relatorio}")
plt.xlabel("Placa")
plt.ylabel("KM Rodado")
plt.grid(True)

buffer = io.BytesIO()
plt.savefig(buffer, format="png", bbox_inches="tight")
plt.close()

buffer.seek(0)


# ===============================
# HTML
# ===============================

html = f"""
<body style="font-family:Arial;background:#f4f6f8;padding:30px">

<div style="max-width:1000px;margin:auto">

<h1 style="color:#0b0f2b;margin-bottom:5px">🚛 Relatório Operacional da Frota</h1>

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

</div>

</body>
"""

# ===============================
# ENVIO EMAIL
# ===============================

remetente = "lucasfarre08@gmail.com"
senha = "niim wrus yilq cdee"
destinatario = "lucasfarre08@gmail.com"

msg = MIMEMultipart("related")

msg["Subject"] = f"Relatório Operacional - {periodo_relatorio}"
msg["From"] = remetente
msg["To"] = destinatario

msg.attach(MIMEText(html, "html"))

grafico = MIMEImage(buffer.read())
grafico.add_header("Content-ID", "<grafico_km>")
msg.attach(grafico)

if buffer_mapa:
    mapa_img = MIMEImage(buffer_mapa.read())
    mapa_img.add_header("Content-ID", "<mapa_eventos>")
    msg.attach(mapa_img)

server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()

server.login(remetente, senha)

server.sendmail(remetente, [destinatario], msg.as_string())

server.quit()

print("Email enviado")