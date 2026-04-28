#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include "base64.h"
#include "board_config.h"

// ================== WIFI ==================
const char* ssid = "Redmi";
const char* password = "camilo01";

// ================== API ==================
const char* serverUrl = "http://ec2-16-59-26-200.us-east-2.compute.amazonaws.com:8000/clasificar";
const char* esp32Receiver = "http://10.75.162.11/resultado";

// ================== SERVIDOR ==================
WebServer server(80);

// ================== CONTROL ==================
volatile bool solicitudFotoPendiente = false;
unsigned long tiempoSolicitud = 0;
bool fotoTomada = false;

const unsigned long retardoFoto = 3000;
bool enviando = false;

// ================== SETUP ==================
void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("🚀 ESP32-CAM DIRECTA");

  // ================== CAMARA ==================
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;

  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_QVGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("❌ Error cámara: 0x%x\n", err);
    while (true);
  }

  // ================== WIFI ==================
  WiFi.begin(ssid, password);
  Serial.print("Conectando WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\n✅ WiFi conectado");
  Serial.print("📡 IP CAM: ");
  Serial.println(WiFi.localIP());

  // ================== ENDPOINT DETECTAR ==================
  server.on("/detectar", HTTP_GET, []() {

    Serial.println("📨 /detectar recibido");

    // RESPUESTA INMEDIATA
    server.send(200, "text/plain", "OK");

    solicitudFotoPendiente = true;
    tiempoSolicitud = millis();
    fotoTomada = false;

    Serial.println("⏳ Foto programada...");
  });

  // DEBUG
  server.on("/", []() {
    server.send(200, "text/plain", "ESP32-CAM OK");
  });

  server.begin();
  Serial.println("🌐 Servidor listo");
}

// ================== LOOP ==================
void loop() {

  server.handleClient();

  if (solicitudFotoPendiente && !fotoTomada &&
      (millis() - tiempoSolicitud >= retardoFoto)) {

    Serial.println("📸 Ejecutando captura...");
    tomarFotoYEnviar();

    fotoTomada = true;
    solicitudFotoPendiente = false;
  }

  delay(5);
}

// ================== CAPTURA Y ENVIO ==================
void tomarFotoYEnviar() {

  if (enviando) {
    Serial.println("⚠️ Ya enviando...");
    return;
  }

  enviando = true;

  Serial.println("📷 Capturando imagen...");

  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("❌ Error capturando");
    enviando = false;
    return;
  }

  Serial.printf("✅ Imagen: %d bytes\n", fb->len);

  String img = base64::encode(fb->buf, fb->len);
  esp_camera_fb_return(fb);

  // ================== API ==================
  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(15000);

  String payload = "{\"image\":\"" + img + "\"}";

  Serial.println("📡 Enviando a API...");

  int code = http.POST(payload);

  if (code > 0) {

    String response = http.getString();

    Serial.println("✅ Respuesta API OK");

    // ================== ENVIO MULTIPLE ==================
    for (int i = 0; i < 10; i++) {

      HTTPClient http2;
      http2.begin(esp32Receiver);
      http2.addHeader("Content-Type", "application/json");
      http2.setTimeout(3000);

      Serial.printf("📤 Envío %d/10 al ESP32...\n", i + 1);

      int code2 = http2.POST(response);

      Serial.print("📤 Código respuesta ESP32: ");
      Serial.println(code2);

      http2.end();

      delay(500);
    }

  } else {
    Serial.printf("❌ Error API: %d\n", code);
  }

  http.end();

  enviando = false;

  Serial.println("📷 Ciclo terminado\n");
}