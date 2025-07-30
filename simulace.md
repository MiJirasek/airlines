# Simulační prostředí pro soutěž studentských týmů

## Základní zadání
Vytvořit simulační prostředí pro soutěž studentských týmů.

## Kontext
Studentské týmy mezi sebou soutěží na trhu aerolinek. Studenti si na výuku přináší formulovanou strategii své aerolinky, tu následně implementují prostřednictvím podrobnějších pololetních plánů a reakcí na vývoj prostředí, který ovlivňují další studentské týmy a herní nastavení.

## Technologie

- **Kód**: Python  
- **Napojování na AI API**: `litellm`  
- **AI API**: Gemini  
- **Framework**: LangGraph  
- **Observabilita**: LangSmith  
- **GitHub repo**: public  
- **Deploy app**: Streamlit  
- **Přihlášení týmů**: přes `streamlit-authenticator`  
- **Úložiště dat**: Firestore kolekce (přihlášený UID smí číst/psát jen svůj dokument)

## Uživatelské rozhraní (UI)
Formulář pro studenty:
- Nahrání JSON pololetního plánu  
- Stav trhu  
- Stav aerolinky  

---

## AI agenti

### Firemní agent

- **Role**: Reprezentuje danou aerolinku jako organizaci  
- **Cíl**: Zhodnocení realizace pololetního plánu  
- **Nastavení (sub-graph)**:  
  - Node A: validátor (rozpočet, kapacity)  
  - Node B: implementační logika  
  - Edge: rozhodnutí „co se nestihne“  
- **Vstupy**: Pololetní implementační plán  
- **Výstup**:  
  - `approved_actions: [...]`  
  - `rejected_actions: [...]`  
  - `cash_used: ...`  
- **Nástroje**: Čtení a zápis dokumentu stavu aerolinky

---

### Tržní agent

- **Role**: Reprezentuje tržní prostředí  
- **Cíl**: Vyhodnocení výkonu aerolinek na trhu  
- **Vstupy**: Realizace plánů, data o trhu a jeho vývoji  
- **Nástroje**: Čtení a zápis dokumentů o aerolinkách a trhu  
- **Výstup**:  
  - Aktualizace stavu aerolinky  
  - Aktualizace trhu a jeho vývoje  

---

### Hodnoticí agent

- **Role**: Podpora vyučujícího a studentů  
- **Cíl**: Hodnocení kvality implementace strategie  
- **Nástroje**: Čtení všech dokumentů  
- **Výstup**:  
  - Rychlá hodnoticí metrika  
  - Textová formativní zpětná vazba zapsaná do dokumentu aerolinky

---

## Vstupní data do simulace

- **Trh** – aktuální situace o zákaznících, konkurentech i širším prostředí  
- **Strategie** – jednotlivých aerolinek naformulované pro danou hodinu  
- **Tržní vývoj** – definovaný seznam scénářů a pravděpodobností; 1–2 události v každém kole, aby týmy musely adaptovat strategii  

---

## Workflow

1. Studenti zadávají pololetní implementační plán  
2. Firemní AI agent vyhodnotí realizovatelnost plánu a realizovatelnou část předá jako výstup  
3. Tržní agent porovná realizace plánů mezi aerolinkami a aktualizuje stav trhu  
4. Hodnoticí agent připraví zpětnou vazbu  
5. Studenti obdrží:
   - Výsledky své aerolinky  
   - Vývoj trhu  
   - Zpětnou vazbu
