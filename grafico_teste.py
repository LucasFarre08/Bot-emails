import mysql.connector
import matplotlib.pyplot as plt

# conexão com banco
conexao = mysql.connector.connect(
    host="localhost",
    user="root",
    password="12345",
    database="telemetria_db"
)

cursor = conexao.cursor()

cursor.execute("""
SELECT `grouping`, SUM(quilometragem) as km
FROM viagens
GROUP BY `grouping`
ORDER BY km DESC
LIMIT 5
""")

dados = cursor.fetchall()

cursor.close()
conexao.close()

placas = []
kms = []

for placa, km in dados:
    placas.append(placa)
    kms.append(km)

# criar gráfico
plt.figure()

plt.plot(placas, kms, marker='o')

plt.title("Top 5 Placas com Mais KM")
plt.xlabel("Placa")
plt.ylabel("KM Rodado")

plt.grid(True)

# salvar imagem
plt.savefig("grafico_km.png")

plt.close()

print("Gráfico criado")