import mysql.connector
import smtplib
import matplotlib.pyplot as plt
import io
from datetime import date
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
# DEFINIR PERÍODOS
# ===============================

hoje = date.today()

primeiro_dia_mes_atual = hoje.replace(day=1)
fim_ultimo_mes = primeiro_dia_mes_atual

if primeiro_dia_mes_atual.month == 1:
    inicio_ultimo_mes = date(primeiro_dia_mes_atual.year - 1, 12, 1)
else:
    inicio_ultimo_mes = date(primeiro_dia_mes_atual.year, primeiro_dia_mes_atual.month - 1, 1)

if inicio_ultimo_mes.month == 1:
    inicio_mes_anterior = date(inicio_ultimo_mes.year - 1, 12, 1)
else:
    inicio_mes_anterior = date(inicio_ultimo_mes.year, inicio_ultimo_mes.month - 1, 1)

fim_mes_anterior = inicio_ultimo_mes

periodo_relatorio = inicio_ultimo_mes.strftime("%m/%Y")
periodo_comparacao = inicio_mes_anterior.strftime("%m/%Y")


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
<h2>Relatório Operacional da Frota</h2>

<p><b>Período:</b> {periodo_relatorio} | <b>Comparação:</b> {periodo_comparacao}</p>

<h3>Indicadores Operacionais</h3>

Veículos: {veiculos} ({formatar_variacao(var_veiculos)})<br>
KM Rodados: {km_total:,.0f} ({formatar_variacao(var_km)})<br>
Litros Consumidos: {litros:,.0f} ({formatar_variacao(var_litros)})<br>
Eficiência: {consumo_medio} km/l ({formatar_variacao(var_consumo)})

<h3>Segurança</h3>

Eventos: {eventos} ({formatar_variacao(var_eventos)})<br>
Eventos / 100km: {eventos_100km} ({formatar_variacao(var_eventos_100km)})

<h3>Mapa de Eventos</h3>
{mapa_html}

<h3>Top KM por Placa</h3>
<img src="cid:grafico_km">
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