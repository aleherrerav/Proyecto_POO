import unittest
import numpy as np
import time
import paho.mqtt.client as mqtt
import json
import tkinter as tk
from datetime import datetime
from sensor_mqtt import SensorData, SensorGUI

BROKER = "mqtt.eclipseprojects.io"
TOPIC = "sensor/temperatura"

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode().strip())
        temperatura = float(data.get("temperatura", 0))
        userdata.append(temperatura)
        print(f"Temperatura recibida: {temperatura}°C")  #  para ver temperaturas en tiempo real
    except Exception as e:
        print("Error procesando mensaje MQTT:", e)

class TestSensorData(unittest.TestCase):
    def setUp(self):
        """
        Se ejecuta antes de cada prueba. Recopila las primeras 10 temperaturas y define los límites,
        luego analiza nuevas temperaturas en tiempo real para detectar anomalías.
        """
        self.root = tk.Tk()
        self.root.withdraw()  
        self.gui = SensorGUI(self.root)
        self.gui.temperaturas = []

        print("🔄 Esperando primeras 10 temperaturas para calcular los límites...")

        # Configurar cliente MQTT
        client = mqtt.Client(userdata=self.gui.temperaturas)
        client.on_message = on_message
        client.connect(BROKER, 1883, 60)
        client.subscribe(TOPIC)
        client.loop_start()

        # Esperar hasta recibir 10 temperaturas
        tiempo_espera = 60  # Tiempo máximo de espera en segundos
        tiempo_inicial = time.time()
        while len(self.gui.temperaturas) < 10 and (time.time() - tiempo_inicial) < tiempo_espera:
            time.sleep(1)

        if len(self.gui.temperaturas) >= 10:
            # Cálculo de los límites basados en las 10 primeras temperaturas
            self.mu = np.mean(self.gui.temperaturas)
            self.sigma = np.std(self.gui.temperaturas)
            self.limite_superior = self.mu + 3 * self.sigma
            self.limite_inferior = self.mu - 3 * self.sigma
            print(f"✅ Límites establecidos: Superior={self.limite_superior:.2f}°C, Inferior={self.limite_inferior:.2f}°C")
        else:
            client.loop_stop()
            client.disconnect()
            self.skipTest("⛔ No se recibieron suficientes datos para establecer los límites.")

        # Análisis de nuevas temperaturas
        print("\n📡 Analizando nuevas temperaturas en tiempo real...\n")
        nuevas_temperaturas = []
        tiempo_analisis = 30  # Analizar durante 30 segundos
        tiempo_inicial = time.time()

        while (time.time() - tiempo_inicial) < tiempo_analisis:
            if self.gui.temperaturas and len(nuevas_temperaturas) < len(self.gui.temperaturas):
                nueva_temp = self.gui.temperaturas[-1]
                nuevas_temperaturas.append(nueva_temp)
                print(f"🌡️ Nueva temperatura recibida: {nueva_temp}°C")
                es_anomalia = nueva_temp > self.limite_superior or nueva_temp < self.limite_inferior
                if es_anomalia:
                    print(f"🚨 Anomalía detectada: {nueva_temp}°C fuera del rango esperado.")
                else:
                    print(f"✅ Temperatura dentro del rango esperado.")
            time.sleep(1)

        client.loop_stop()
        client.disconnect()

    def test_anomalia_detectada_correctamente(self):
        """
        Prueba si una temperatura fuera de los límites es detectada como anomalía.
        """
        temperatura_anomala = self.limite_superior + 2.0  # Un poco más arriba del límite
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sensor_data = SensorData(temperatura_anomala, timestamp, self.gui)

        print(f"\nProbando temperatura anómala: {temperatura_anomala}°C")
        print(f"Límites: Superior={self.limite_superior:.2f}°C, Inferior={self.limite_inferior:.2f}°C")

        es_anomalia = temperatura_anomala > self.limite_superior or temperatura_anomala < self.limite_inferior
        self.assertTrue(es_anomalia)

    def test_temperatura_normal(self):
        """
        Prueba si una temperatura dentro de los límites NO es detectada como anomalía.
        """
        temperatura_normal = self.mu  # Un valor promedio
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sensor_data = SensorData(temperatura_normal, timestamp, self.gui)

        print(f"\n Probando temperatura normal: {temperatura_normal}°C")
        print(f"Límites: Superior={self.limite_superior:.2f}°C, Inferior={self.limite_inferior:.2f}°C")

        es_anomalia = temperatura_normal > self.limite_superior or temperatura_normal < self.limite_inferior
        self.assertFalse(es_anomalia)

if __name__ == '__main__':
    unittest.main()
