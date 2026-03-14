import mysql.connector
import smtplib
import matplotlib.pyplot as plt
import io
from staticmap import StaticMap, CircleMarker

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage


# conexão com banco
conexao = mysql.connector.connect(
    host="localhost",
    user="root",
    password="12345",
    database="telemetria_db"
)

cursor = conexao.cursor()

# veículos ativos
cursor.execute("SELECT COUNT(DISTINCT `grouping`) FROM viagens")
veiculos = cursor.fetchone()[0]

# km total
cursor.execute("SELECT SUM(`quilometragem`) FROM viagens")
km_total = cursor.fetchone()[0] or 0

# litros consumidos
cursor.execute("SELECT SUM(`litros_consumidos`) FROM viagens")
litros = cursor.fetchone()[0] or 0

# consumo médio
consumo_medio = round(km_total / litros, 2) if litros else 0

# eventos inseguros
cursor.execute("SELECT COUNT(`grouping`) FROM seguranca")
eventos = cursor.fetchone()[0]

# eventos por 100 km
eventos_100km = round((eventos / km_total) * 100, 2) if km_total else 0


# ===============================
# DADOS PARA GRÁFICO
# ===============================
cursor.execute("""
SELECT `grouping`, SUM(quilometragem) as km
FROM viagens
GROUP BY `grouping`
ORDER BY km DESC
LIMIT 5
""")

dados = cursor.fetchall()


# ===============================
# DADOS PARA MAPA
# ===============================
cursor.execute("""
SELECT coordenadas
FROM seguranca
WHERE coordenadas IS NOT NULL
LIMIT 200
""")

coords = cursor.fetchall()

cursor.close()
conexao.close()


# ===============================
# PREPARAR COORDENADAS
# ===============================
latitudes = []
longitudes = []

for c in coords:
    lat, lon = c[0].split(",")
    latitudes.append(float(lat))
    longitudes.append(float(lon))


# ===============================
# GERAR MAPA COM STATICMAP
# ===============================
mapa = StaticMap(800, 400)

for lat, lon in zip(latitudes, longitudes):
    marker = CircleMarker((lon, lat), 'red', 6)
    mapa.add_marker(marker)

imagem = mapa.render()

buffer_mapa = io.BytesIO()
imagem.save(buffer_mapa, format="PNG")
buffer_mapa.seek(0)


# ===============================
# PREPARAR GRÁFICO
# ===============================
placas = []
kms = []

for placa, km in dados:
    placas.append(placa)
    kms.append(km)

plt.figure()

plt.plot(placas, kms, marker="o")

plt.title("Top 5 Placas com Mais KM")
plt.xlabel("Placa")
plt.ylabel("KM Rodado")

plt.grid(True)

buffer = io.BytesIO()
plt.savefig(buffer, format="png")
plt.close()

buffer.seek(0)


# ===============================
# TABELA HTML
# ===============================
linhas = ""

for placa, km in dados:
    linhas += f"""
    <tr>
        <td style="padding:8px;border:1px solid #ddd">{placa}</td>
        <td style="padding:8px;border:1px solid #ddd">{km}</td>
    </tr>
    """


# ===============================
# HTML DO EMAIL
# ===============================
html = f"""
<html>
<body style="font-family:Arial;background:#f4f6f8;padding:20px">

<h2 style="color:#0b0f2b">🚛 Relatório Operacional da Frota</h2>

<h3>Indicadores Operacionais</h3>

<table width="100%" cellspacing="10">
<tr>

<td align="center" style="background:#0b0f2b;color:white;padding:20px;border-radius:10px">
<div style="font-size:12px;color:#cbd5e1">VEÍCULOS</div>
<div style="font-size:26px;font-weight:bold">{veiculos}</div>
</td>

<td align="center" style="background:#0b0f2b;color:white;padding:20px;border-radius:10px">
<div style="font-size:12px;color:#cbd5e1">KM RODADOS</div>
<div style="font-size:26px;font-weight:bold">{km_total:,.0f}</div>
</td>

<td align="center" style="background:#0b0f2b;color:white;padding:20px;border-radius:10px">
<div style="font-size:12px;color:#cbd5e1">LITROS CONSUMIDOS</div>
<div style="font-size:26px;font-weight:bold">{litros:,.0f}</div>
</td>

<td align="center" style="background:#0b0f2b;color:white;padding:20px;border-radius:10px">
<div style="font-size:12px;color:#cbd5e1">EFICIÊNCIA</div>
<div style="font-size:26px;font-weight:bold">{consumo_medio} km/l</div>
</td>

</tr>
</table>

<h3>Indicadores de Segurança</h3>

<ul>
<li>Total de eventos inseguros: <b>{eventos}</b></li>
<li>Eventos por 100 km: <b>{eventos_100km}</b></li>
</ul>

<h3>Mapa de Eventos Inseguros</h3>
<img src="cid:mapa_eventos">

<br><br>

<h3>Gráfico de KM por Placa</h3>
<img src="cid:grafico_km">

<br><br>

<h3>Top Placas por Quilometragem</h3>

<table style="border-collapse:collapse;width:60%">
<tr style="background:#0b0f2b;color:white">
<th style="padding:8px;border:1px solid #ddd">Placa</th>
<th style="padding:8px;border:1px solid #ddd">KM</th>
</tr>

{linhas}

</table>

</body>
</html>
"""


# ===============================
# ENVIO EMAIL
# ===============================
remetente = "lucasfarre08@gmail.com"
senha = "niim wrus yilq cdee"
destinatario = "lucasfarre08@gmail.com"

msg = MIMEMultipart("related")

msg["Subject"] = "Relatório Operacional da Frota"
msg["From"] = remetente
msg["To"] = destinatario

msg.attach(MIMEText(html, "html"))

grafico = MIMEImage(buffer.read())
grafico.add_header("Content-ID", "<grafico_km>")
msg.attach(grafico)

mapa_img = MIMEImage(buffer_mapa.read())
mapa_img.add_header("Content-ID", "<mapa_eventos>")
msg.attach(mapa_img)

server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()
server.login(remetente, senha)

server.sendmail(remetente, [destinatario], msg.as_string())

server.quit()

print("Email enviado")