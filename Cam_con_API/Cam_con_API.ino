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

const char* serverUrl =
"http://ec2-16-59-26-200.us-east-2.compute.amazonaws.com:8000/clasificar";

const char* listarLiteUrl =
"http://ec2-16-59-26-200.us-east-2.compute.amazonaws.com:8000/listar_lite";

// ================== RED DINAMICA ==================

IPAddress local_IP;
IPAddress gateway;
IPAddress subnet;
IPAddress primaryDNS;
IPAddress secondaryDNS;

// ================== ESP32 CENTRAL ==================

String esp32Receiver;

// ================== SERVIDOR ==================

WebServer server(80);

// ================== CONTROL ==================

volatile bool solicitudFotoPendiente = false;

unsigned long tiempoSolicitud = 0;

bool fotoTomada = false;

bool enviando = false;

const unsigned long retardoFoto = 500;

// =====================================================
// WIFI + IP .56
// =====================================================

void conectarWiFiConIP56() {

  WiFi.begin(ssid, password);

  Serial.print("Conectando WiFi");

  while (WiFi.status() != WL_CONNECTED) {

    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("✅ WiFi conectado");

  IPAddress ip = WiFi.localIP();

  gateway = WiFi.gatewayIP();

  subnet = WiFi.subnetMask();

  primaryDNS = WiFi.dnsIP(0);

  secondaryDNS = WiFi.dnsIP(1);

  Serial.print("📡 IP temporal: ");
  Serial.println(ip);

  // =========================================
  // FORZAR .56
  // =========================================

  local_IP = IPAddress(
    ip[0],
    ip[1],
    ip[2],
    56
  );

  // =========================================
  // ESP32 CENTRAL .11
  // =========================================

  esp32Receiver =
    "http://" +
    String(ip[0]) + "." +
    String(ip[1]) + "." +
    String(ip[2]) +
    ".11/resultado";

  Serial.print("🎯 ESP32 CENTRAL: ");
  Serial.println(esp32Receiver);

  WiFi.disconnect(true);

  delay(1000);

  WiFi.config(
    local_IP,
    gateway,
    subnet,
    primaryDNS,
    secondaryDNS
  );

  WiFi.begin(ssid, password);

  Serial.print("Aplicando IP .56");

  while (WiFi.status() != WL_CONNECTED) {

    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("✅ WiFi reconectado");

  Serial.print("📡 IP FINAL CAM: ");
  Serial.println(WiFi.localIP());
}

// =====================================================
// SETUP
// =====================================================

void setup() {

  Serial.begin(115200);

  delay(1000);

  Serial.println("");
  Serial.println("🚀 ESP32-CAM DIRECTA");

  // =====================================================
  // CAMARA
  // =====================================================

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

  Serial.println("✅ Cámara iniciada");

  // =====================================================
  // WIFI
  // =====================================================

  conectarWiFiConIP56();

  // =====================================================
  // ENDPOINTS
  // =====================================================

  server.on("/detectar", HTTP_GET, []() {

    Serial.println("");
    Serial.println("📨 /detectar recibido");

    server.send(200, "text/plain", "OK");

    solicitudFotoPendiente = true;

    tiempoSolicitud = millis();

    fotoTomada = false;

    Serial.println("⏳ Foto programada...");
  });

  server.on("/", []() {

    server.send(
      200,
      "text/plain",
      "ESP32-CAM OK"
    );
  });

  server.begin();

  Serial.println("🌐 Servidor listo");
}

// =====================================================
// LOOP
// =====================================================

void loop() {

  server.handleClient();

  // =========================================
  // RECONEXION WIFI
  // =========================================

  if (WiFi.status() != WL_CONNECTED) {

    Serial.println("⚠️ WiFi perdido");

    conectarWiFiConIP56();
  }

  // =========================================
  // TOMAR FOTO
  // =========================================

  if (
    solicitudFotoPendiente &&
    !fotoTomada &&
    (millis() - tiempoSolicitud >= retardoFoto)
  ) {

    Serial.println("");
    Serial.println("📸 Ejecutando captura...");

    tomarFotoYEnviar();

    fotoTomada = true;

    solicitudFotoPendiente = false;
  }

  delay(5);
}

// =====================================================
// CAPTURA Y ENVIO
// =====================================================

void tomarFotoYEnviar() {

  if (enviando) {

    Serial.println("⚠️ Ya enviando...");

    return;
  }

  enviando = true;

  // =========================================
  // LIMPIAR BUFFER
  // =========================================

  Serial.println("🧹 Limpiando buffer...");

  for (int i = 0; i < 3; i++) {

    camera_fb_t * fb = esp_camera_fb_get();

    if (fb) {

      esp_camera_fb_return(fb);
    }

    delay(50);
  }

  // =========================================
  // CAPTURA REAL
  // =========================================

  Serial.println("📷 Capturando imagen REAL...");

  camera_fb_t * fb = esp_camera_fb_get();

  if (!fb) {

    Serial.println("❌ Error capturando");

    enviando = false;

    return;
  }

  Serial.printf("✅ Imagen: %d bytes\n", fb->len);

  String img = base64::encode(
    fb->buf,
    fb->len
  );

  esp_camera_fb_return(fb);

  // =========================================
  // ENVIAR A /clasificar
  // =========================================

  HTTPClient http;

  http.begin(serverUrl);

  http.addHeader(
    "Content-Type",
    "application/json"
  );

  http.setTimeout(15000);

  String payload =
    "{\"image\":\"" +
    img +
    "\"}";

  Serial.println("📡 Enviando imagen a API...");

  int code = http.POST(payload);

  if (code > 0) {

    Serial.print("✅ Código API: ");
    Serial.println(code);

    // =========================================
    // IGNORAR RESPUESTA PESADA
    // =========================================

    http.getString();

    http.end();

    Serial.println("🧹 Respuesta pesada ignorada");

    // =========================================
    // PEDIR SOLO DATOS LIVIANOS
    // =========================================

    HTTPClient httpLite;

    Serial.println("📥 Consultando listar_lite...");

    httpLite.begin(listarLiteUrl);

    httpLite.setTimeout(10000);

    int liteCode = httpLite.GET();

    if (liteCode > 0) {

      String liteResponse =
        httpLite.getString();

      Serial.println("✅ Datos livianos:");

      Serial.println(liteResponse);

      httpLite.end();

      // =========================================
      // ENVIAR AL ESP32 CENTRAL
      // =========================================

      for (int i = 0; i < 2; i++) {

        HTTPClient http2;

        http2.begin(esp32Receiver);

        http2.addHeader(
          "Content-Type",
          "application/json"
        );

        http2.setTimeout(3000);

        Serial.printf(
          "📤 Envío %d/2 al ESP32...\n",
          i + 1
        );

        int code2 =
          http2.POST(liteResponse);

        Serial.print(
          "📤 Código respuesta ESP32: "
        );

        Serial.println(code2);

        if (code2 <= 0) {

          Serial.println(
            "❌ ESP32 CENTRAL NO RESPONDE"
          );
        }

        http2.end();

        delay(500);
      }

    } else {

      Serial.print("❌ Error listar_lite: ");

      Serial.println(liteCode);

      httpLite.end();
    }

  } else {

    Serial.printf(
      "❌ Error API: %d\n",
      code
    );

    http.end();
  }

  enviando = false;

  Serial.println("");
  Serial.println("📷 Ciclo terminado");
}