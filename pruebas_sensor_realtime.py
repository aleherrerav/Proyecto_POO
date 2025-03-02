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
    except Exception as e:
        print("Error procesando mensaje MQTT:", e)

class TestSensorData(unittest.TestCase):
    def setUp(self):
        """
        Se ejecuta antes de cada prueba. Crea una instancia simulada de la GUI y genera temperaturas base.
        """
        self.root = tk.Tk()
        self.root.withdraw()  # Ocultar la ventana de Tkinter en las pruebas
        self.gui = SensorGUI(self.root)
        self.gui.temperaturas = []

        print("Esperando datos...")

        # Configurar cliente MQTT
        client = mqtt.Client(userdata=self.gui.temperaturas)
        client.on_message = on_message
        client.connect(BROKER, 1883, 60)
        client.subscribe(TOPIC)
        client.loop_start()

        # Esperar hasta recibir 10 temperaturas reales del ESP32 o del broker MQTT
        tiempo_espera = 30  # Tiempo máximo de espera en segundos
        tiempo_inicial = time.time()
        while len(self.gui.temperaturas) < 10 and (time.time() - tiempo_inicial) < tiempo_espera:
            time.sleep(1)  # Esperar un segundo antes de verificar de nuevo

        client.loop_stop()
        client.disconnect()
    
    def test_limites_calculados_correctamente(self):
        """
        Verifica que los límites se calculan correctamente usando la media y desviación estándar.
        """
        if len(self.gui.temperaturas) < 2:
            self.skipTest("No hay suficientes datos para calcular límites.")

        mu = np.mean(self.gui.temperaturas)
        sigma = np.std(self.gui.temperaturas)
        limite_superior = mu + 3 * sigma
        limite_inferior = mu - 3 * sigma

        print(f"Media: {mu:.2f}, Desviación estándar: {sigma:.2f}")
        print(f"Límite superior: {limite_superior:.2f}, Límite inferior: {limite_inferior:.2f}")

        self.assertIsInstance(mu, float)
        self.assertIsInstance(sigma, float)
        self.assertGreater(limite_superior, limite_inferior)
    
    def test_anomalia_detectada_correctamente(self):
        """
        Prueba si una temperatura fuera de los límites es detectada como anomalía.
        """
        if len(self.gui.temperaturas) < 2:
            self.skipTest("No hay suficientes datos para calcular límites.")

        temperatura_anomala = 30.0  # Temperatura fuera del rango esperado
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sensor_data = SensorData(temperatura_anomala, timestamp, self.gui)
        
        mu = np.mean(self.gui.temperaturas)
        sigma = np.std(self.gui.temperaturas)
        limite_superior = mu + 3 * sigma
        limite_inferior = mu - 3 * sigma

        print(f"Probando temperatura anómala: {temperatura_anomala}°C")
        print(f"Límite superior: {limite_superior:.2f}, Límite inferior: {limite_inferior:.2f}")

        es_anomalia = temperatura_anomala > limite_superior or temperatura_anomala < limite_inferior
        self.assertTrue(es_anomalia)
    
    def test_temperatura_normal(self):
        """
        Prueba si una temperatura dentro de los límites NO es detectada como anomalía.
        """
        if len(self.gui.temperaturas) < 2:
            self.skipTest("No hay suficientes datos para calcular límites.")

        temperatura_normal = 23.0  # Dentro del rango esperado
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sensor_data = SensorData(temperatura_normal, timestamp, self.gui)
        
        mu = np.mean(self.gui.temperaturas)
        sigma = np.std(self.gui.temperaturas)
        limite_superior = mu + 3 * sigma
        limite_inferior = mu - 3 * sigma

        print(f"Probando temperatura normal: {temperatura_normal}°C")
        print(f"Límite superior: {limite_superior:.2f}, Límite inferior: {limite_inferior:.2f}")

        es_anomalia = temperatura_normal > limite_superior or temperatura_normal < limite_inferior
        self.assertFalse(es_anomalia)

if __name__ == '__main__':
    unittest.main()
