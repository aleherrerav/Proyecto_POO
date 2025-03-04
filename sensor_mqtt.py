import paho.mqtt.client as mqtt
import json
from datetime import datetime
import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import MaxNLocator
import numpy as np  # Importamos numpy para calcular media y desviación estándar
import os

class SensorMQTTClient:
    """Clase que maneja la conexión con el broker MQTT y la recepción de mensajes del sensor."""
    
    def __init__(self, broker, topic, gui):
        """Inicializa el cliente MQTT y lo vincula con la interfaz gráfica."""
        self.broker = broker
        self.topic = topic
        self.client = mqtt.Client()  # Creamos una instancia del cliente MQTT
        self.client.on_message = self.on_message  # Definimos la función a ejecutar cuando se recibe un mensaje
        self.gui = gui  

    def connect(self):
        """Conecta el cliente MQTT al broker y se suscribe al tópico del sensor."""
        self.client.connect(self.broker, 1883, 60)  # Conexión al broker en el puerto 1883
        self.client.subscribe(self.topic)  # Nos suscribimos al tópico donde se publican los datos del sensor
        print(f"Conectado al broker {self.broker}, suscrito al tópico {self.topic}")

    def on_message(self, client, userdata, msg):
        """Se ejecuta cuando se recibe un mensaje. Convierte los datos JSON en un objeto Python."""
        try:
            data = json.loads(msg.payload.decode().strip())  # Decodificamos el mensaje recibido en formato JSON
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Registramos la hora en que llega el dato
            sensor_data = SensorData(float(data.get("temperatura", 0)), timestamp, self.gui)
            sensor_data.analizar_temperatura()  # Analizamos la temperatura recibida
        except Exception as e:
            print("Error procesando mensaje:", e)

    def start(self):
        """Inicia el loop de escucha del cliente MQTT."""
        self.client.loop_forever()

class SensorData:
    """Clase que almacena y analiza los datos de temperatura recibidos."""
    
    limites_establecidos = False
    LIMITE_SUPERIOR = None
    LIMITE_INFERIOR = None
    temperaturas_iniciales = []  # Lista para almacenar las primeras 10 mediciones

    def __init__(self, temperatura, timestamp, gui):
        """Inicializa los datos del sensor con temperatura, timestamp e interfaz gráfica."""
        self.temperatura = temperatura
        self.timestamp = timestamp
        self.gui = gui 
    
    def analizar_temperatura(self):
        """Analiza la temperatura recibida y verifica si es una anomalía."""
        print(f"[{self.timestamp}] Temperatura recibida: {self.temperatura}°C")
        self.gui.actualizar_temperatura(self.temperatura, self.timestamp)
        self.gui.actualizar_grafica(self.temperatura)

        if not SensorData.limites_establecidos:
            # Guardamos las primeras 10 mediciones para calcular los límites
            SensorData.temperaturas_iniciales.append(self.temperatura)
            if len(SensorData.temperaturas_iniciales) == 10:
                mu = np.mean(SensorData.temperaturas_iniciales)  # Media de las primeras 10 mediciones
                sigma = np.std(SensorData.temperaturas_iniciales)  # Desviación estándar
                SensorData.LIMITE_SUPERIOR = mu + 3 * sigma
                SensorData.LIMITE_INFERIOR = mu - 3 * sigma
                SensorData.limites_establecidos = True
                print(f"Límites establecidos -> Superior: {SensorData.LIMITE_SUPERIOR:.2f}°C, Inferior: {SensorData.LIMITE_INFERIOR:.2f}°C")
        else:
            # Verificamos si la temperatura está fuera de los límites
            if self.temperatura > SensorData.LIMITE_SUPERIOR or self.temperatura < SensorData.LIMITE_INFERIOR:
                tipo_anomalia = "Temperatura alta" if self.temperatura > SensorData.LIMITE_SUPERIOR else "Temperatura baja"
                print(f"⚠️ Anomalía detectada: {tipo_anomalia} ({self.temperatura}°C)")
                self.guardar_anomalia(tipo_anomalia)
    
    def guardar_anomalia(self, tipo_anomalia):
        """Guarda las anomalías detectadas en un archivo JSON."""
        anomalía = {
            'timestamp': self.timestamp,
            'temperatura': self.temperatura,
            'tipo_anomalia': tipo_anomalia
        }
        try:
            archivo = 'anomalias_detectadas.json'
            datos = []
            
            if os.path.exists(archivo):
                with open(archivo, 'r') as file:
                    datos = json.load(file)
                    if not isinstance(datos, list):
                        datos = []
            
            datos.append(anomalía)
            
            with open(archivo, 'w') as file:
                json.dump(datos, file, indent=4)  # Guardamos la anomalía con formato JSON
            
            print(f"Anomalía guardada en el archivo: {anomalía}")
        except Exception as e:
            print(f"Error al guardar la anomalía: {e}")

class SensorGUI:
    """Clase que gestiona la interfaz gráfica para visualizar los datos del sensor."""
    
    def __init__(self, root):
        """Inicializa la ventana y sus elementos gráficos."""
        self.root = root
        self.root.title("Monitoreo de Temperatura")
        self.root.geometry("600x400")

        self.temp_label = tk.Label(root, text="Temperatura: --°C", font=("Arial", 14))
        self.temp_label.pack(pady=20)

        self.alert_label = tk.Label(root, text="Estado: Esperando datos...", font=("Arial", 12))
        self.alert_label.pack(pady=10)

        self.fig, self.ax = plt.subplots(figsize=(5, 3))
        self.ax.set_title("Gráfica de Control - Temperatura")
        self.ax.set_xlabel("Tiempo")
        self.ax.set_ylabel("Temperatura (°C)")
        self.ax.set_ylim(20, 30)

        self.timestamps = []
        self.temperaturas = []

        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(pady=20)

    def actualizar_temperatura(self, temperatura, timestamp):
        """Actualiza la etiqueta con la última temperatura recibida."""
        self.temp_label.config(text=f"Temperatura: {temperatura}°C")
    
    def actualizar_grafica(self, temperatura):
        """Actualiza la gráfica en la interfaz con la nueva temperatura recibida."""
        self.timestamps.append(datetime.now().strftime("%H:%M:%S"))
        self.temperaturas.append(temperatura)

        if len(self.timestamps) > 10:
            self.timestamps.pop(0)
            self.temperaturas.pop(0)

        self.ax.clear()
        self.ax.set_title("Gráfica de Control - Temperatura")
        self.ax.set_xlabel("Tiempo")
        self.ax.set_ylabel("Temperatura (°C)")

        self.ax.plot(self.timestamps, self.temperaturas, marker='o', color='blue', label='Temperatura')
        
        if SensorData.limites_establecidos:
            self.ax.axhline(y=SensorData.LIMITE_SUPERIOR, color='red', linestyle='--', label=f'UCL ({SensorData.LIMITE_SUPERIOR:.2f}°C)')
            self.ax.axhline(y=SensorData.LIMITE_INFERIOR, color='green', linestyle='--', label=f'LCL ({SensorData.LIMITE_INFERIOR:.2f}°C)')
        
        self.ax.legend()
        self.fig.tight_layout()
        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    gui = SensorGUI(root)
    mqtt_client = SensorMQTTClient("mqtt.eclipseprojects.io", "sensor/temperatura", gui)
    mqtt_client.connect()

    import threading
    mqtt_thread = threading.Thread(target=mqtt_client.start)
    mqtt_thread.daemon = True
    mqtt_thread.start()

    root.mainloop()
