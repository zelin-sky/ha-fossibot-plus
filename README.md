<div align="center">

# 🔋 FOSSiBOT Power Station for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---
Monitor and control your FOSSiBOT power station directly from Home Assistant. See battery level, power consumption, charging status in real time — and control outputs without touching the app.

### Supported devices

| Model | Status |
|-------|--------|
| FOSSiBOT F1800 | ✅ Tested |
| FOSSiBOT F3000 | ✅ Tested |
| Other Fossibot+ models | ⚠️ May work |

Multiple stations in one account are supported — each gets its own device with its serial number in the name (e.g. `Fossibot-F180V012605B4936`).

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
| **Total output power** | W | Combined output across all ports (AC + DC + USB) |
| **AC output voltage** | V | Voltage on the AC output (~230 V when active) |
| **AC frequency** | Hz | AC output frequency (50.0 Hz) |
| **AC grid power** | W | Power drawn from the mains socket while charging |
| **Total input power** | W | Total charging input: mains + solar panel combined |
| **Charge power** | W | Read-back of the current charge power limit setting |
| **Battery voltage** | V | Battery pack voltage |
| **Battery current** | A | Battery current (sign shows charge / discharge) |
| **DC input power** | W | Solar / car / external battery input power |
| **DC input voltage** | V | Voltage on the DC (PV) input |
| **DC input current** | A | Current on the DC (PV) input |
| **DC input energy** | kWh | Energy received through the DC input |
| **DC output power** | W | Power delivered through the 12V DC port |
| **Inverter temperature** | °C | Inverter temperature |
| *Diagnostic* | — | Battery min temperature, BMS MOS / MOS temperature, BMS / PCS / DC input fault codes (raw value, `0` = no fault), firmware, BMS and PCS versions (e.g. `01-02-03-04`) |

> F3000 does not send battery voltage/current, DC input voltage/current, inverter / MOS temperatures and fault codes to the cloud, so these show *Unknown* there. They are kept to check other models — please report if they work on yours.

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
| **DC / USB / AC standby** | Never / 30 min / 1 / 4 / 8 / 12 / 24 h | Auto-off of the output when there is no load |
| **Screen timeout** | Always on / 30 s / 1 / 5 / 10 / 30 min | Display auto-off |
| **Power-off timer** | Never / 5 / 10 min / 1 / 8 h | Station auto power-off |

#### Number
| Name | Range | Description |
|------|-------|-------------|
| **Charge power limit** | 100–1200 W (F1800) / 100–2000 W (F3000) | Set how much power the station draws while charging. Detected automatically from the serial number. |
| **DC charge current** | 1–15 A (F1800) / 1–25 A (F3000) | DC input charge current. Values above 8 A may require the extended mode in the Fossibot app. |
| **Charge limit** | 60–100 % | Stop charging at this level |
| **Discharge limit** | 0–20 % | Stop discharging at this level |
| **Screen brightness** | 0–100 % | Display brightness |

> Standby dropdowns and screen brightness are in the device's **Configuration** section; fault codes, firmware and internal temperatures are in **Diagnostic**.

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

### 🙏 Credits

The register map for battery, DC input/output sensors and extra settings comes from [Enduranc3/fossibot-control](https://github.com/Enduranc3/fossibot-control) (decoded from the official app). These were tested on the F3000 only — if a value looks wrong on your model, please open an issue.

---

---


Моніторинг та керування зарядною станцією FOSSiBOT прямо з Home Assistant. Рівень заряду, споживання, статус зарядки в реальному часі — і повне керування виходами без відкриття застосунку.

### Підтримувані пристрої

| Модель | Статус |
|--------|--------|
| FOSSiBOT F1800 | ✅ Протестовано |
| FOSSiBOT F3000 | ✅ Протестовано |
| Інші моделі Fossibot+ | ⚠️ Можливо сумісні |

Підтримується декілька станцій в одному обліковому записі — кожна отримує окремий пристрій із серійним номером у назві (наприклад `Fossibot-F180V012605B4936`).

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
| **Загальна вихідна потужність** | W | Сумарне навантаження на всі виходи (AC + DC + USB) |
| **Вихідна напруга AC** | V | Напруга на виході розеток (~230 В коли увімкнено) |
| **Частота мережі** | Hz | Частота AC-виходу (50.0 Гц) |
| **Потужність від мережі** | W | Скільки потужності береться з розетки під час зарядки |
| **Сумарна вхідна потужність** | W | Загальна вхідна потужність: мережа + сонячна панель |
| **Потужність заряджання** | W | Поточне встановлене обмеження потужності зарядки |
| **Напруга батареї** | V | Напруга батарейного пакета |
| **Струм батареї** | A | Струм батареї (знак показує заряд / розряд) |
| **Потужність DC-входу** | W | Вхід від сонця / авто / зовнішньої батареї |
| **Напруга DC-входу** | V | Напруга на DC (PV) вході |
| **Струм DC-входу** | A | Струм на DC (PV) вході |
| **Енергія DC-входу** | kWh | Скільки енергії отримано через DC-вхід |
| **Потужність DC-виходу** | W | Потужність на виході DC 12V |
| **Температура інвертора** | °C | Температура інвертора |
| *Діагностика* | — | Мін. температура батареї, температура MOS BMS / MOS, коди помилок BMS / PCS / DC-входу (сире значення, `0` — без помилок), прошивка, версії BMS і PCS (напр. `01-02-03-04`) |

> F3000 не надсилає в хмару напругу/струм батареї, напругу/струм DC-входу, температури інвертора / MOS і коди помилок, тому там вони показують *Невідомо*. Їх залишено для перевірки на інших моделях — повідомте, якщо на вашій вони працюють.

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
| **Автовимкнення DC / USB / AC** | Ніколи / 30 хв / 1 / 4 / 8 / 12 / 24 год | Вимкнення виходу, якщо немає навантаження |
| **Час вимкнення екрана** | Завжди / 30 с / 1 / 5 / 10 / 30 хв | Автовимкнення дисплея |
| **Час вимкнення станції** | Ніколи / 5 / 10 хв / 1 / 8 год | Автовимкнення станції |

#### Числовий регулятор
| Назва | Діапазон | Опис |
|-------|----------|------|
| **Потужність заряджання (ліміт)** | 100–1200 W (F1800) / 100–2000 W (F3000) | Встановлює максимальну потужність, яку станція споживає під час зарядки. Крок — 100 W. Діапазон визначається автоматично з серійного номера. |
| **Струм DC-заряду** | 1–15 A (F1800) / 1–25 A (F3000) | Струм заряду через DC-вхід. Понад 8 A може знадобитися розширений режим у застосунку Fossibot. |
| **Ліміт заряду** | 60–100 % | Зупинити заряд на цьому рівні |
| **Ліміт розряду** | 0–20 % | Зупинити розряд на цьому рівні |
| **Яскравість екрана** | 0–100 % | Яскравість дисплея |

> Автовимкнення виходів і яскравість екрана — у розділі **Конфігурація** пристрою; коди помилок, прошивка та внутрішні температури — у розділі **Діагностика**.

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

### 🙏 Подяки

Карту регістрів для сенсорів батареї, DC-входу/виходу та додаткових налаштувань взято з [Enduranc3/fossibot-control](https://github.com/Enduranc3/fossibot-control) (розшифровано з офіційного застосунку). Перевірено лише на F3000 — якщо на вашій моделі якесь значення виглядає неправильно, створіть issue.

---

<div align="center">

Зроблено з ❤️. Зроблено в Україні.

</div>
