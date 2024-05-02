# water_project
Repozitář je třeba vložit/naklonovat do složky scripts:
- WIN: AppData\Roaming\QGIS\QGIS3\profiles\default\processing\scripts\
- MAC: /Users/YOUR_USERNAME/Library/Application Support/QGIS/QGIS3/profiles/default/processing/scripts


## Genreování stromových linií
Script treelines10 vytváří stromové linie po určité vzdálenosti vypočítáné z reálné 3D vzdálenosti. Pro spuštění skriptu je nutné mít digitální model reliéfu jako vstupní rastr, vektorovou vrstvu polí reprezentující půdní bloky pomocí polygonů. Pro tyto účely je využita dostupná vrstva  z LPIS.Algoritmus rozdělí rastr na menší rastery – jednotlivá pole, na kterých následně iterativně počítá průměrné 3D vzdálenosti jednotlivých vrstevnic. Na základě sklonu terénu podle metodiky živá krajina jsou následně vytvořeny jednotlivé linie. Každá vytvořená linie je v závěru výpočtu vyhlazena a nekopíruje přesně vrstevnice. Výsledkem výpočtu je jeden soubor obsahující vektorovou vrstvu linií reprezentující jednotlivé stromové prvky. V Algorytmu lze nastavit parametry pro různé sklony terénu, kterým je přiřazená příslušná vzdálenost mezi jednolivými liniemi. Ve výchozím nastavení se pro sklon "A", který odpovídá 7 % stoupání počítají stromové linie v rozestupu 120 m. V rozestupu 60 m jsou navrhovány linie mezi sklonem 7-12 % (mezi sklony "A" a "C") Pro sklon větší než 12 % jsou generovány linie ve vzdálenosti

### Vstupy
- DEM rastr
- Vektorová vrstva půdních bloků z LPIS
- Uživatelské parametry


## Algoritmus pro zatravnování drah soustředěného odtoku
Ve skriptu DSOeroze jsou udolnice vyhledávány pomocí napočítaných odtokových linií pomocí nástroje GRASS.Pro výpočet odtokových linií využívá algoritmus systému GRASS, konkrétně funkci „r.watershed“. Vsupem je DMR raster, na který před samotným výpočtem aplikován filtr pro vyhlazení chyb DMR vrstvy. Jednotlivé napočítané segmenty odtokových linií jsou následně podrobeny analýze pro výpočet průměrného sklonu. Analýze odfiltruje úseky mimo polní plochy či ty úseky s nižším průměrným sklonem, než je definice uživatele. Výsledkem je jedna vrstva polygonů reprezentující zatravněné DSO. 

### Vstupy
- DEM rastr
- Mezní hodnota pro odfiltrování segmentů s malým sklonem
- Hodnota šíře travního pásu


## Návrh terénních vln na lesních cestách
Cesty získané z webu https://overpass-turbo.eu/ rozdělí na jednotlivé segmenty, u kterých analyzuje sklon a v případně naplnění definovaných podmínek umístí krajinný prvek v podobě terénní vlny. Terénní vlny mohou být umisťovány ortogonálně či pod určitým sklonem, kde jsou nakloněny tak aby odtok vlny směřoval ze svahu dolů. Výsledkem je vektorová vrstva polygonů/linii reprezentující terénní vlny. 

### Vstupy
- DEM rastr 
- Vektorová vrstva lesních cest


### Export lesních cest: 

- cesty lze exportovat z  https://overpass-turbo.eu/
- příkaz pro export:
```
[out:json][timeout:25];
(
  way["highway"="track"]({{bbox}}); /* lesni cesty a polnacky */
  way["highway"="path"]({{bbox}}); /* cesty pro pesi */
);
out geom;
```
- při spuštění samotného scriptu se použije DEM rastr území a exportovaná vrstva cest, 
- polygony reprezentující půdní bloky, vrstva půdních bloku je nahraná na GoogleDrivu v technickém řešení, generování protiopatření

## Návrh mokřadních ploch okolo vodních toků
Skript vytváří okolo vektorových linií vytvoří definovanou obalovou zónu, která je oříznuta podle typu půdních bloků. V tomto konkrétním případně je vynechán lesní porost. Plochy lesních porostů jsou získány z konsolidované vrstvy ekosystému dostupné z https://data.nature.cz/ds/102. Výslednou vrstvou je vektorová vrstva polygonů reprezentující mokřadní plochy.  

### Vstupy 
- Vektorová vrstva vodních toků
- Vektorová vrstva konsolidované vrstvy ekosystému
