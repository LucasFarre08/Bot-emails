

import mysql.connector 
import smtplib
from email.mime.text import MIMEText

# conexão com banco
conexao = mysql.connector.connect(
    host="localhost",
    user="root",
    password="12345",
    database="telemetria_db"
)

cursor = conexao.cursor()

cursor.execute("SELECT `grouping`, quilometragem FROM viagens LIMIT 5")

dados = cursor.fetchall()

# montar texto do email
mensagem_texto = "Relatório de Viagens\n\n"

for placa, km in dados:
    mensagem_texto += f"Placa: {placa} | KM: {km}\n"

cursor.close()
conexao.close()

# email
remetente = "lucasfarre08@gmail.com"
senha = "niim wrus yilq cdee"
destinatario = "lucas.figueredo" \
"@buonnytech.com.br"

msg = MIMEText(mensagem_texto)

msg["Subject"] = "Relatório Automático"
msg["From"] = remetente
msg["To"] = destinatario

# criar conexão SMTP
server = smtplib.SMTP("smtp.gmail.com", 587)

# ativar log SMTP
server.set_debuglevel(1)

server.starttls()

server.login(remetente, senha)

server.sendmail(remetente, [destinatario], msg.as_string())

server.quit()

print("Email enviado")