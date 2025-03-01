import paho.mqtt.client as mqtt
import json
from datetime import datetime
import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import MaxNLocator
import numpy as np  # Importamos numpy para calcular media y desviación estándar

class SensorMQTTClient:
    def __init__(self, broker, topic, gui):
        self.broker = broker
        self.topic = topic
        self.client = mqtt.Client()
        self.client.on_message = self.on_message
        self.gui = gui  

    def connect(self):
        self.client.connect(self.broker, 1883, 60)
        self.client.subscribe(self.topic)
        print(f"Conectado al broker {self.broker}, suscrito al tópico {self.topic}")

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode().strip())  
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sensor_data = SensorData(float(data.get("temperatura", 0)), timestamp, self.gui)
            sensor_data.analizar_temperatura()
        except Exception as e:
            print("Error procesando mensaje:", e)
    
    def start(self):
        self.client.loop_forever()

class SensorData:
    def __init__(self, temperatura, timestamp, gui):
        self.temperatura = temperatura
        self.timestamp = timestamp
        self.gui = gui 
    
    def analizar_temperatura(self):
        print(f"[{self.timestamp}] Temperatura recibida: {self.temperatura}°C")
        self.gui.actualizar_temperatura(self.temperatura, self.timestamp)
        self.gui.actualizar_grafica(self.temperatura)

        if len(self.gui.temperaturas) >= 10:
            mu = np.mean(self.gui.temperaturas)
            sigma = np.std(self.gui.temperaturas)
            LIMITE_SUPERIOR = mu + 3 * sigma
            LIMITE_INFERIOR = mu - 3 * sigma

            if self.temperatura > LIMITE_SUPERIOR or self.temperatura < LIMITE_INFERIOR:
                tipo_anomalia = "Temperatura alta" if self.temperatura > LIMITE_SUPERIOR else "Temperatura baja"
                print(f"⚠️ Anomalía detectada: {tipo_anomalia} ({self.temperatura}°C)")
                self.guardar_anomalia(tipo_anomalia)
    
    def guardar_anomalia(self, tipo_anomalia):
        anomalía = {
            'timestamp': self.timestamp,
            'temperatura': self.temperatura,
            'tipo_anomalia': tipo_anomalia
        }
        try:
            with open('anomalias_detectadas.json', 'a') as file:
                json.dump(anomalía, file)
                file.write('\n')  
            print(f"Anomalía guardada en el archivo: {anomalía}")
        except Exception as e:
            print(f"Error al guardar la anomalía: {e}")

class SensorGUI:
    def __init__(self, root):
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
        self.temp_label.config(text=f"Temperatura: {temperatura}°C")
    
    def actualizar_alerta(self, mensaje):
        self.alert_label.config(text=f"Estado: {mensaje}")

    def actualizar_grafica(self, temperatura):
        self.timestamps.append(datetime.now().strftime("%H:%M:%S"))
        self.temperaturas.append(temperatura)

        if len(self.timestamps) > 10:  
            self.timestamps.pop(0)
            self.temperaturas.pop(0)

        self.ax.clear()
        self.ax.set_title("Gráfica de Control - Temperatura")
        self.ax.set_xlabel("Tiempo")
        self.ax.set_ylabel("Temperatura (°C)")

        if len(self.temperaturas) >= 10:
            mu = np.mean(self.temperaturas)
            sigma = np.std(self.temperaturas)
            LIMITE_SUPERIOR = mu + 3 * sigma
            LIMITE_INFERIOR = mu - 3 * sigma
        else:
            LIMITE_SUPERIOR, LIMITE_INFERIOR = None, None

        self.ax.plot(self.timestamps, self.temperaturas, marker='o', color='blue', label='Temperatura')
        
        if LIMITE_SUPERIOR is not None and LIMITE_INFERIOR is not None:
            self.ax.axhline(y=LIMITE_SUPERIOR, color='red', linestyle='--', label=f'UCL ({LIMITE_SUPERIOR:.2f}°C)')
            self.ax.axhline(y=LIMITE_INFERIOR, color='green', linestyle='--', label=f'LCL ({LIMITE_INFERIOR:.2f}°C)')
        
        self.ax.set_ylim(20, 30)
        self.ax.xaxis.set_major_locator(MaxNLocator(nbins=5))  
        self.ax.set_xticks(range(len(self.timestamps)))
        self.ax.set_xticklabels(self.timestamps, rotation=45, ha='right') 
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
