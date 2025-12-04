Jasne, oto wyjaśnienie matematyczne i fizyczne działania symulacji bojlera z regulatorem PID, w formacie Markdown.

---

# 📐 Matematyka i Fizyka Symulacji Bojlera z Regulatorem PID

Symulacja łączy w sobie dwa główne elementy: **bilans energetyczny bojlera** (fizyka obiektu) oraz **algorytm regulatora PID** (matematyka sterowania), które oddziałują na siebie w dyskretnym czasie.

---

## 1. ⚙️ Bilans Energetyczny Bojlera (`boiler_step`)

Funkcja `boiler_step` modeluje zmianę temperatury wody $\Delta T$ w bojlerze w kroku czasowym $dt$, opierając się na bilansie mocy cieplnej.

### A. Równanie Różniczkowe (model ciągły)

Szybkość zmiany energii cieplnej $E$ w czasie jest równa sumie wszystkich mocy:

$$\frac{dE}{dt} = P_{in} - P_{loss} - P_{draw}$$

Ponieważ zmiana energii cieplnej w wodzie to $dE = C \cdot dT$ ($C$ to pojemność cieplna), możemy to zapisać jako:

$$C \frac{dT}{dt} = P_{in} - P_{loss} - P_{draw}$$

A stąd, szybkość zmiany temperatury $\frac{dT}{dt}$:

$$\frac{dT}{dt} = \frac{P_{in} - P_{loss} - P_{draw}}{C}$$

### B. Składowe Mocy (P)

| Symbol | Nazwa | Wzór | Wyjaśnienie |
| :--- | :--- | :--- | :--- |
| $P_{in}$ | Moc Grzałki | $P_{in}$ (ze sterowania PID) | Moc dostarczana przez grzałkę (sterowanie). |
| $P_{loss}$ | Straty Ciepła | $k_{loss} \cdot (T - T_{out})$ | Moc tracona do otoczenia. Jest proporcjonalna do różnicy temperatury wody ($T$) i otoczenia ($T_{out}$), z uwzględnieniem współczynnika strat $k_{loss}$. |
| $P_{draw}$ | Moc Stracona na Pobór | $k_{draw} \cdot q_{out} \cdot (T - T_{cold})$ | Moc tracona z powodu wypływu gorącej wody ($T$) i wpływu zimnej wody ($T_{cold}$). Zależy od przepływu $q_{out}$ i stałej $k_{draw}$ (wzór uproszczony, $k_{draw}$ jest w przybliżeniu równe ciepłu właściwemu wody $c_w$). |

### C. Dyskretny Krok Czasowy (Metoda Eulera)

W symulacji używamy prostego przybliżenia Eulera do obliczenia nowej temperatury po kroku $dt$:

$$T_{next} = T + \Delta T = T + \frac{dT}{dt} \cdot dt$$

---

## 2. 🤖 Algorytm Regulatora PID (`simulate_boiler_pid`)

Regulator oblicza moc grzałki ($P_{in}$) w oparciu o **uchyb regulacji** $e$, czyli różnicę między temperaturą zadaną ($T_{set}$) a aktualną ($T$).

$$e = T_{set} - T$$

Sygnał sterujący $u$ (moc grzałki przed nasyceniem) jest sumą trzech członów: P, I i D.

$$u = P_{term} + I_{term} + D_{term}$$

### A. Człon Proporcjonalny (P)

Reaguje na **aktualny uchyb**:

$$P_{term} = K_p \cdot e$$

### B. Człon Całkujący (I)

Reaguje na **całkowity uchyb z przeszłości** (eliminuje uchyb ustalony). Wykorzystuje wzmocnienie całkujące $K_i$:

$$I_{term} = K_i \cdot \text{integ}$$
gdzie:
$$\text{integ} = \int e(\tau) d\tau$$
a dla dyskretnej symulacji $\text{integ}$ jest przybliżane jako suma prostokątów:
$$\text{integ}_{k+1} = \text{integ}_k + e \cdot dt$$
**Parametr:** $K_i = \frac{K_p}{T_i}$

#### Anti-Windup
W symulacji zastosowano mechanizm **Anti-Windup**. Zapobiega on nadmiernemu "nawinięciu" całki, gdy moc grzałki jest już nasycona ($P_{in} = P_{max}$). Całka jest blokowana lub regulowana, gdy wyjście regulatora $u$ przekracza $P_{max}$ lub spada poniżej $0$, co zapobiega dużym przeregulowaniom.

### C. Człon Różniczkujący (D)

Reaguje na **szybkość zmian uchybu** (przewiduje przyszłe zmiany). Wykorzystuje wzmocnienie różniczkujące $K_d$:

$$D_{term} = K_d \cdot \frac{de}{dt}$$
a dla dyskretnej symulacji różniczkę przybliża się różnicą wsteczną:
$$D_{term} = K_d \cdot \frac{e - e_{prev}}{dt}$$
**Parametr:** $K_d = K_p \cdot T_d$

### D. Nasycenie (Ograniczenie Wyjścia)

Ostateczny sygnał sterujący $P_{in}$ (rzeczywista moc grzałki) jest ograniczony fizycznymi możliwościami grzałki $P_{max}$ i $0$:

$$P_{in} = \max(0.0, \min(u, P_{max}))$$