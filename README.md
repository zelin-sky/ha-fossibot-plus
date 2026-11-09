<div align="center">

# 🔋 FOSSiBOT Power Station for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## 🇬🇧 English

Monitor and control your FOSSiBOT power station directly from Home Assistant. See battery level, power consumption, charging status in real time — and control outputs without touching the app.

### Supported devices

| Model | Status |
|-------|--------|
| FOSSiBOT F1800 | ✅ Tested |
| FOSSiBOT F3000 | ✅ Tested |
| Other Fossibot+ models | ⚠️ May work |

Multiple stations in one account are supported — each gets its own device with its serial number in the name (e.g. `Fossibot-F180V012605B4936`).

---
## ⚠️ Prerequisites

This integration supports three connection modes:

- **Cloud**: the station is connected to Wi-Fi and visible as online in the Fossibot+ app.
- **Home network (no cloud)**: the station stays on your Wi-Fi and connects to Home Assistant instead of the cloud, through a LAN DNS override.
- **Local Wi-Fi AP**: Home Assistant connects to the station's `FOSS_<serial>` Wi-Fi network and listens for the station's TCP connection.

It communicates through the FOSSiBOT cloud API — the same channel the mobile app uses when your station is on your home network. **Bluetooth is not used** and is not required.

Before adding this integration to Home Assistant, make sure:
1. Your power station is connected to Wi-Fi via the **Fossibot+** app.
2. The device shows as **online** in the app.
3. You have a working Fossibot+ account (email + password).

If you can't pair the device in the Fossibot+ app, please contact FOSSiBOT support — that step is handled entirely by the app and is outside the scope of this integration.

### Home network mode (no cloud)

Select **Home network (no cloud)** when adding the integration. The station stays on
your home Wi-Fi and connects to Home Assistant instead of the FOSSiBOT cloud. It looks
up `app.fossibot.hk` and opens a plain TCP connection to port `5555`, so a small relay can
take the place of that endpoint and pass the data to Home Assistant.

The relay is required for reliable use. In testing, the station left Wi-Fi about 75 seconds
after losing its server and needed a manual restart, so a direct connection would not survive a
Home Assistant restart. [`tools/fossibot_relay.py`](tools/fossibot_relay.py) holds the station's
connection while Home Assistant restarts. Python only, no dependencies.

You need:

1. A LAN DNS server that answers `app.fossibot.hk` with the relay host's IP.
   If possible, limit this to the station's IP, so other devices keep reaching the real
   cloud. If your router cannot do this itself, point its DHCP DNS setting at a DNS
   server on an always-on device, because every client using it depends on that device.
2. A fixed IP for the station and for Home Assistant (DHCP reservations).
3. The relay running on an always-on host, started at boot, for example:
   `python3 tools/fossibot_relay.py <host-ip> 5555 <station-ip> 127.0.0.1 5556`.
   Then accept the form's defaults (`127.0.0.1`, port `5556`) when adding the entry.
4. The station restarted after the DNS change, so that it picks up the new DNS server.

While this is active, the Fossibot+ app's online mode, cloud charge schedules and
firmware update checks do not work for the station. To go back, remove the DNS override
and restart the station. Remove any cloud entry for the same station first, because both
entries would create the same device.

The relay accepts only the configured station IP, but traffic on your LAN is
unencrypted and unauthenticated. This relies on undocumented behaviour tested on firmware
`10-01-02-07`, and a firmware update could end it. Do not use it for safety-critical
control.

### Local Wi-Fi AP mode

Select **Local Wi-Fi AP** when adding the integration. Connect the Home Assistant
host to the station Wi-Fi network (`FOSS_<serial>`), then configure the station
serial number and TCP port `8058`. The station initiates the TCP connection to
Home Assistant; Home Assistant does not connect to the station.

This mode uses the reverse-engineered binary protocol documented in
[`Enduranc3/fossibot-control`](https://github.com/Enduranc3/fossibot-control/blob/main/PROTOCOL.md).
The station's AP password and IP range are firmware-dependent. The integration
does not require Fossibot cloud credentials in local mode. If the Home Assistant
host has multiple network interfaces, bind the listener to the appropriate
address and optionally restrict the client IP prefix.

Local mode is firmware-dependent and should be tested with the station before
relying on it for automation or safety-critical control.

---

## 🙏 Acknowledgements

**Special thanks to everyone who contributed to making this integration better:**

- [**OleksiiSaviuk**](https://github.com/OleksiiSaviuk) — for the valuable pull request that added new controls and sensors, including standby timers, charge/discharge limits, screen brightness, DC charge current, and the important frame-merge fix in the coordinator.

- [**@bootuseua**](https://www.youtube.com/@bootuseua) — for additional real-world testing, and for mentioning this project in videos and in the Telegram channel. Your support helps the community discover and use this integration.

---


### 📊 Sensors

| Name | Unit | Description |
|------|------|-------------|
| **Battery** | % | Current battery charge level |
| **Temperature** | °C | Internal station temperature |
| **Time remaining** | min | Time until fully charged or discharged |
| **Charging** | — | Shows whether the station is actively charging (1) or not (0) |
| **AC output power** | W | Power currently delivered through AC outlets |
| **USB output power** | W | Power currently delivered through USB ports |
| **Total output power** | W | Combined output across all ports (AC + USB) |
| **AC output voltage** | V | Voltage on the AC output (~230 V when active) |
| **AC frequency** | Hz | AC output frequency (50.0 Hz) |
| **AC grid power** | W | Power drawn from the mains socket while charging |
| **Total input power** | W | Total charging input: mains + solar panel combined |
| **Charge power** | W | Read-back of the current charge power limit setting |

---

### 🎛️ Controls

#### Switches
| Name | Description |
|------|-------------|
| **AC output** | Turn AC outlets on or off |
| **DC output** | Turn 12V DC port on or off |
| **USB output** | Turn USB ports on or off |
| **Sound** | Enable or disable beep notifications |
| **Output memory** | Remember output states after a power cut |

#### Dropdowns
| Name | Options | Description |
|------|---------|-------------|
| **LED mode** | Off / Steady / SOS / Strobe | Control the built-in flashlight |
| **Charge mode** | UPS / ECO | Switch between bypass (UPS) and efficient (ECO) charging mode |

#### Number
| Name | Range | Description |
|------|-------|-------------|
| **Charge power limit** | 100–1200 W (F1800) / 100–2000 W (F3000) | Set how much power the station draws while charging. Detected automatically from the serial number. |

---

### 🚀 Installation

**Via HACS (recommended)**
1. HACS → ⋮ → **Custom repositories** → add `https://github.com/zelin-sky/ha-fossibot-plus` → category: **Integration**
2. Find **FOSSiBOT Power Station** → **Download**
3. Restart Home Assistant
4. **Settings → Devices & Services → Add Integration → FOSSiBOT Power Station**
5. Enter the email and password from the **Fossibot+** app

**Manual**
1. Copy `custom_components/fossibot_plus/` to `<config>/custom_components/`
2. Restart Home Assistant and add the integration as above

---


## 🇺🇦 Українська

Моніторинг та керування зарядною станцією FOSSiBOT прямо з Home Assistant. Рівень заряду, споживання, статус зарядки в реальному часі — і повне керування виходами без відкриття застосунку.

### Підтримувані пристрої

| Модель | Статус |
|--------|--------|
| FOSSiBOT F1800 | ✅ Протестовано |
| FOSSiBOT F3000 | ✅ Протестовано |
| Інші моделі Fossibot+ | ⚠️ Можливо сумісні |

Підтримується декілька станцій в одному обліковому записі — кожна отримує окремий пристрій із серійним номером у назві (наприклад `Fossibot-F180V012605B4936`).

---

## ⚠️ Передумови

Ця інтеграція працює **тільки з пристроями, підключеними до Wi-Fi**, які відображаються як **онлайн** у застосунку Fossibot+.

Вона використовує хмарний API FOSSiBOT — той самий канал, через який мобільний застосунок спілкується зі станцією, коли та підключена до вашої домашньої мережі. **Bluetooth не використовується** і не потрібен.

Перед додаванням інтеграції в Home Assistant переконайтеся що:
1. Ваша зарядна станція підключена до Wi-Fi через застосунок **Fossibot+**.
2. Пристрій відображається як **онлайн** у застосунку.
3. У вас є обліковий запис Fossibot+ (email + пароль).

Якщо не вдається підключити пристрій у застосунку Fossibot+ — зверніться до підтримки FOSSiBOT. Цей крок виконується виключно через застосунок і не пов'язаний з цією інтеграцією.

### Режим домашньої мережі (без хмари)

Під час додавання інтеграції виберіть **Домашня мережа (без хмари)**. Станція лишається
у домашньому Wi-Fi і підключається до Home Assistant замість хмари FOSSiBOT. Вона
запитує адресу `app.fossibot.hk` і відкриває звичайне TCP-з'єднання на порт `5555`, тому
невеликий релей може замінити цей сервер і передавати дані в Home Assistant.

Для надійної роботи релей обов'язковий. Під час тестів станція вимикала Wi-Fi приблизно через
75 секунд після втрати сервера і потребувала ручного перезапуску, тому пряме з'єднання не
переживе перезапуск Home Assistant. [`tools/fossibot_relay.py`](tools/fossibot_relay.py) тримає
з'єднання зі станцією, поки Home Assistant перезапускається. Потрібен лише Python.

Вам потрібно:

1. DNS-сервер у локальній мережі, який повертає для `app.fossibot.hk` IP-адресу хоста
   релея. Бажано обмежити це IP-адресою станції, щоб інші пристрої й далі
   бачили справжню хмару. Якщо роутер цього не вміє, вкажіть у його налаштуваннях DHCP
   DNS-сервер на пристрої, що працює постійно: від нього залежатимуть усі клієнти.
2. Постійна IP-адреса для станції та Home Assistant (резервування DHCP).
3. Релей на пристрої, що працює постійно і запускає його під час старту, наприклад:
   `python3 tools/fossibot_relay.py <ip-хоста> 5555 <ip-станції> 127.0.0.1 5556`.
   Потім під час додавання запису прийміть типові значення форми (`127.0.0.1`, порт `5556`).
4. Перезапуск станції після зміни DNS, щоб вона отримала новий DNS-сервер.

Поки цей режим діє, для станції не працюють онлайн-режим застосунку Fossibot+, хмарні
розклади заряджання та перевірка оновлень. Щоб повернутися, приберіть підміну DNS і
перезапустіть станцію. Спершу видаліть хмарний запис цієї станції, якщо він є, бо обидва
записи створять той самий пристрій.

Релей приймає лише вказану IP-адресу станції, але трафік у локальній мережі не
шифрується і не автентифікується. Цей режим спирається на недокументовану поведінку,
перевірену на прошивці `10-01-02-07`, і оновлення прошивки може його зламати. Не
використовуйте його для критичного щодо безпеки керування.

### Локальний режим точки доступу Wi-Fi

Під час додавання інтеграції виберіть **Локальна Wi-Fi точка доступу**.
Підключіть Home Assistant до мережі станції `FOSS_<серійний_номер>` і
налаштуйте TCP-порт `8058`. Станція сама ініціює TCP-з'єднання з Home
Assistant. Хмарні облікові дані в цьому режимі не потрібні.

Режим використовує реверс-інжиніринговий бінарний протокол, тому сумісність
залежить від прошивки. Пароль точки доступу та діапазон IP можуть відрізнятися.

---

## 🙏 Подяки

**Щира подяка всім, хто допоміг зробити цю інтеграцію кращою:**

- [**OleksiiSaviuk**](https://github.com/OleksiiSaviuk) — за цінний pull request із додаванням нових елементів керування та сенсорів: таймери standby, ліміти заряду/розряду, яскравість екрану, струм DC заряду, а також важливе виправлення злиття WS-фреймів у координаторі.

- [**@bootuseua**](https://www.youtube.com/@bootuseua) — за додаткове реальне тестування та за згадки цього проєкту у відео та телеграм-каналі. Ваша підтримка допомагає спільноті дізнаватися про інтеграцію та користуватися нею.

---

### 📊 Сенсори

| Назва | Одиниці | Що показує |
|-------|---------|-----------|
| **Заряд батареї** | % | Поточний рівень заряду акумулятора |
| **Температура** | °C | Внутрішня температура станції |
| **Залишок часу** | хв | Час до повного заряду або до розряду |
| **Заряджання** | — | Чи заряджається станція зараз (1) чи ні (0) |
| **Вихідна потужність AC** | W | Потужність, яка зараз видається через розетки |
| **Вихідна потужність USB** | W | Потужність, яка зараз видається через USB-порти |
| **Загальна вихідна потужність** | W | Сумарне навантаження на всі виходи (AC + USB) |
| **Вихідна напруга AC** | V | Напруга на виході розеток (~230 В коли увімкнено) |
| **Частота мережі** | Hz | Частота AC-виходу (50.0 Гц) |
| **Потужність від мережі** | W | Скільки потужності береться з розетки під час зарядки |
| **Сумарна вхідна потужність** | W | Загальна вхідна потужність: мережа + сонячна панель |
| **Потужність заряджання** | W | Поточне встановлене обмеження потужності зарядки |

---

### 🎛️ Керування

#### Перемикачі
| Назва | Що робить |
|-------|-----------|
| **Змінний струм (AC)** | Вмикає/вимикає розетки змінного струму |
| **Постійний струм (DC)** | Вмикає/вимикає DC-вихід 12V |
| **USB** | Вмикає/вимикає USB-порти |
| **Звук** | Вмикає/вимикає звукові сигнали станції |
| **Пам'ять виходів** | Запам'ятовує стан виходів після відновлення живлення |

#### Дропдауни
| Назва | Варіанти | Опис |
|-------|----------|------|
| **Режим LED** | Вимкнено / Постійний / SOS / Стробоскоп | Керування вбудованим ліхтарем |
| **Режим зарядки** | UPS / ECO | UPS — миттєве перемикання без зупинки, режим ДБЖ ; ECO — Сонячна панель->Батарея->Мережа |

#### Числовий регулятор
| Назва | Діапазон | Опис |
|-------|----------|------|
| **Потужність заряджання (ліміт)** | 100–1200 W (F1800) / 100–2000 W (F3000) | Встановлює максимальну потужність, яку станція споживає під час зарядки. Крок — 100 W. Діапазон визначається автоматично з серійного номера. |

---

### 🚀 Встановлення

**Через HACS (рекомендовано)**
1. HACS → ⋮ → **Custom repositories** → додайте `https://github.com/zelin-sky/ha-fossibot-plus` → категорія: **Integration**
2. Знайдіть **FOSSiBOT Power Station** → **Download**
3. Перезапустіть Home Assistant
4. **Налаштування → Пристрої та служби → Додати інтеграцію → FOSSiBOT Power Station**
5. Введіть email та пароль від застосунку **Fossibot+**

**Вручну**
1. Скопіюйте `custom_components/fossibot_plus/` до `<config>/custom_components/`
2. Перезапустіть Home Assistant і додайте інтеграцію як описано вище

---

<div align="center">

Зроблено з ❤️. Зроблено в Україні.

</div>
