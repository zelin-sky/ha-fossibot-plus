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

---

## 🙏 Acknowledgements / Подяки

---

### 🇬🇧 English

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
| **Режим зарядки** | UPS / ECO | UPS — миттєве перемикання без зупинки (для чутливої техніки); ECO — ефективне заряджання з відключенням по-завершенні |

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
