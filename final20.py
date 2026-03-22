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


def contar_eventos(cursor, tabela, id_cliente, inicio, fim):

    cursor.execute(f"""
        SELECT COUNT(*)
        FROM {tabela} t
        JOIN frotas f
        ON f.nome COLLATE utf8mb4_unicode_ci =
           t.grouping COLLATE utf8mb4_unicode_ci
        WHERE f.IDcliente = %s
        AND t.data >= %s
        AND t.data < %s
    """,(id_cliente,inicio,fim))

    valor = cursor.fetchone()[0]
    return valor or 0

def contar_freio(cursor, tabela, id_cliente, inicio, fim):

    cursor.execute(f"""
        SELECT COUNT(*)
        FROM {tabela} t
        JOIN frotas f
        ON f.nome COLLATE utf8mb4_unicode_ci =
           t.grouping COLLATE utf8mb4_unicode_ci
        WHERE f.IDcliente = %s
        AND t.ativado >= %s
        AND t.ativado< %s
    """,(id_cliente,inicio,fim))

    valor = cursor.fetchone()[0]
    return valor or 0

def contar_kickdown(cursor, tabela, id_cliente, inicio, fim):

    cursor.execute(f"""
        SELECT COUNT(*)
        FROM {tabela} t
        JOIN frotas f
        ON f.nome COLLATE utf8mb4_unicode_ci =
           t.grouping COLLATE utf8mb4_unicode_ci
        WHERE f.IDcliente = %s
        AND t.ativado >= %s
        AND t.ativado < %s
    """,(id_cliente,inicio,fim))

    valor = cursor.fetchone()[0]
    return valor or 0
def contar_embreagem(cursor, tabela, id_cliente, inicio, fim):

    cursor.execute(f"""
        SELECT COUNT(*)
        FROM {tabela} t
        JOIN frotas f
        ON f.nome COLLATE utf8mb4_unicode_ci =
           t.grouping COLLATE utf8mb4_unicode_ci
        WHERE f.IDcliente = %s
        AND t.ativado >= %s
        AND t.ativado < %s
    """,(id_cliente,inicio,fim))

    valor = cursor.fetchone()[0]
    return valor or 0

def contar_velocidade(cursor, tabela, id_cliente, inicio, fim):

    cursor.execute(f"""
        SELECT COUNT(*)
        FROM {tabela} t
        JOIN frotas f
        ON f.nome COLLATE utf8mb4_unicode_ci =
           t.grouping COLLATE utf8mb4_unicode_ci
        WHERE f.IDcliente = %s
        AND t.ativado >= %s
        AND t.ativado < %s
    """,(id_cliente,inicio,fim))

    valor = cursor.fetchone()[0]
    return valor or 0

def contar_velocidade_chuva(cursor, tabela, id_cliente, inicio, fim):

    cursor.execute(f"""
        SELECT COUNT(*)
        FROM {tabela} t
        JOIN frotas f
        ON f.nome COLLATE utf8mb4_unicode_ci =
           t.grouping COLLATE utf8mb4_unicode_ci
        WHERE f.IDcliente = %s
        AND t.ativado >= %s
        AND t.ativado < %s
    """,(id_cliente,inicio,fim))

    valor = cursor.fetchone()[0]
    return valor or 0

def contar_rpm_vermelho(cursor, tabela, id_cliente, inicio, fim):

    cursor.execute(f"""
        SELECT COUNT(*)
        FROM {tabela} t
        JOIN frotas f
        ON f.nome COLLATE utf8mb4_unicode_ci =
           t.grouping COLLATE utf8mb4_unicode_ci
        WHERE f.IDcliente = %s
        AND t.ativado >= %s
        AND t.ativado < %s
    """,(id_cliente,inicio,fim))

    valor = cursor.fetchone()[0]
    return valor or 0
def contar_rpm_amarelo(cursor, tabela, id_cliente, inicio, fim):

    cursor.execute(f"""
        SELECT COUNT(*)
        FROM {tabela} t
        JOIN frotas f
        ON f.nome COLLATE utf8mb4_unicode_ci =
           t.grouping COLLATE utf8mb4_unicode_ci
        WHERE f.IDcliente = %s
        AND t.ativado >= %s
        AND t.ativado < %s
    """,(id_cliente,inicio,fim))

    valor = cursor.fetchone()[0]

    return valor or 0

# ===============================
# FUNÇÕES
# ===============================

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
    # EVENTOS (DISTRIBUIÇÃO)
    # ===============================
    eventos_dist = contar_eventos_dados(
        cursor,
        id_cliente,
        inicio_ultimo_mes,
        fim_ultimo_mes
    ) or []

    eventos_dict = {
        "Frenagem Brusca": 0,
        "Aceleração Brusca": 0,
        "Curva Brusca": 0,
        "Condução Agressiva": 0
    }

    for nome, total in eventos_dist:
        if nome in eventos_dict:
            eventos_dict[nome] += total

    labels = list(eventos_dict.keys())
    valores = list(eventos_dict.values())

    if sum(valores) == 0:
        labels = ["Sem eventos"]
        valores = [1]



# ===============================
# VIAGENS
# ===============================

    cursor.execute("""
        SELECT COUNT(DISTINCT v.grouping),
               SUM(v.quilometragem),
               SUM(v.litros_consumidos)
        FROM viagens v
        JOIN frotas f 
ON f.nome COLLATE utf8mb4_unicode_ci =
   v.grouping COLLATE utf8mb4_unicode_ci
        WHERE f.IDcliente = %s
        AND v.inicio >= %s
        AND v.inicio < %s
    """,(id_cliente,inicio_ultimo_mes,fim_ultimo_mes))

    veiculos, km_total, litros = cursor.fetchone()

    veiculos = veiculos or 0
    km_total = km_total or 0
    litros = litros or 0

    consumo_medio = round(km_total/litros,2) if litros else 0

    if km_total == 0:
        print("Sem dados no período")
        


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
# EVENTOS SEGURANÇA
# ===============================

    cursor.execute("""
        SELECT COUNT(*)
        FROM seguranca s
        JOIN frotas f 
ON f.nome COLLATE utf8mb4_unicode_ci =
   s.grouping COLLATE utf8mb4_unicode_ci
        WHERE f.IDcliente = %s
        AND s.data >= %s
        AND s.data < %s
    """,(id_cliente,inicio_ultimo_mes,fim_ultimo_mes))

    eventos = cursor.fetchone()[0] or 0

    eventos_100km = round((eventos/km_total)*100,2) if km_total else 0

    


# ===============================
# VELOCIDADE 80KM
# ===============================

    cursor.execute("""
    SELECT COUNT(*)
    FROM velocidade_80km s
    JOIN frotas f
    ON f.nome COLLATE utf8mb4_unicode_ci =
       s.grouping COLLATE utf8mb4_unicode_ci
    WHERE f.IDcliente = %s
    AND s.ativado >= %s
    AND s.ativado < %s
""",(id_cliente,inicio_ultimo_mes,fim_ultimo_mes))

    vel80_eventos = cursor.fetchone()[0] or 0


# ===============================
# EVENTOS DE CONDUÇÃO
# ===============================

    freio = contar_freio(cursor,"freio",id_cliente,inicio_ultimo_mes,fim_ultimo_mes)
    kickdown = contar_kickdown(cursor,"kickdown",id_cliente,inicio_ultimo_mes,fim_ultimo_mes)
    rpm_amarelo = contar_rpm_amarelo(cursor,"rpm_amarelo",id_cliente,inicio_ultimo_mes,fim_ultimo_mes)
    rpm_vermelho = contar_rpm_vermelho(cursor,"rpm_vermelho",id_cliente,inicio_ultimo_mes,fim_ultimo_mes)
    vel80 = contar_velocidade(cursor,"velocidade_80km",id_cliente,inicio_ultimo_mes,fim_ultimo_mes)
    vel60 = contar_velocidade_chuva(cursor,"velocidade_chuva_60km",id_cliente,inicio_ultimo_mes,fim_ultimo_mes)
    embreagem = contar_embreagem(cursor,"embreagem",id_cliente,inicio_ultimo_mes,fim_ultimo_mes)


# ===============================
# OCIOSIDADE
# ===============================

    cursor.execute("""
SELECT 
    CONCAT(
        ROUND(SUM(TIME_TO_SEC(IFNULL(duracao,'00:00:00'))) / 3600,2),
        ' horas'
    ) AS horas_ociosas,
    
    SUM(IFNULL(combustivel_gasto,0)) AS combustivel_ociosidade

FROM ociosidade o

JOIN frotas f 
ON f.nome COLLATE utf8mb4_unicode_ci =
   o.grouping COLLATE utf8mb4_unicode_ci

WHERE f.IDcliente = %s
AND o.ativado >= %s
AND o.ativado < %s
""",(id_cliente,inicio_ultimo_mes,fim_ultimo_mes))

    ocioso_tempo, combustivel_ocioso = cursor.fetchone()

    ocioso_tempo = ocioso_tempo or 0
    combustivel_ocioso = combustivel_ocioso or 0


# ===============================
# TOP KM
# ===============================

    cursor.execute("""
        SELECT v.grouping,
               SUM(IFNULL(v.quilometragem,0))
        FROM viagens v
        JOIN frotas f 
ON f.nome COLLATE utf8mb4_unicode_ci =
   v.grouping COLLATE utf8mb4_unicode_ci
        WHERE f.IDcliente = %s
        AND v.inicio >= %s
        AND v.inicio < %s
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
    # GRÁFICO EVENTOS (CORRETO)
    # ===============================
    plt.figure(figsize=(6,4))

    plt.pie(
        valores,
        labels=labels,
        autopct='%1.1f%%'
    )

    plt.title("Distribuição de Eventos")

    buffer_eventos = io.BytesIO()

    plt.savefig(buffer_eventos, format="png", bbox_inches="tight")

    plt.close()

    buffer_eventos.seek(0)


# ===============================
# GRÁFICO EVENTOS
# ===============================

    
# gráfico
plt.figure(figsize=(6,4))

plt.pie(valores, labels=labels, autopct='%1.1f%%')

buffer_eventos = io.BytesIO()

plt.savefig(buffer_eventos, format="png", bbox_inches="tight")

plt.close()

buffer_eventos.seek(0)


# ===============================
# TRATAMENTO SEM DADOS
# ===============================

if sum(valores) == 0:
    labels = ["Sem eventos"]
    valores = [1]


# ===============================
# GRÁFICO PIZZA
# ===============================

plt.figure(figsize=(6,4))

plt.pie(
    valores,
    labels=labels,
    autopct='%1.1f%%'
)

plt.title("Distribuição de Eventos")

buffer_eventos = io.BytesIO()

plt.savefig(buffer_eventos, format="png", bbox_inches="tight")

plt.close()

buffer_eventos.seek(0)
# GRÁFICO KM
plt.figure(figsize=(6,4))
plt.bar(placas, kms)
plt.title("Top 5 Veículos por KM")
buffer_km = io.BytesIO()
plt.savefig(buffer_km, format="png", bbox_inches="tight")
plt.close()
buffer_km.seek(0)


# ===============================
# INSIGHT AUTOMÁTICO 🔥
# ===============================

if sum(valores) > 0:
    max_valor = max(valores)
    idx = valores.index(max_valor)

    top_evento = labels[idx]
    perc = round((max_valor / sum(valores)) * 100, 1)

    insight_evento = f"O principal evento foi {top_evento}, representando {perc}% do total."
else:
    insight_evento = "Não houve eventos registrados no período."


# ===============================
# GRÁFICO RPM
# ===============================

    plt.figure(figsize=(6,4))
    plt.bar(["RPM Amarelo","RPM Vermelho"],
            [rpm_amarelo,rpm_vermelho],
            color=["#f59e0b","#ef4444"])

    plt.title("Eventos RPM")

    buffer_rpm=io.BytesIO()
    plt.savefig(buffer_rpm,format="png",bbox_inches="tight")
    plt.close()
    buffer_rpm.seek(0)


# ===============================
# MAPA
# ===============================

    cursor.execute("""
        SELECT s.coordenadas
        FROM seguranca s
        JOIN frotas f 
ON f.nome COLLATE utf8mb4_unicode_ci =
   s.grouping COLLATE utf8mb4_unicode_ci
        WHERE f.IDcliente = %s
        AND s.data >= %s
        AND s.data < %s
        AND s.coordenadas IS NOT NULL
        LIMIT 300
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

        mapa_html='<img src="cid:mapa_eventos">'

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

    </div>


    <h3 style="margin-top:30px;color:#0b0f2b">Mapa de Eventos</h3>

    <div style="background:white;padding:15px;border-radius:10px;text-align:center">
    {mapa_html}
    </div>


    <h3 style="margin-top:30px;color:#0b0f2b">Top KM por Placa</h3>

    <div style="background:white;padding:15px;border-radius:10px;text-align:center">
    <img src="cid:grafico_km" style="max-width:100%">
    </div>


    <h3 style="margin-top:30px;color:#0b0f2b">Distribuição de Eventos</h3>

    <div style="background:white;padding:15px;border-radius:10px;text-align:center">
    <img src="cid:grafico_eventos" style="max-width:100%">
    </div>


    <h3 style="margin-top:30px;color:#0b0f2b">RPM do Motor</h3>

    <div style="background:white;padding:15px;border-radius:10px;text-align:center">
    <img src="cid:grafico_rpm" style="max-width:100%">
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
    msg["Subject"]=f"Relatório - {razao_social}"
    msg["From"]=remetente
    msg["To"]=destinatario

    msg.attach(MIMEText(html,"html"))

    for nome,buffer in [
        ("grafico_km",buffer_km),
        ("grafico_eventos",buffer_eventos),
        ("grafico_rpm",buffer_rpm)
    ]:
        img=MIMEImage(buffer.read())
        img.add_header("Content-ID",f"<{nome}>")
        msg.attach(img)

    if buffer_mapa:
        img=MIMEImage(buffer_mapa.read())
        img.add_header("Content-ID","<mapa_eventos>")
        msg.attach(img)

    server=smtplib.SMTP("smtp.gmail.com",587)
    server.starttls()
    server.login(remetente,senha)
    server.sendmail(remetente,[destinatario],msg.as_string())
    server.quit()

    print("Email enviado:",razao_social)

cursor.close()
conexao.close()