// =====================================================
// LIBRERIAS
// =====================================================

#include <WiFi.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>
#include <WebServer.h>
#include <Wire.h>
#include <IskakINO_LiquidCrystal_I2C.h>
#include "BluetoothSerial.h"

// =====================================================
// BLUETOOTH
// =====================================================

BluetoothSerial SerialBT;

// =====================================================
// LCD
// =====================================================

LiquidCrystal_I2C lcd(16, 2);

// =====================================================
// PINES
// =====================================================

#define TRIG_PIN 12
#define ECHO_PIN 14

#define MOTOR_IN1 27
#define MOTOR_IN2 26
#define MOTOR_ENA 25

#define SERVO1_PIN 16
#define SERVO2_PIN 17

// =====================================================
// WIFI
// =====================================================

const char* ssid = "Redmi";
const char* password = "camilo01";

IPAddress camaraIP;

// =====================================================
// PARAMETROS
// =====================================================

const float DISTANCIA_UMBRAL = 19.8;

// =====================================================
// VARIABLES MODO
// =====================================================

String modoOperacion = "rapido";

int pwmMotor = 255;
int delayMotor = 4000;
int velocidadServo = 0;
int cooldownFoto = 2000;

bool modoPrueba = false;

// =====================================================
// SERVIDOR
// =====================================================

WebServer server(80);

// =====================================================
// SERVOS
// =====================================================

Servo servo1;
Servo servo2;

// =====================================================
// ESTADOS GENERALES
// =====================================================

enum Estado {
  BLOQUEADO,
  ESPERANDO_DETECCION,
  ESPERANDO_FOTO,
  ESPERANDO_CONFIRMACION,   // nuevo estado para esperar confirmación Bluetooth
  CLASIFICANDO              // nuevo estado para proceso no bloqueante de clasificación
};

Estado estadoActual = BLOQUEADO;

// =====================================================
// VARIABLES GENERALES
// =====================================================

bool btConectado = false;
unsigned long tiempoUltimoIntentoFoto = 0;

String ultimoTimestampConfirmado = "";
String resultadoPendiente = "";

// =====================================================
// VARIABLES PARA EL MODO PRUEBA (NO BLOQUEANTE)
// =====================================================

int pasoPruebaActual = 0;          // 0 = sin paso activo, 1..4
String confirmacionEsperada = "";
unsigned long tiempoInicioEspera = 0;
const unsigned long TIMEOUT_CONFIRMACION = 10000; // 10 segundos por paso

// Variables para la clasificación no bloqueante
enum ClasificacionEstado {
  CLASIF_INICIO,
  CLASIF_MOVER_SERVOS,
  CLASIF_ESPERAR_MOTOR,
  CLASIF_FIN
};
ClasificacionEstado clasifEstado = CLASIF_INICIO;
String clasifTamanio = "";
unsigned long tiempoInicioClasif = 0;

// =====================================================
// LCD
// =====================================================

void mostrarLCD(String l1, String l2 = "") {
  lcd.clear();
  lcd.setCursor(0,0);
  if(l1.length() > 16) l1 = l1.substring(0,16);
  lcd.print(l1);
  lcd.setCursor(0,1);
  if(l2.length() > 16) l2 = l2.substring(0,16);
  lcd.print(l2);
}

// =====================================================
// DELAY NO BLOQUEANTE (SOLO PARA MOVIMIENTOS CORTOS)
// =====================================================

void delayConServidor(unsigned long tiempo) {
  unsigned long inicio = millis();
  while(millis() - inicio < tiempo) {
    server.handleClient();
    if(SerialBT.available()) {
      // Leer posibles comandos pero sin bloquear la máquina de estados
      String cmd = SerialBT.readStringUntil('\n');
      cmd.trim();
      cmd.toLowerCase();
      if(cmd == "cancelar" && estadoActual == ESPERANDO_CONFIRMACION) {
        // Cancelar espera actual
        estadoActual = ESPERANDO_DETECCION;
      }
    }
    delay(1);
  }
}

// =====================================================
// MOTOR
// =====================================================

void setMotorPWM(int valor) {
  analogWrite(MOTOR_ENA, valor);
}

void apagarMotor() {
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, LOW);
  setMotorPWM(0);
}

void encenderMotor() {
  digitalWrite(MOTOR_IN1, HIGH);
  digitalWrite(MOTOR_IN2, LOW);
  setMotorPWM(pwmMotor);
}

// =====================================================
// MODOS
// =====================================================

void configurarModo(String modo) {
  modoOperacion = modo;

  if(modo == "rapido") {
    pwmMotor = 255;
    delayMotor = 4000;
    velocidadServo = 0;
    cooldownFoto = 2000;
    modoPrueba = false;
  }
  else if(modo == "medio") {
    pwmMotor = 170;
    delayMotor = 5500;
    velocidadServo = 400;
    cooldownFoto = 3500;
    modoPrueba = false;
  }
  else if(modo == "lento") {
    pwmMotor = 85;
    delayMotor = 7000;
    velocidadServo = 700;
    cooldownFoto = 5000;
    modoPrueba = false;
  }
  else if(modo == "prueba") {
    pwmMotor = 150;
    delayMotor = 4500;
    velocidadServo = 100;
    cooldownFoto = 3000;
    modoPrueba = true;
  }

  Serial.println("================");
  Serial.println("MODO ACTUAL: " + modoOperacion);
  Serial.print("Potencia motor: "); Serial.println(pwmMotor);
  Serial.print("Espera servo (ms): "); Serial.println(velocidadServo);
  Serial.println("================");

  mostrarLCD("Modo:", modoOperacion);
  delayConServidor(1200);
}

// =====================================================
// BLUETOOTH - COMANDOS GENERALES
// =====================================================

void verificarBluetooth() {
  btConectado = SerialBT.hasClient();

  if(SerialBT.available()) {
    String recibido = SerialBT.readStringUntil('\n');
    recibido.trim();
    recibido.toLowerCase();

    // Si estamos esperando una confirmación específica
    if(estadoActual == ESPERANDO_CONFIRMACION && confirmacionEsperada != "") {
      if(recibido == confirmacionEsperada) {
        Serial.println("✅ Confirmación recibida: " + recibido);
        estadoActual = ESPERANDO_DETECCION; // temporal, luego se avanzará
        pasoPruebaActual++;
        tiempoInicioEspera = 0; // cancelar timeout
        return;
      }
      else if(recibido == "cancelar") {
        Serial.println("Cancelación recibida");
        estadoActual = ESPERANDO_DETECCION;
        pasoPruebaActual = 0;
        mostrarLCD("Cancelado", "Volviendo");
        delayConServidor(1500);
        return;
      }
    }

    // Cambio de modo en cualquier momento
    if(recibido == "rapido" || recibido == "medio" || recibido == "lento" || recibido == "prueba") {
      configurarModo(recibido);
      mostrarLCD("Modo:", recibido);
      delayConServidor(1000);
    }
    else {
      // Otros comandos (ignorar)
      Serial.print("BT -> ");
      Serial.println(recibido);
    }
  }
}

// =====================================================
// FUNCIONES PARA ENVIAR PASOS Y ESPERAR CONFIRMACIÓN (NO BLOQUEANTE)
// =====================================================

void iniciarEsperaConfirmacion(int paso) {
  pasoPruebaActual = paso;
  confirmacionEsperada = "confirmado " + String(paso);
  String mensaje = "paso " + String(paso);
  Serial.println(mensaje);
  SerialBT.println(mensaje);
  mostrarLCD("Paso " + String(paso), "Esperando...");
  tiempoInicioEspera = millis();
  estadoActual = ESPERANDO_CONFIRMACION;
}

// Comprobar si la espera actual ha excedido el timeout
void verificarTimeoutConfirmacion() {
  if(estadoActual == ESPERANDO_CONFIRMACION && tiempoInicioEspera > 0) {
    if(millis() - tiempoInicioEspera > TIMEOUT_CONFIRMACION) {
      Serial.println("Timeout esperando " + confirmacionEsperada);
      mostrarLCD("Timeout", "Reintente");
      delayConServidor(1500);
      estadoActual = ESPERANDO_DETECCION;
      pasoPruebaActual = 0;
    }
  }
}

// =====================================================
// SERVOS (MOVIMIENTO DIRECTO)
// =====================================================

void escribirServo1(int angulo) {
  if(angulo < 10) angulo = 10;
  if(angulo > 170) angulo = 170;
  servo1.write(angulo);
  if(velocidadServo > 0) delayConServidor(velocidadServo);
}

void escribirServo2(int angulo) {
  if(angulo < 10) angulo = 10;
  if(angulo > 170) angulo = 170;
  servo2.write(angulo);
  if(velocidadServo > 0) delayConServidor(velocidadServo);
}

void estado_inicial() {
  escribirServo1(50);
  escribirServo2(0);
}

// =====================================================
// SENSOR ULTRASÓNICO
// =====================================================

float medirDistancia() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duracion = pulseIn(ECHO_PIN, HIGH, 30000);
  if(duracion == 0) return -1;
  return duracion * 0.0343 / 2;
}

// =====================================================
// CÁMARA
// =====================================================

bool enviarSolicitudFoto() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("❌ WiFi desconectado");
    mostrarLCD("ERROR WIFI", "Sin conexion");
    return false;
  }

  HTTPClient http;
  String url = "http://" + camaraIP.toString() + "/detectar";

  Serial.println("");
  Serial.println("================================");
  Serial.println("📸 ENVIANDO SOLICITUD");
  Serial.println(url);
  Serial.println("================================");

  mostrarLCD("Tomando foto", "ESP32-CAM");

  http.begin(url);
  http.setConnectTimeout(1000);
  http.setTimeout(1000);

  int codigo = http.GET();
  Serial.print("📡 Codigo HTTP: ");
  Serial.println(codigo);

  if (codigo > 0) {
    String payload = http.getString();
    Serial.print("📨 Respuesta: ");
    Serial.println(payload);
    mostrarLCD("Foto enviada", "Procesando");
    http.end();
    return true;
  } else {
    Serial.print("❌ ERROR GET: ");
    Serial.println(codigo);
    mostrarLCD("Error Camara", String(codigo));
    http.end();
    return false;
  }
}

// =====================================================
// CLASIFICACIÓN NO BLOQUEANTE (MÁQUINA DE ESTADOS)
// =====================================================

void iniciarClasificacion(String tamanio) {
  clasifTamanio = tamanio;
  clasifEstado = CLASIF_INICIO;
  estadoActual = CLASIFICANDO;
}

void procesarClasificacion() {
  if(estadoActual != CLASIFICANDO) return;

  switch(clasifEstado) {
    case CLASIF_INICIO:
      Serial.println("Clasificando: " + clasifTamanio);
      mostrarLCD(clasifTamanio, "Clasificando");
      apagarMotor();
      clasifEstado = CLASIF_MOVER_SERVOS;
      tiempoInicioClasif = millis();
      break;

    case CLASIF_MOVER_SERVOS:
      // Movimientos específicos según tamaño
      if(clasifTamanio == "PEQUENO") {
        escribirServo2(38);
        escribirServo1(10);
      }
      else if(clasifTamanio == "MEDIANO") {
        escribirServo2(170);
        escribirServo1(95);
      }
      else if(clasifTamanio == "GRANDE") {
        escribirServo2(90);
        escribirServo1(50);
      }
      delayConServidor(300); // pausa corta antes de encender motor
      encenderMotor();
      mostrarLCD(clasifTamanio, "Moviendo");
      clasifEstado = CLASIF_ESPERAR_MOTOR;
      tiempoInicioClasif = millis();
      break;

    case CLASIF_ESPERAR_MOTOR:
      if(millis() - tiempoInicioClasif >= delayMotor) {
        apagarMotor();
        estado_inicial();
        clasifEstado = CLASIF_FIN;
      }
      break;

    case CLASIF_FIN:
      mostrarLCD(clasifTamanio, "Listo");
      delayConServidor(1000);
      // Finalizar clasificación
      estadoActual = ESPERANDO_DETECCION;
      clasifEstado = CLASIF_INICIO;
      pasoPruebaActual = 0; // Reiniciar pasos de prueba
      // En modo prueba, después de la clasificación se esperaba paso 4, pero eso se maneja aparte
      break;
  }
}

// =====================================================
// SERVIDOR WEB
// =====================================================

void configurarServidor() {
  server.on("/resultado", HTTP_POST, []() {
    resultadoPendiente = server.arg("plain");
    Serial.println("");
    Serial.println("================================");
    Serial.println("📥 RESULTADO RECIBIDO");
    Serial.println("================================");
    Serial.println(resultadoPendiente);
    mostrarLCD("Resultado", "Recibido");
    server.send(200, "text/plain", "OK");
  });
  server.begin();
  Serial.println("🌐 Servidor HTTP listo");
  mostrarLCD("Servidor", "Iniciado");
  delayConServidor(1000);
}

// =====================================================
// PROCESAR RESULTADO CON MODO PRUEBA ASÍNCRONO
// =====================================================

void procesarResultadoPendiente() {
  if(resultadoPendiente == "") return;

  String body = resultadoPendiente;
  resultadoPendiente = "";

  // Extraer timestamp
  String timestamp = "";
  int idx = body.indexOf("\"timestamp\":");
  if(idx != -1) {
    int start = body.indexOf("\"", idx + 12) + 1;
    int end = body.indexOf("\"", start);
    timestamp = body.substring(start, end);
  }
  Serial.print("🕒 Timestamp: ");
  Serial.println(timestamp);

  if(timestamp == "" || timestamp == "null") {
    Serial.println("⚠️ Timestamp inválido");
    return;
  }
  if(timestamp == ultimoTimestampConfirmado) {
    Serial.println("⚠️ Duplicado ignorado");
    return;
  }
  ultimoTimestampConfirmado = timestamp;

  // Determinar tamaño
  String tamanio = "";
  if(body.indexOf("PEQUE") != -1) tamanio = "PEQUENO";
  else if(body.indexOf("MEDIANO") != -1) tamanio = "MEDIANO";
  else if(body.indexOf("GRANDE") != -1) tamanio = "GRANDE";
  else {
    Serial.println("Tamaño no reconocido");
    return;
  }

  // Si estamos en modo prueba, se debe pasar por el paso 2 (confirmación) ANTES de clasificar
  if(modoPrueba) {
    // Guardar el tamaño para usarlo después de la confirmación
    // Usaremos una variable temporal para recordar el tamaño pendiente
    static String tamanioPendiente = "";
    if(estadoActual == ESPERANDO_DETECCION) {
      // Iniciamos la espera del paso 2
      tamanioPendiente = tamanio;
      iniciarEsperaConfirmacion(2);
      // No clasificar aún
      return;
    }
    else if(estadoActual == ESPERANDO_CONFIRMACION && pasoPruebaActual == 2 && confirmacionEsperada == "confirmado 2") {
      // La confirmación se recibirá en el loop, entonces cuando se reciba, debemos clasificar
      // Para ello, guardaremos el tamaño en una variable global y después de la confirmación se usa
      // Lo haremos con una variable global "tamanioParaClasificar"
    }
    // NOTA: La confirmación se maneja en verificarBluetooth, que al recibir "confirmado 2" pasará estadoActual a ESPERANDO_DETECCION y aumentará pasoPruebaActual.
    // Entonces debemos engancharnos allí: cuando se confirma paso 2, se inicia la clasificación.
    // Para simplificar, haremos que tras recibir confirmación del paso 2, se llame a iniciarClasificacion con el tamaño pendiente.
    // Por ello, en verificarBluetooth, después de procesar la confirmación, debemos comprobar si hay un tamaño pendiente.
  }
  else {
    // Modo normal (rápido/medio/lento): clasificar directamente
    iniciarClasificacion(tamanio);
  }
}

// Para almacenar el tamaño pendiente en modo prueba y que se use tras confirmación
String tamanioPendienteClasificacion = "";

// Modificamos ligeramente verificarBluetooth para gestionar la transición después de confirmación
void verificarBluetoothConClasificacion() {
  verificarBluetooth(); // llama a la original

  // Si acabamos de recibir una confirmación y estamos en modo prueba y el paso era 2, entonces clasificamos
  if(modoPrueba && pasoPruebaActual == 3 && tamanioPendienteClasificacion != "") {
    // Se espera que después de confirmar paso 2, pasoPruebaActual se incremente a 3 (por la lógica de iniciarEsperaConfirmacion)
    // Pero cuidado: iniciarEsperaConfirmacion incrementa pasoPruebaActual después de recibir confirmación.
    // Para evitar complicaciones, usaremos una variable flag.
    iniciarClasificacion(tamanioPendienteClasificacion);
    tamanioPendienteClasificacion = "";
    pasoPruebaActual = 0; // reseteamos después de clasificar
  }
}

// Reemplazamos la función verificarBluetooth por esta nueva
void verificarBluetoothActualizada() {
  // Código original de verificarBluetooth pero con agregado al final
  btConectado = SerialBT.hasClient();

  if(SerialBT.available()) {
    String recibido = SerialBT.readStringUntil('\n');
    recibido.trim();
    recibido.toLowerCase();

    if(estadoActual == ESPERANDO_CONFIRMACION && confirmacionEsperada != "") {
      if(recibido == confirmacionEsperada) {
        Serial.println("✅ Confirmación recibida: " + recibido);
        // Avanzamos según el paso
        if(pasoPruebaActual == 1) {
          // Paso 1 confirmado: seguir con la foto (se maneja en el loop)
          estadoActual = ESPERANDO_DETECCION;
          pasoPruebaActual = 0; // ya no se necesita más
          // El loop continuará y tomará la foto porque detectó previamente? Cuidado.
          // Realmente después de confirmar paso 1, debemos tomar la foto inmediatamente.
          // Para ello, podemos usar una bandera "tomarFotoPendiente = true"
        }
        else if(pasoPruebaActual == 2) {
          // Paso 2 confirmado: hay que clasificar con el tamaño pendiente
          estadoActual = ESPERANDO_DETECCION;
          pasoPruebaActual = 0;
          if(tamanioPendienteClasificacion != "") {
            iniciarClasificacion(tamanioPendienteClasificacion);
            tamanioPendienteClasificacion = "";
          }
        }
        else if(pasoPruebaActual == 3) {
          // Paso 3 confirmado: continuar la clasificación (ya estaba en proceso)
          estadoActual = CLASIFICANDO; // Aseguramos que siga clasificando
          pasoPruebaActual = 0;
        }
        else if(pasoPruebaActual == 4) {
          // Paso 4 confirmado: finalizar ciclo
          estadoActual = ESPERANDO_DETECCION;
          pasoPruebaActual = 0;
          mostrarLCD("Exitoso", "Emoji");
          delayConServidor(1500);
        }
        confirmacionEsperada = "";
        tiempoInicioEspera = 0;
        return;
      }
      else if(recibido == "cancelar") {
        Serial.println("Cancelación recibida");
        estadoActual = ESPERANDO_DETECCION;
        pasoPruebaActual = 0;
        confirmacionEsperada = "";
        mostrarLCD("Cancelado", "Volviendo");
        delayConServidor(1500);
        return;
      }
    }

    // Cambio de modo
    if(recibido == "rapido" || recibido == "medio" || recibido == "lento" || recibido == "prueba") {
      configurarModo(recibido);
      mostrarLCD("Modo:", recibido);
      delayConServidor(1000);
    }
  }
}

// Sobrescribimos la función anterior (renombramos para no duplicar)
#define verificarBluetooth verificarBluetoothActualizada

// =====================================================
// SETUP
// =====================================================

void setup() {
  Serial.begin(115200);
  SerialBT.begin("ESP32_LIMONES");

  Wire.begin(21,22);
  lcd.setAddress(0x27);
  lcd.begin();
  lcd.backlight();
  mostrarLCD("Iniciando");

  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  pinMode(MOTOR_ENA, OUTPUT);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  servo1.attach(SERVO1_PIN);
  servo2.attach(SERVO2_PIN);
  estado_inicial();

  // WiFi
  mostrarLCD("Conectando", "WiFi...");
  WiFi.begin(ssid, password);
  while(WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado");

  IPAddress ip = WiFi.localIP();
  IPAddress gateway = WiFi.gatewayIP();
  IPAddress subnet = WiFi.subnetMask();
  IPAddress dns = WiFi.dnsIP();

  IPAddress staticIP(ip[0], ip[1], ip[2], 11);
  camaraIP = IPAddress(ip[0], ip[1], ip[2], 56);

  WiFi.disconnect(true);
  delay(1000);
  WiFi.config(staticIP, gateway, subnet, dns);
  WiFi.begin(ssid, password);
  while(WiFi.status() != WL_CONNECTED) delay(500);

  Serial.print("ESP32 -> ");
  Serial.println(WiFi.localIP());
  Serial.print("CAM -> ");
  Serial.println(camaraIP);

  mostrarLCD("WiFi OK", WiFi.localIP().toString());
  delayConServidor(1500);

  configurarServidor();
  configurarModo("rapido");
  mostrarLCD("Esperando", "Limon...");
  estadoActual = ESPERANDO_DETECCION;
}

// =====================================================
// LOOP PRINCIPAL (NO BLOQUEANTE)
// =====================================================

void loop() {
  server.handleClient();
  verificarBluetooth();
  verificarTimeoutConfirmacion();
  procesarClasificacion(); // Maneja la máquina de estados de clasificación

  // Fotografía pendiente (tras confirmación paso 1)
  static bool fotoPendiente = false;
  static String timestampPendiente = "";

  if(estadoActual == ESPERANDO_DETECCION && fotoPendiente) {
    fotoPendiente = false;
    if(enviarSolicitudFoto()) {
      estadoActual = ESPERANDO_FOTO;
      mostrarLCD("Esperando", "Resultado...");
    } else {
      mostrarLCD("Error", "Camara");
    }
    return;
  }

  // Detección normal
  if(estadoActual == ESPERANDO_DETECCION) {
    float dist = medirDistancia();
    if(dist > 0 && dist < DISTANCIA_UMBRAL) {
      if(millis() - tiempoUltimoIntentoFoto >= cooldownFoto) {
        Serial.println("🍋 Limon detectado: " + String(dist) + " cm");
        mostrarLCD("Detectado", "Tomando foto");

        if(modoPrueba) {
          // Iniciar paso 1 de prueba
          iniciarEsperaConfirmacion(1);
          // Guardamos que después de confirmar hay que tomar foto
          fotoPendiente = true;
        } else {
          // Modo normal: tomar foto directamente
          if(enviarSolicitudFoto()) {
            estadoActual = ESPERANDO_FOTO;
            mostrarLCD("Esperando", "Resultado...");
          } else {
            mostrarLCD("Error", "Camara");
          }
        }
        tiempoUltimoIntentoFoto = millis();
      }
    }
  }
  else if(estadoActual == ESPERANDO_FOTO) {
    // Esperar a que llegue el resultado por HTTP (se procesa en resultadoPendiente)
    // No hacer nada aquí
  }

  // Procesar resultado pendiente (llamada después de recibir HTTP)
  // Esto debe hacerse regularmente, pero sin interferir con la máquina de estados
  static unsigned long ultimoProcesamiento = 0;
  if(millis() - ultimoProcesamiento > 100 && resultadoPendiente != "") {
    ultimoProcesamiento = millis();
    // Función que extrae el tamaño y, si modo prueba, inicia espera de paso 2
    String body = resultadoPendiente;
    resultadoPendiente = "";
    // Extraer timestamp y tamaño...
    String timestamp = "";
    int idx = body.indexOf("\"timestamp\":");
    if(idx != -1) {
      int start = body.indexOf("\"", idx + 12) + 1;
      int end = body.indexOf("\"", start);
      timestamp = body.substring(start, end);
    }
    if(timestamp != "" && timestamp != "null" && timestamp != ultimoTimestampConfirmado) {
      ultimoTimestampConfirmado = timestamp;
      String tamanio = "";
      if(body.indexOf("PEQUE") != -1) tamanio = "PEQUENO";
      else if(body.indexOf("MEDIANO") != -1) tamanio = "MEDIANO";
      else if(body.indexOf("GRANDE") != -1) tamanio = "GRANDE";
      else return;

      if(modoPrueba) {
        // Guardar el tamaño y esperar confirmación paso 2
        tamanioPendienteClasificacion = tamanio;
        iniciarEsperaConfirmacion(2);
      } else {
        iniciarClasificacion(tamanio);
      }
    }
  }

  delay(10);
}