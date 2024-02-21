# water_project
repozitář je třeba vložit do složky 
.....AppData\Roaming\QGIS\QGIS3\profiles\default\processing\scripts\

The skritp treelines10 vytváří stromové linie po určité vzdálenosti vypočítáné z reálné 3D vzdálenosti 
==vstupy==
DEM rastr


Ve skriptu DSOeroze jsou udolnice vyhledávány pomocí napočítaných odtokových linií pomocí nástroje GRASS, 
==vstupy==
DEM rastr
polygony reprezentující půdní bloky


Skript forest tracks: 

cesty lze exportovat z  https://overpass-turbo.eu/
příkaz pro export: 

[out:json][timeout:25];
(
  way["highway"="track"]({{bbox}}); /* lesni cesty a polnacky */
  way["highway"="path"]({{bbox}}); /* cesty pro pesi */
);
out geom;

při spuštění samotného skriptu se použije DEM rastr území a exportovaná vrstva cest, 
