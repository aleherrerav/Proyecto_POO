#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

const char* ssid = "LASTELECOMUNICACIONESNOPARAN";
const char* password = "LTNPP-2023CCT";

const char* mqttServer = "broker.emqx.io"; 
const int mqttPort = 1883;
const char* topic_temp = "temperatura/sensor";

#define DHTPIN 18       
#define DHTTYPE DHT11    
DHT dht(DHTPIN, DHTTYPE);

WiFiClient espClient;
PubSubClient mqttClient(espClient);

void setupWifi() {
  delay(1000);
  Serial.print("Conectando a WiFi");
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado.");
}

void connectToMqtt() {
  while (!mqttClient.connected()) {
    Serial.println("Conectando al broker MQTT...");

    if (mqttClient.connect("ESP32_Client")) {
      Serial.println("Conectado a MQTT.");
    } else {
      Serial.print("Fallo en la conexión MQTT. Estado: ");
      Serial.println(mqttClient.state());
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(5000);

  dht.begin();
  setupWifi();

  mqttClient.setServer(mqttServer, mqttPort);
  connectToMqtt();
}

void loop() {
  if (!mqttClient.connected()) {
    connectToMqtt();
  }

  mqttClient.loop();

  float temperatura = NAN;
  for (int i = 0; i < 3 && isnan(temperatura); i++) {
    temperatura = dht.readTemperature();
    delay(100); // Pequeña espera entre intentos
  }

  if (isnan(temperatura)) {
    Serial.println("Error leyendo el sensor DHT22 después de 3 intentos");
  } else {
    char tempStr[50];
    snprintf(tempStr, 50, "{\"temperatura\": %.2f}", temperatura);
    mqttClient.publish(topic_temp, tempStr);

    Serial.print("Temperatura publicada: ");
    Serial.println(tempStr);
  }

  delay(2000); 
}