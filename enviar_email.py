import smtplib
from email.mime.text import MIMEText

remetente = "lucasfarre08@gmail.com"
senha = "niim wrus yilq cdee"
destinatario = "lucasfarre08@gmail.com"

msg = MIMEText("Teste Python funcionando")

msg["Subject"] = "Teste email"
msg["From"] = remetente
msg["To"] = destinatario

server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()

server.login(remetente, senha)

server.sendmail(remetente, destinatario, msg.as_string())

server.quit()

print("Email enviado!")