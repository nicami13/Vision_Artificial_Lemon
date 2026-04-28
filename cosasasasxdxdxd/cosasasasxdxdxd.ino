#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>
#include <WebServer.h>

// ================== PINES ==================
#define TRIG_PIN 12
#define ECHO_PIN 14
#define MOTOR_IN1 27
#define MOTOR_IN2 26
#define MOTOR_ENA 25
#define SERVO1_PIN 16
#define SERVO2_PIN 17

// ================== WIFI ==================
const char* ssid = "Redmi";
const char* password = "camilo01";
const char* camIP = "10.75.162.56";

// ================== PARAMETROS ==================
const float DISTANCIA_UMBRAL = 7.0;
const unsigned long TIEMPO_ESPERA_FOTO = 7000;
const unsigned long COOLDOWN_FALLO_FOTO = 5000;
String ultimoTimestampConfirmado = "";
String timestampTemporal = "";
int contadorConfirmacion = 0;
String timestampEnValidacion = "";
int intentosValidacion = 0;
unsigned long ultimoIntentoValidacion = 0;
const int MAX_INTENTOS = 10;
const unsigned long INTERVALO_INTENTO = 500;
// ================== SERVIDOR ==================
WebServer server(80);

// ================== VARIABLES ==================
Servo servo1, servo2;

enum Estado { ESPERANDO_DETECCION, ESPERANDO_FOTO };
Estado estadoActual = ESPERANDO_DETECCION;

unsigned long tiempoInicioEstado = 0;
unsigned long tiempoUltimoIntentoFoto = 0;

int ultimoAnguloServo1 = -1;
int ultimoAnguloServo2 = -1;

// Barrido
bool barridoActivo = true;
int anguloBarrido = 45;
int pasoBarrido = 1;
unsigned long tiempoUltimoBarrido = 0;
const unsigned long INTERVALO_BARRIDO = 20;
String ultimoIDProcesado = "";

// ================== SERVOS ==================
void moverServoSuave(Servo &servo, int &ultimoAngulo, int destino) {
  if (destino < 10) destino = 10;
  if (destino > 170) destino = 170;

  if (ultimoAngulo == -1) {
    servo.write(destino);
    delay(50);
    ultimoAngulo = destino;
    return;
  }

  int paso = (destino > ultimoAngulo) ? 1 : -1;
  int actual = ultimoAngulo;

  while (actual != destino) {
    actual += paso;
    servo.write(actual);
    delay(8);
  }

  ultimoAngulo = destino;
}

void escribirServo1(int angulo) {
  moverServoSuave(servo1, ultimoAnguloServo1, angulo);
}

void escribirServo2(int angulo) {
  moverServoSuave(servo2, ultimoAnguloServo2, angulo);
}

// ================== MOTOR ==================
void apagarMotor() {
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, LOW);
  analogWrite(MOTOR_ENA, 0);
}

void encenderMotor(int pwm = 255) {
  digitalWrite(MOTOR_IN1, HIGH);
  digitalWrite(MOTOR_IN2, LOW);
  analogWrite(MOTOR_ENA, pwm);
}

// ================== ESTADO INICIAL ==================
void estado_inicial() {
  escribirServo1(50);
  escribirServo2(0);
}

// ================== SENSOR ==================
float medirDistancia() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duracion = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duracion == 0) return -1;
  return duracion * 0.0343 / 2;
}

// ================== CAMARA ==================
bool enviarSolicitudFoto() {
  if (WiFi.status() != WL_CONNECTED) return false;

  HTTPClient http;
  String url = "http://" + String(camIP) + "/detectar";

  http.begin(url);
  http.setTimeout(2000);

  int codigo = http.GET();
  http.end();

  return (codigo == 200);
}

// ================== RECEPCIÓN DIRECTA ==================
// ================== RECEPCIÓN DIRECTA ==================
void configurarServidor() {

  server.on("/resultado", []() {

    String body = server.arg("plain");

    Serial.println("📥 Resultado recibido:");
    Serial.println(body);

    // ================== EXTRAER TIMESTAMP ==================
    String timestamp = "";

    int idx = body.indexOf("\"timestamp\":");
    if (idx != -1) {
      int start = body.indexOf("\"", idx + 12) + 1;
      int end = body.indexOf("\"", start);
      timestamp = body.substring(start, end);
    }

    Serial.print("⏱ Timestamp recibido: ");
    Serial.println(timestamp);

    if (timestamp == "" || timestamp == "null") {
      Serial.println("⚠️ Timestamp inválido → ignorado");
      server.send(200, "text/plain", "IGNORED");
      return;
    }

    // 🔥 SI ES EL MISMO YA PROCESADO → IGNORAR
    if (timestamp == ultimoTimestampConfirmado) {
      Serial.println("⏳ Mismo limón ya procesado → ignorado");
      server.send(200, "text/plain", "IGNORED");
      return;
    }

    unsigned long ahora = millis();

    // 🔁 MISMO EN VALIDACIÓN
    if (timestamp == timestampEnValidacion) {

      if (ahora - ultimoIntentoValidacion >= INTERVALO_INTENTO) {
        ultimoIntentoValidacion = ahora;
        intentosValidacion++;

        Serial.printf("🔁 Intento %d/%d\n", intentosValidacion, MAX_INTENTOS);
      }

      // ✅ CONFIRMADO
      if (intentosValidacion >= MAX_INTENTOS) {

        Serial.println("✅✅ LIMÓN CONFIRMADO (10/10)");

        ultimoTimestampConfirmado = timestamp;
        timestampEnValidacion = "";
        intentosValidacion = 0;

        // ================== CLASIFICACIÓN ==================
        if (body.indexOf("PEQUE") != -1) clasificar_pequeno();
        else if (body.indexOf("MEDIANO") != -1) clasificar_mediano();
        else if (body.indexOf("GRANDE") != -1) clasificar_grande();
        else Serial.println("⚠️ Tamaño desconocido");

        estadoActual = ESPERANDO_DETECCION;
        barridoActivo = true;
      }

    } 
    // 🆕 NUEVO DETECTADO
    else {
      timestampEnValidacion = timestamp;
      intentosValidacion = 1;
      ultimoIntentoValidacion = ahora;

      Serial.println("🆕 Nuevo limón detectado → iniciando validación...");
    }

    server.send(200, "text/plain", "OK");
  });

  server.begin();
}
// ================== CLASIFICACIÓN MEDIANO ==================
void clasificar_mediano() {
  Serial.println("🍋 MEDIANO");
  barridoActivo = false;

  apagarMotor();
  delay(300);

  escribirServo2(0);
  delay(150);

  escribirServo2(170);
  while (ultimoAnguloServo2 != 170) delay(10);

  Serial.println("🧠 Pre-empuje suave...");

  digitalWrite(MOTOR_IN1, HIGH);
  digitalWrite(MOTOR_IN2, LOW);
  analogWrite(MOTOR_ENA, 140);

  escribirServo1(95);

  delay(120);

  apagarMotor();

  while (ultimoAnguloServo1 != 95) delay(10);

  Serial.println("✅ Posición correcta");

  delay(200);

  encenderMotor();
  delay(4000);
  apagarMotor();

  for (int i = 0; i < 8; i++) {
    digitalWrite(MOTOR_IN1, HIGH);
    digitalWrite(MOTOR_IN2, LOW);
    analogWrite(MOTOR_ENA, 200);
    delay(random(150, 300));

    digitalWrite(MOTOR_IN1, LOW);
    digitalWrite(MOTOR_IN2, HIGH);
    analogWrite(MOTOR_ENA, 200);
    delay(random(150, 300));

    apagarMotor();
    delay(80);
  }

  encenderMotor();
  for (int i = 0; i < 6; i++) {
    escribirServo1(105);
    delay(90);
    escribirServo1(60);
    delay(90);
  }
  apagarMotor();

  escribirServo1(50);
  delay(150);
  escribirServo2(0);

  estado_inicial();
  barridoActivo = true;
}

// ================== CLASIFICACIÓN PEQUEÑO ==================
void clasificar_pequeno() {
  Serial.println("🍋 PEQUEÑO");
  barridoActivo = false;

  apagarMotor();
  delay(300);

  escribirServo2(10);
  delay(150);

  Serial.println("🧠 Pre-empuje suave...");

  digitalWrite(MOTOR_IN1, HIGH);
  digitalWrite(MOTOR_IN2, LOW);
  analogWrite(MOTOR_ENA, 130);

  escribirServo2(38);

  delay(120);
  apagarMotor();

  while (ultimoAnguloServo2 != 38) delay(10);

  escribirServo1(0);
  while (ultimoAnguloServo1 != 10) delay(10);

  Serial.println("✅ Posición lista");

  delay(200);

  encenderMotor();
  delay(4000);
  apagarMotor();

  for (int i = 0; i < 6; i++) {
    digitalWrite(MOTOR_IN1, HIGH);
    digitalWrite(MOTOR_IN2, LOW);
    analogWrite(MOTOR_ENA, random(150, 220));
    delay(random(120, 250));

    digitalWrite(MOTOR_IN1, LOW);
    digitalWrite(MOTOR_IN2, HIGH);
    analogWrite(MOTOR_ENA, random(150, 220));
    delay(random(120, 250));

    apagarMotor();
    delay(80);
  }

  Serial.println("👊 Patadas con servo2 (rampa)");

  encenderMotor();

  for (int i = 0; i < 8; i++) {
    escribirServo2(38);
    delay(80);
    escribirServo2(20);
    delay(80);
  }

  apagarMotor();
  delay(500);

  escribirServo1(50);
  delay(150);
  escribirServo2(0);

  estado_inicial();
  barridoActivo = true;

  Serial.println("✅ PEQUEÑO completado");
}

// ================== CLASIFICACIÓN GRANDE ==================
void clasificar_grande() {
  Serial.println("🍋 GRANDE");
  barridoActivo = false;

  apagarMotor();
  delay(300);

  Serial.println("⚡ Meneo progresivo (romper inercia)");

  for (int i = 0; i < 14; i++) {
    int potencia = 140 + (i * 40);
    int tiempo   = 30 + (i * 20);

    digitalWrite(MOTOR_IN1, HIGH);
    digitalWrite(MOTOR_IN2, LOW);
    analogWrite(MOTOR_ENA, potencia);
    delay(tiempo);

    digitalWrite(MOTOR_IN1, LOW);
    digitalWrite(MOTOR_IN2, HIGH);
    analogWrite(MOTOR_ENA, potencia);
    delay(tiempo);

    apagarMotor();
    delay(40);
  }

  Serial.println("✅ Inercia rota");

  digitalWrite(MOTOR_IN1, HIGH);
  digitalWrite(MOTOR_IN2, LOW);
  analogWrite(MOTOR_ENA, 255);
  delay(2000);

  escribirServo2(90);
  while (ultimoAnguloServo2 != 90) delay(10);

  escribirServo1(50);
  while (ultimoAnguloServo1 != 50) delay(10);

  delay(200);

  analogWrite(MOTOR_ENA, 255);
  delay(5000);

  apagarMotor();

  escribirServo2(0);
  delay(200);

  estado_inicial();
  barridoActivo = true;

  Serial.println("✅ GRANDE completado");
}

// ================== SETUP ==================
void setup() {
  Serial.begin(115200);

  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  pinMode(MOTOR_ENA, OUTPUT);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  servo1.attach(SERVO1_PIN);
  servo2.attach(SERVO2_PIN);

  estado_inicial();

  WiFi.begin(ssid, password);

  Serial.print("Conectando WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\n✅ WiFi conectado");

  Serial.print("📡 IP del ESP32: ");
  Serial.println(WiFi.localIP());

  // 🔥🔥🔥 ESTO FALTABA
  configurarServidor();

  Serial.println("🌐 Servidor listo (/resultado)");
}

// ================== LOOP ==================
void loop() {

  server.handleClient();

  unsigned long ahora = millis();

  switch (estadoActual) {

    case ESPERANDO_DETECCION: {

      if (barridoActivo && (ahora - tiempoUltimoBarrido >= INTERVALO_BARRIDO)) {
        tiempoUltimoBarrido = ahora;
        anguloBarrido += pasoBarrido;
        if (anguloBarrido >= 55 || anguloBarrido <= 45) pasoBarrido *= -1;
        escribirServo1(anguloBarrido);
      }

      float dist = medirDistancia();  // 🔥 YA NO DA ERROR

      if (dist > 0 && dist < DISTANCIA_UMBRAL) {

        if (ahora - tiempoUltimoIntentoFoto >= COOLDOWN_FALLO_FOTO) {

          Serial.println("🚨 Detectado → solicitando foto");

          if (enviarSolicitudFoto()) {
            estadoActual = ESPERANDO_FOTO;
            tiempoInicioEstado = ahora;
            barridoActivo = false;
            escribirServo1(50);
          } else {
            tiempoUltimoIntentoFoto = ahora;
          }
        }
      }

      break;
    }

    case ESPERANDO_FOTO: {
      // Solo espera respuesta de la cámara
      break;
    }
  }

  delay(10);
}