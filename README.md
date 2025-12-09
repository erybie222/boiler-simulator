# Symulacja Bojlera Elektrycznego z Regulacją PID

Projekt ten implementuje numeryczną symulację termodynamiki elektrycznego podgrzewacza wody (bojlera) sterowanego algorytmem PID. Symulator modeluje zachowanie temperatury wody w czasie, uwzględniając bezwładność cieplną, straty energii do otoczenia oraz zakłócenia wynikające z poboru wody (np. prysznic).

## 1. Model Matematyczny (Fizyka)

Symulacja opiera się na **I Zasadzie Termodynamiki** (zasada zachowania energii). Zmiana temperatury wody w zbiorniku jest opisana równaniem różniczkowym bilansu mocy.

### Równanie różniczkowe stanu
Zmiana temperatury $T$ w czasie $t$ wyraża się wzorem:

$$C \cdot \frac{dT}{dt} = P_{in}(t) - P_{loss}(t) - P_{draw}(t)$$

Gdzie poszczególne składniki to:

1.  **Moc dostarczona ($P_{in}$):** Sterowanie z grzałki (ograniczone do $P_{max}$).
2.  **Straty postojowe ($P_{loss}$):** Wynikają z przenikania ciepła przez izolację (Prawo stygnięcia Newtona):
    $$P_{loss} = k_{loss} \cdot (T(t) - T_{out})$$
3.  **Straty przepływowe ($P_{draw}$):** Wynikają z wymiany ciepłej wody na zimną podczas poboru:
    $$P_{draw} = k_{draw} \cdot q_{out}(t) \cdot (T(t) - T_{cold})$$

### Dyskretyzacja (Metoda Eulera)
Do symulacji komputerowej równanie ciągłe zostało zdyskretyzowane przy użyciu metody Eulera z krokiem czasowym $\Delta t$:

$$T_{k+1} = T_k + \frac{P_{in} - P_{loss} - P_{draw}}{C} \cdot \Delta t$$

---

## 2. Algorytm Sterowania (PID)

Do utrzymania zadanej temperatury ($T_{set}$) wykorzystano regulator PID w wersji dyskretnej z mechanizmem **Anti-Windup**.

Równanie sterowania:
$$u(t) = P_{term} + I_{term} + D_{term}$$

Gdzie poszczególne człony to:

* **Proporcjonalny (P):** $K_p \cdot e(t)$
* **Całkujący (I):** $\frac{K_p}{T_i} \cdot \sum (e(t) \cdot \Delta t)$
* **Różniczkujący (D):** $K_p \cdot T_d \cdot \frac{e(t) - e(t-1)}{\Delta t}$

Uchyb regulacji zdefiniowany jest jako: $e(t) = T_{set} - T(t)$.

**Zabezpieczenia:**
* **Nasycenie wyjścia:** Moc grzałki jest ograniczona do zakresu $[0, P_{max}]$.
* **Anti-Windup (Clamping):** Całkowanie jest wstrzymywane, gdy regulator jest nasycony, aby zapobiec niekontrolowanemu wzrostowi członu I.

---

## 3. Słownik Zmiennych i Parametrów

Poniższe tabele opisują wszystkie kluczowe zmienne użyte w kodzie Python.

### Klasa `BoilerParams` (Stałe fizyczne)

| Zmienna Python | Symbol Mat. | Jednostka | Opis |
| :--- | :--- | :--- | :--- |
| `C` | $C$ | $J/^\circ C$ | **Pojemność cieplna.** Ilość energii potrzebna do ogrzania całego bojlera o 1 stopień. Obliczana jako $V \cdot \rho \cdot c_p$. |
| `k_loss` | $k_{loss}$ | $W/^\circ C$ | **Współczynnik strat postojowych.** Określa jakość izolacji termicznej. Im mniejsza wartość, tym lepsza izolacja. |
| `k_draw` | $k_{draw}$ | $\frac{W}{^\circ C \cdot (l/s)}$ | **Współczynnik strat przepływowych.** Stała fizyczna wynikająca z ciepła właściwego wody ($\approx 4186$). Określa koszt energetyczny podgrzewania przepływającej wody. |
| `T_out` | $T_{out}$ | $^\circ C$ | **Temperatura otoczenia.** Temperatura powietrza wokół bojlera (np. w łazience). |
| `T_cold` | $T_{cold}$ | $^\circ C$ | **Temperatura zimnej wody.** Temperatura wody zasilającej z sieci wodociągowej. |

### Parametry Regulatora PID

| Zmienna | Symbol | Opis |
| :--- | :--- | :--- |
| `Kp` | $K_p$ | **Wzmocnienie proporcjonalne.** Decyduje o tym, jak agresywnie regulator reaguje na bieżący błąd. |
| `Ti` | $T_i$ | **Czas zdwojenia (stała czasowa całkowania).** Wpływa na siłę członu całkującego ($K_i = K_p / T_i$). Eliminuje uchyb ustalony. |
| `Td` | $T_d$ | **Czas wyprzedzenia (stała czasowa różniczkowania).** Wpływa na człon różniczkujący ($K_d = K_p \cdot T_d$). Tłumi oscylacje i reaguje na szybkość zmian. |
| `T_set` | $T_{set}$ | **Wartość zadana.** Docelowa temperatura wody, którą chcemy utrzymać. |

### Zmienne Symulacji (`boiler_step` / `simulate`)

| Zmienna | Jednostka | Opis |
| :--- | :--- | :--- |
| `dt` | $s$ | **Krok czasowy.** Rozdzielczość czasowa symulacji (np. 1.0 sekunda). |
| `total_time` | $s$ | Całkowity czas trwania symulacji. |
| `T` | $^\circ C$ | Aktualna temperatura wody w danej chwili. |
| `P_in` | $W$ | Aktualna moc dostarczana przez grzałkę (sterowanie). |
| `q_out` | $l/s$ | Aktualny przepływ wody użytkowej (zakłócenie, np. odkręcony kran). |
| `e` | $^\circ C$ | Uchyb regulacji ($T_{set} - T$). |
| `integ` | $^\circ C \cdot s$ | Skumulowana suma błędów (pamięć regulatora dla członu I). |

---

## 4. Struktura Kodu

* `BoilerParams`: Dataclass przechowująca stałe parametry fizyczne obiektu.
* `boiler_step()`: Funkcja realizująca jeden krok całkowania numerycznego (fizyka).
* `simulate_boiler_pid()`: Główna pętla symulacji łącząca regulator PID z modelem fizycznym.
* `run_simulation()`: Funkcja pomocnicza (wrapper), która ułatwia uruchomienie symulacji z parametrami użytkowymi (pojemność w litrach, przepływ w l/min).

## 5. Wymagania

* Python 3.7+
* `pandas` (do zbierania i analizy wyników)
* `dataclasses` (standardowa biblioteka)