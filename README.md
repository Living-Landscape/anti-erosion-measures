# water_project
repozitář je třeba vložit/naklonovat do složky scripts:
- WIN: AppData\Roaming\QGIS\QGIS3\profiles\default\processing\scripts\
- MAC: /Users/<username>/Library/Application Support/QGIS/QGIS3/profiles/default/processing/scripts


## Treelines10
Script treelines10 vytváří stromové linie po určité vzdálenosti vypočítáné z reálné 3D vzdálenosti.

### Vstupy
- DEM rastr


## DSOeroze
Ve skriptu DSOeroze jsou udolnice vyhledávány pomocí napočítaných odtokových linií pomocí nástroje GRASS, 

### Vstupy
- DEM rastr


## Forest Tracks and Paths
forest_tracks_and_paths
polygony reprezentující půdní bloky


Script forest tracks: 

cesty lze exportovat z  https://overpass-turbo.eu/
příkaz pro export: 

[out:json][timeout:25];
(
  way["highway"="track"]({{bbox}}); /* lesni cesty a polnacky */
  way["highway"="path"]({{bbox}}); /* cesty pro pesi */
);
out geom;

při spuštění samotného skriptu se použije DEM rastr území a exportovaná vrstva cest, 
=======
polygony reprezentující půdní bloky, vrstva půdních bloku je nahraná na GoogleDrivu v technickém řešení, generování protiopatření 
