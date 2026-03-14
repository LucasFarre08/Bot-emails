import mysql.connector

conexao = mysql.connector.connect(
    host="localhost",
    user="root",
    password="12345",
    database="telemetria_db"
)

cursor = conexao.cursor()

cursor.execute("SELECT `grouping`, quilometragem FROM viagens LIMIT 5")

resultado = cursor.fetchall()

for linha in resultado:
    print(linha)

cursor.close()
conexao.close()